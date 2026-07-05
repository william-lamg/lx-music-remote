#!/usr/bin/env python3
"""
LX Music 一體化遙控應用
- 自動監測 LX Music 進程
- 音樂開 → 自動啟動代理伺服器
- 音樂關 → 自動停止並退出
- 雙擊即用，唔使手動操作
"""

import http.server
import urllib.request
import urllib.error
import json
import os
import sys
import socket
import signal
import threading
import time
import subprocess
import webbrowser

# === 設定 ===
PORT = 8080
LX_API_HOST = 'http://127.0.0.1:23330'
POLL_INTERVAL = 2  # 每秒檢查 LX Music 進程

# LX Music 進程名（Windows）
LX_PROCESS_NAMES = [
    'lx-music-desktop.exe',
    'lx-music.exe',
    'lx-music-desktop',
    'LX Music.exe',
    'LX-Music.exe',
]

# API 路徑列表
API_PATHS = (
    '/status', '/lyric', '/lyric-all', '/subscribe-player-status',
    '/play', '/pause', '/skip-next', '/skip-prev',
    '/seek', '/volume', '/mute', '/collect', '/uncollect',
)

# HTML 文件路徑（同目錄或者內嵌）
HERE = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(HERE, 'lx-remote.html')


def get_lan_ip():
    """獲取本機區域網 IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(('10.254.254.254', 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            hostname = socket.gethostname()
            for addr in socket.gethostbyname_ex(hostname)[2]:
                if not addr.startswith('127.'):
                    return addr
        except Exception:
            pass
        return '127.0.0.1'


def is_lx_music_running():
    """檢查 LX Music 進程係咪運行中"""
    try:
        # 用 WMIC 代替 tasklist，更穩定 + 編碼友好
        output = subprocess.check_output(
            'wmic process get name /FORMAT:CSV',
            shell=True,
            timeout=5,
            stderr=subprocess.DEVNULL
        )
        text = output.decode('utf-8', errors='replace')
        for pname in LX_PROCESS_NAMES:
            if pname.lower() in text.lower():
                return True
        return False
    except subprocess.TimeoutExpired:
        return False
    except FileNotFoundError:
        # WMIC 可能唔存在，fallback 用 tasklist
        try:
            output = subprocess.check_output(
                'tasklist /NH /FO CSV',
                shell=True,
                timeout=5,
                stderr=subprocess.DEVNULL
            )
            text = output.decode('gbk', errors='replace')
            for pname in LX_PROCESS_NAMES:
                if pname.lower() in text.lower():
                    return True
            return False
        except Exception:
            return False
    except Exception:
        return False


def wait_for_lx_music():
    """等待 LX Music 啟動"""
    print('  ⏳ 等待 LX Music 啟動...')
    while True:
        if is_lx_music_running():
            print('  ✅ LX Music 已啟動')
            return True
        time.sleep(2)


def wait_for_api():
    """等待 LX Music API 就緒"""
    print('  ⏳ 等待 API 就緒...')
    for i in range(30):  # 最多等 60 秒
        try:
            req = urllib.request.Request(LX_API_HOST + '/status')
            resp = urllib.request.urlopen(req, timeout=2)
            data = json.loads(resp.read())
            status = data.get('status', 'unknown')
            print(f'  ✅ API 就緒，狀態：{status}')
            return True
        except Exception:
            if i % 5 == 0:
                print(f'  .', end='', flush=True)
            time.sleep(2)
    print()
    print('  ⚠️  API 未能連接，但伺服器仍會啟動')
    return False


class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    """代理 API 請求 + 提供靜態文件"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=HERE, **kwargs)

    def _is_api_path(self, path):
        clean_path = path.split('?')[0].split('#')[0]
        for p in API_PATHS:
            if clean_path == p or clean_path.startswith(p + '?'):
                return True
        return False

    def _proxy_request(self):
        path = self.path
        target_url = LX_API_HOST + path

        try:
            req = urllib.request.Request(target_url)

            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                req.data = self.rfile.read(content_length)

            timeout = 3600 if '/subscribe-player-status' in path else 10
            resp = urllib.request.urlopen(req, timeout=timeout)

            self.send_response(resp.status)

            content_type = resp.headers.get('Content-Type', 'application/octet-stream')
            self.send_header('Content-Type', content_type)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', '*')
            self.send_header('Cache-Control', 'no-cache')

            if 'text/event-stream' in content_type:
                self.send_header('Connection', 'keep-alive')
                self.send_header('X-Accel-Buffering', 'no')

            self.end_headers()

            buf_size = 1024 * 64
            while True:
                chunk = resp.read(buf_size)
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    break
            resp.close()

        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(e.read())
            e.close()

        except urllib.error.URLError as e:
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'error': '無法連接到 LX Music',
                'detail': str(e.reason)
            }).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': '代理錯誤', 'detail': str(e)}).encode())

    def do_GET(self):
        if self._is_api_path(self.path):
            self._proxy_request()
        else:
            super().do_GET()

    def do_POST(self):
        if self._is_api_path(self.path):
            self._proxy_request()
        else:
            self.send_response(405)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

    def log_message(self, format, *args):
        pass  # 靜默日誌


