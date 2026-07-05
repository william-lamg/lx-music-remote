"""
LX Music API 控制助手
Call via `python scripts/lx_api.py <action> [params]`

Actions:
  status                — 獲取播放器狀態
  play                  — 播放
  pause                 — 暫停
  toggle-play           — 切換播放/暫停
  next                  — 下一首
  prev                  — 上一首
  seek <seconds>        — 跳轉到指定秒數
  volume <0-100>        — 設定音量
  mute <true/false>     — 靜音開關
  collect               — 收藏當前歌曲
  uncollect             — 取消收藏
  lyric                 — 獲取當前 LRC 歌詞
  lyric-all             — 獲取所有類型歌詞
  current-song          — 獲取當前歌曲簡要資訊
  search-play <name> [artist]  — 搜索並播放指定歌曲
  recommend-next [api_key]      — 🔥 根據當前歌曲，用 Last.fm 推薦下一首
  search <keywords>     — 搜索歌曲（唔播）
"""

import sys
import os
import json
import urllib.request
import urllib.error
import urllib.parse
import subprocess
import webbrowser

API_HOST = 'http://127.0.0.1:23330'

def api_get(path):
    url = API_HOST + path
    try:
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=5)
        return resp.read().decode('utf-8')
    except urllib.error.URLError as e:
        return json.dumps({'error': f'無法連接到 LX Music ({e.reason})'})
    except Exception as e:
        return json.dumps({'error': str(e)})

def api_get_json(path):
    raw = api_get(path)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {'error': '無效回應', 'raw': raw[:200]}

def cmd_status():
    data = api_get_json('/status')
    if 'error' in data:
        return data
    return {
        'status': data.get('status'),
        'song': data.get('name', '—'),
        'artist': data.get('singer', '—'),
        'album': data.get('albumName', '—'),
        'progress': f"{data.get('progress', 0):.1f}s / {data.get('duration', 0):.1f}s",
        'volume': data.get('volume'),
        'muted': data.get('mute', False),
        'collected': data.get('collect', False),
        'lyric_line': data.get('lyricLineText', ''),
    }

def cmd_current_song():
    data = api_get_json('/status')
    if 'error' in data:
        return data
    return {
        'status': data.get('status'),
        'song': data.get('name', '—'),
        'artist': data.get('singer', '—'),
        'album': data.get('albumName', '—'),
        'duration': data.get('duration'),
        'progress': data.get('progress'),
    }

def cmd_lyric():
    return api_get('/lyric')

def cmd_lyric_all():
    return api_get('/lyric-all')

def cmd_simple(action):
    paths = {
        'play': '/play',
        'pause': '/pause',
        'next': '/skip-next',
        'prev': '/skip-prev',
        'collect': '/collect',
        'uncollect': '/uncollect',
    }
    path = paths.get(action)
    if not path:
        return {'error': f'未知操作: {action}'}
    api_get(path)
    return {'ok': True, 'action': action}

def cmd_seek(seconds):
    api_get(f'/seek?offset={seconds}')
    return {'ok': True, 'action': 'seek', 'seconds': seconds}

def cmd_volume(val):
    api_get(f'/volume?volume={val}')
    return {'ok': True, 'action': 'volume', 'value': val}

def cmd_mute(val):
    api_get(f'/mute?mute={val}')
    return {'ok': True, 'action': 'mute', 'value': val}

def cmd_toggle_play():
    data = api_get_json('/status')
    if 'error' in data:
        return data
    if data.get('status') == 'playing':
        return cmd_simple('pause')
    else:
        return cmd_simple('play')

def _open_scheme_url(path):
    """通過 Scheme URL 調用 LX Music"""
    url = 'lxmusic://' + path
    try:
        if sys.platform == 'win32':
            subprocess.run(['cmd', '/c', 'start', url], check=False, timeout=5)
        else:
            webbrowser.open(url)
        return {'ok': True, 'scheme': url,
                'hint': '已發送搜歌指令，LX Music 將會搜索並播放'}
    except Exception as e:
        return {'error': str(e), 'hint': '請確保 LX Music 已安裝並註冊 lxmusic:// 協議'}

