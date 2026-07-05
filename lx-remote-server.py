#!/usr/bin/env python3
"""
LX Music 區域網遙控伺服器
- 提供靜態文件服務（HTML）
- 代理 API 請求到 LX Music（解決 CORS 跨域問題）
- 支援 SSE 實時串流
"""

import http.server
import urllib.request
import urllib.error
import os
import sys
import socket
import json
import threading
import signal

# === 設定 ===
PORT = 8080
LX_API_HOST = 'http://127.0.0.1:23330'
HTML_FILE = 'lx-remote.html'

# LX Music API 路徑前綴
API_PATHS = (
    '/status', '/lyric', '/lyric-all', '/subscribe-player-status',
    '/play', '/pause', '/skip-next', '/skip-prev',
    '/seek', '/volume', '/mute', '/collect', '/uncollect',
)


def get_lan_ip():
    """獲取本機區域網 IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        # 用一個唔存在嘅地址嚟拎路由 IP
        s.connect(('10.254.254.254', 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # fallback: 列舉所有非 127 嘅 IPv4
        try:
            hostname = socket.gethostname()
            for addr in socket.gethostbyname_ex(hostname)[2]:
                if not addr.startswith('127.'):
                    return addr
        except Exception:
            pass
        return '127.0.0.1'


class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    """自訂 handler：代理 API + 提供靜態文件"""

    def __init__(self, *args, **kwargs):
        # 以 HTML 所在目錄作為靜態文件根目錄
        super().__init__(*args, directory=os.path.dirname(os.path.abspath(__file__)), **kwargs)

    def _is_api_path(self, path):
        """判斷是否為 API 路徑"""
        clean_path = path.split('?')[0].split('#')[0]
        for p in API_PATHS:
            if clean_path == p or clean_path.startswith(p + '?'):
                return True
        return False

    def _proxy_request(self, method='GET'):
        """代理請求到 LX Music API"""
        path = self.path
        target_url = LX_API_HOST + path

        try:
            req = urllib.request.Request(target_url, method=method)

            # 轉發查詢參數
            if self.command == 'GET' and self.path.find('?') >= 0:
                pass  # query string already in self.path

            # 轉發 body（如果有）
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length)
                req.data = body

            # 設置超時
            timeout = None
            if '/subscribe-player-status' in path:
                timeout = 3600  # SSE 長連接，用長 timeout
            else:
                timeout = 10

            resp = urllib.request.urlopen(req, timeout=timeout)

            # 轉發狀態碼
            self.send_response(resp.status)

            # 轉發關鍵 headers
            content_type = resp.headers.get('Content-Type', 'application/octet-stream')
            self.send_header('Content-Type', content_type)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', '*')
            self.send_header('Cache-Control', 'no-cache')

            # SSE 需要嘅 headers
            if 'text/event-stream' in content_type:
                self.send_header('Connection', 'keep-alive')
                self.send_header('X-Accel-Buffering', 'no')

            self.end_headers()

            # 串流傳輸（尤其係 SSE）
            buffer_size = 1024 * 64
            while True:
                chunk = resp.read(buffer_size)
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
            error_body = e.read()
            self.wfile.write(error_body)
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
            self.wfile.write(json.dumps({
                'error': '代理錯誤',
                'detail': str(e)
            }).encode())

    def do_GET(self):
        if self._is_api_path(self.path):
            self._proxy_request('GET')
        else:
            super().do_GET()

    def do_POST(self):
        if self._is_api_path(self.path):
            self._proxy_request('POST')
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
        """精簡日誌輸出"""
        if self._is_api_path(self.path.split('?')[0]):
            print(f'  🎵 API  {self.path}')


def main():
    lan_ip = get_lan_ip()

    # 檢查 HTML 文件是否存在
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(script_dir, HTML_FILE)
    if not os.path.exists(html_path):
        print(f'❌ 找不到 {HTML_FILE}，請確認文件喺同一個目錄')
        sys.exit(1)

    # 檢查 LX Music API 係咪著緊
    try:
        test_req = urllib.request.Request(LX_API_HOST + '/status')
        test_resp = urllib.request.urlopen(test_req, timeout=2)
        test_data = json.loads(test_resp.read())
        print(f'✅ LX Music API 狀態：{test_data.get("status", "unknown")}')
    except Exception:
        print('⚠️  警告：無法連接到 LX Music API (127.0.0.1:23330)')
        print('   請確認 LX Music 已啟動並且已開啟「開放 API 服務」')
        print()

    # 啟動伺服器
    server = http.server.HTTPServer(('0.0.0.0', PORT), ProxyHandler)
    server.timeout = 1  # 令 serve_forever 可以收到 signal

    print()
    print('=' * 50)
    print('  🔥 LX Music 區域網遙控器已啟動')
    print('=' * 50)
    print()
    print(f'  📱 手機訪問：')
    print(f'     http://{lan_ip}:{PORT}/{HTML_FILE}')
    print()
    print(f'  💻 本機訪問：')
    print(f'     http://127.0.0.1:{PORT}/{HTML_FILE}')
    print()
    print(f'  🎯 代理 LX Music API：')
    print(f'     {LX_API_HOST}')
    print()
    print('  ⏹  按 Ctrl+C 停止')
    print('=' * 50)
    print()

    # 優雅關閉
    shutdown_event = threading.Event()

    def signal_handler(sig, frame):
        print('\n\n正在關閉伺服器...')
        shutdown_event.set()
        server.shutdown()
        print('已停止')

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
