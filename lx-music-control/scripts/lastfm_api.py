"""
Last.fm Scrobble 助手
Call via: python scripts/lastfm_api.py <action> [params]

Actions:
  now-playing <artist> <title> [album]    — 更新正在播放
  scrobble <artist> <title> <timestamp> [album]  — 記錄 scrobble
  recent [user]                           — 獲取最近播放
  info <artist> <title>                   — 獲取歌曲資訊
  similar <artist>                        — 獲取相似藝人
  top-tracks [artist]                     — 獲取熱門歌曲
  help                                    — 顯示說明

Usage:
  # 檢查 config
  python scripts/lastfm_api.py config-check

  # 更新 now playing（如果 LX Music 正在播放）
  python scripts/lastfm_api.py now-playing-from-lx

  # Scrobble 當前歌曲
  python scripts/lastfm_api.py scrobble-from-lx
"""

import sys
import json
import os
import hmac
import hashlib
import time
import urllib.request
import urllib.parse
import urllib.error

# === 設定（用戶自行填寫）===
# 可通過環境變數 LASTFM_API_KEY, LASTFM_SECRET, LASTFM_USER, LASTFM_SESSION 覆蓋
CONFIG = {
    'api_key': os.environ.get('LASTFM_API_KEY', ''),
    'secret': os.environ.get('LASTFM_SECRET', ''),
    'username': os.environ.get('LASTFM_USER', ''),
    'session_key': os.environ.get('LASTFM_SESSION', ''),
}

API_URL = 'https://ws.audioscrobbler.com/2.0/'

def _get_lx_status():
    """從 LX Music 獲取當前播放狀態"""
    try:
        req = urllib.request.Request('http://127.0.0.1:23330/status')
        resp = urllib.request.urlopen(req, timeout=3)
        data = json.loads(resp.read().decode('utf-8'))
        return data
    except Exception as e:
        return {'error': str(e)}

def _api_call(method, params, sign=False):
    """Call Last.fm API"""
    params['method'] = method
    params['api_key'] = CONFIG['api_key']
    params['format'] = 'json'

    if sign:
        params['sk'] = CONFIG['session_key']
        # 按字母順序排序並加上 secret 做 md5 簽名
        sorted_keys = sorted(params.keys())
        sig_str = ''.join(f'{k}{params[k]}' for k in sorted_keys) + CONFIG['secret']
        params['api_sig'] = hashlib.md5(sig_str.encode('utf-8')).hexdigest()

    data = urllib.parse.urlencode(params).encode()
    try:
        req = urllib.request.Request(API_URL, data=data)
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        return {'error': f'HTTP {e.code}', 'detail': body[:300]}
    except Exception as e:
        return {'error': str(e)}

def cmd_config_check():
    """檢查 Last.fm 設定"""
    missing = [k for k, v in CONFIG.items() if not v]
    if missing:
        return {'status': 'incomplete', 'missing_fields': missing,
                'hint': '請透過環境變數設定: LASTFM_API_KEY, LASTFM_SECRET, LASTFM_USER, LASTFM_SESSION'}
    return {'status': 'configured', 'username': CONFIG['username']}

def cmd_now_playing(artist, title, album=''):
    """更新 now playing"""
    if not CONFIG['session_key']:
        return {'error': '未設定 session_key', 'hint': cmd_config_check()['hint']}
    params = {
        'artist': artist,
        'track': title,
    }
    if album:
        params['album'] = album
    return _api_call('track.updateNowPlaying', params, sign=True)

def cmd_now_playing_from_lx():
    """從 LX Music 當前狀態更新 now playing"""
    status = _get_lx_status()
    if 'error' in status:
        return status
    if status.get('status') not in ('playing', 'paused'):
        return {'error': 'LX Music 不在播放中', 'status': status.get('status')}
    return cmd_now_playing(
        status.get('singer', ''),
        status.get('name', ''),
        status.get('albumName', '')
    )

def cmd_scrobble(artist, title, timestamp, album=''):
    """Scrobble 一首歌"""
    if not CONFIG['session_key']:
        return {'error': '未設定 session_key'}
    params = {
        'artist': artist,
        'track': title,
        'timestamp': str(timestamp),
    }
    if album:
        params['album'] = album
    return _api_call('track.scrobble', params, sign=True)

def cmd_scrobble_from_lx():
    """從 LX Music 當前狀態 scrobble（使用當前時間戳）"""
    status = _get_lx_status()
    if 'error' in status:
        return status
    if status.get('status') != 'playing':
        return {'error': 'LX Music 不在播放中'}
    return cmd_scrobble(
        status.get('singer', ''),
        status.get('name', ''),
        int(time.time()),
        status.get('albumName', '')
    )

def cmd_recent(user=''):
    """獲取最近播放"""
    username = user or CONFIG['username']
    if not username:
        return {'error': '請提供 username 或設定 LASTFM_USER'}
    return _api_call('user.getRecentTracks', {'user': username, 'limit': 10})

def cmd_info(artist, title):
    """獲取歌曲資訊"""
    return _api_call('track.getInfo', {'artist': artist, 'track': title})

def cmd_similar(artist):
    """獲取相似藝人"""
    return _api_call('artist.getSimilar', {'artist': artist})

def cmd_top_tracks(artist=''):
    """獲取熱門歌曲（空缺時用全局 Top）"""
    if artist:
        return _api_call('artist.getTopTracks', {'artist': artist})
    return _api_call('chart.getTopTracks', {})

def cmd_help():
    return {
        'usage': 'python scripts/lastfm_api.py <action> [params]',
        'actions': {
            'now-playing <artist> <title> [album]': '更新 Last.fm Now Playing',
            'now-playing-from-lx': '從 LX Music 當前播放更新 Now Playing',
            'scrobble <artist> <title> <timestamp> [album]': '手動 Scrobble',
            'scrobble-from-lx': '從 LX Music 當前播放 Scrobble',
            'recent [user]': '查看最近播放記錄',
            'info <artist> <title>': '歌曲詳細資訊',
            'similar <artist>': '相似藝人推薦',
            'top-tracks [artist]': '熱門歌曲',
            'config-check': '檢查 Last.fm 設定',
        },
        'note': 'Scrobble / Now Playing 需要設定 LASTFM_API_KEY 等環境變數',
    }

ACTIONS = {
    'config-check': lambda: cmd_config_check(),
    'now-playing': lambda: cmd_now_playing(_arg(1, ''), _arg(2, ''), _arg(3, '')),
    'now-playing-from-lx': cmd_now_playing_from_lx,
    'scrobble': lambda: cmd_scrobble(_arg(1, ''), _arg(2, ''), int(_arg(3, '0')), _arg(4, '')),
    'scrobble-from-lx': cmd_scrobble_from_lx,
    'recent': lambda: cmd_recent(_arg(1, '')),
    'info': lambda: cmd_info(_arg(1, ''), _arg(2, '')),
    'similar': lambda: cmd_similar(_arg(1, '')),
    'top-tracks': lambda: cmd_top_tracks(_arg(1, '')),
    'help': cmd_help,
}

def _arg(idx, default=''):
    args = sys.argv[2:]
    return args[idx] if idx < len(args) else default

def main():
    if len(sys.argv) < 2:
        print(json.dumps({'error': '請指定操作', 'actions': list(ACTIONS.keys())}, ensure_ascii=False))
        return

    action = sys.argv[1]
    handler = ACTIONS.get(action)
    if not handler:
        print(json.dumps({'error': f'未知操作: {action}', 'actions': list(ACTIONS.keys())}, ensure_ascii=False))
        return

    result = handler()
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