def cmd_search_play(name, artist=''):
    """搜索並播放指定歌曲"""
    if not name:
        return {'error': '請輸入歌名', 'usage': 'search-play <歌名> [歌手名]'}
    # 先確認 LX Music 在線
    status = api_get_json('/status')
    if not status:
        return {'error': 'LX Music 未運行或 API 未開啟', 'hint': '請先打開 LX Music 並開啟「開放 API 服務」'}
    params = {'name': name, 'playLater': False}
    if artist:
        params['singer'] = artist
    data = urllib.parse.quote(json.dumps(params, ensure_ascii=False))
    result = _open_scheme_url(f'music/searchPlay?data={data}')
    if result.get('ok'):
        result['song'] = name
        if artist:
            result['artist'] = artist
    return result

def cmd_search(keywords):
    """搜索歌曲（唔自動播放）"""
    if not keywords:
        return {'error': '請輸入搜索關鍵字', 'usage': 'search <關鍵字>'}
    params = {'keywords': keywords}
    data = urllib.parse.quote(json.dumps(params, ensure_ascii=False))
    return _open_scheme_url(f'music/search?data={data}')

def cmd_direct_play(name, artist=''):
    """進階搜歌即播 — 用公開API搵ID直接播（唔使㩒揀結果）"""
    import subprocess
    script_dir = os.path.dirname(os.path.abspath(__file__))
    search_script = os.path.join(script_dir, 'search_direct.py')
    cmd = [sys.executable, search_script, name]
    if artist:
        cmd.append(artist)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        lines = result.stdout.strip().split('\n')
        outputs = []
        for line in lines:
            try:
                outputs.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        # 最後一行係 play result
        if outputs:
            return outputs[-1]
        return {'error': '腳本無輸出', 'raw': result.stdout[:200]}
    except subprocess.TimeoutExpired:
        return {'error': '搜尋超時'}
    except Exception as e:
        return {'error': str(e)}

def cmd_recommend_next(api_key=''):
    """用 Last.fm 推薦下一首歌"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    rec_script = os.path.join(script_dir, 'recommend_next.py')
    cmd = [sys.executable, rec_script]
    if api_key:
        cmd.append(api_key)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        lines = result.stdout.strip().split('\n')
        outputs = []
        for line in lines:
            try:
                outputs.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        if outputs:
            return outputs[-1]
        return {'error': '腳本無輸出', 'raw': result.stdout[:200]}
    except subprocess.TimeoutExpired:
        return {'error': '推薦超時'}
    except Exception as e:
        return {'error': str(e)}

ACTIONS = {
    'status': cmd_status,
    'current-song': cmd_current_song,
    'lyric': cmd_lyric,
    'lyric-all': cmd_lyric_all,
    'play': lambda: cmd_simple('play'),
    'pause': lambda: cmd_simple('pause'),
    'toggle-play': cmd_toggle_play,
    'next': lambda: cmd_simple('next'),
    'prev': lambda: cmd_simple('prev'),
    'seek': lambda: cmd_seek(_arg(1, '0')),
    'volume': lambda: cmd_volume(_arg(1, '50')),
    'mute': lambda: cmd_mute(_arg(1, 'true')),
    'collect': lambda: cmd_simple('collect'),
    'uncollect': lambda: cmd_simple('uncollect'),
    'search-play': lambda: cmd_search_play(_arg(0, ''), _arg(1, '')),
    'direct-play': lambda: cmd_direct_play(_arg(0, ''), _arg(1, '')),
    'recommend-next': lambda: cmd_recommend_next(_arg(0, '')),
    'search': lambda: cmd_search(_arg(0, '')),
}

def _arg(idx, default=''):
    args = sys.argv[2:]
    return args[idx] if idx < len(args) else default

def main():
    if len(sys.argv) < 2:
        print(json.dumps({'error': '請指定操作', 'available': list(ACTIONS.keys())}))
        return

    action = sys.argv[1]
    handler = ACTIONS.get(action)
    if not handler:
        print(json.dumps({'error': f'未知操作: {action}', 'available': list(ACTIONS.keys())}))
        return

    result = handler()
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