def monitor_process(stop_event):
    """監測 LX Music 進程，退出時觸發停止"""
    while not stop_event.is_set():
        time.sleep(POLL_INTERVAL)
        if not is_lx_music_running():
            print()
            print('  🔴 LX Music 已關閉，正在停止伺服器...')
            stop_event.set()
            break


def main():
    lan_ip = get_lan_ip()

    # 顯示啟動畫面
    print()
    print('=' * 52)
    print('   🎵 LX Music 一體化遙控器')
    print('=' * 52)
    print()

    # 先等 LX Music 啟動
    if not is_lx_music_running():
        print('  ⚠️  LX Music 未啟動')
        print('  請先打開 LX Music，我會自動連接')
        print()
        wait_for_lx_music()
    else:
        print('  ✅ LX Music 正在運行')

    # 檢查 HTML
    html_ok = os.path.exists(HTML_PATH)
    if html_ok:
        print(f'  ✅ 遙控器頁面：lx-remote.html')
    else:
        print(f'  ⚠️  找不到 lx-remote.html，用內嵌頁面')

    # 等 API 就緒（非必須，後台照行）
    api_ok = wait_for_api()

    # 啟動代理伺服器
    server = http.server.HTTPServer(('0.0.0.0', PORT), ProxyHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    print()
    print('  🟢 遙控器已啟動！')
    print()
    print(f'  📱 手機訪問：')
    print(f'     http://{lan_ip}:{PORT}/lx-remote.html')
    print()
    print(f'  💻 本機訪問：')
    print(f'     http://127.0.0.1:{PORT}/lx-remote.html')
    print()
    print(f'  🔗 連接 LX Music：')
    print(f'     {LX_API_HOST}')
    print()
    print('  ⏹  關閉 LX Music 自動停止')
    print('     或按 Ctrl+C 手動停止')
    print('=' * 52)
    print()

    # 自動打開瀏覽器（本機）
    try:
        webbrowser.open(f'http://127.0.0.1:{PORT}/lx-remote.html')
    except Exception:
        pass

    # 監測 LX Music 進程（後台）
    stop_event = threading.Event()
    monitor_thread = threading.Thread(
        target=monitor_process,
        args=(stop_event,),
        daemon=True
    )
    monitor_thread.start()

    # 等待停止信號
    try:
        while not stop_event.is_set():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print()
        print('  ⏹  收到中斷信號，正在停止...')

    # 清理
    print('  正在關閉伺服器...')
    server.shutdown()
    print('  ✅ 已停止')
    print()


if __name__ == '__main__':
    main()
