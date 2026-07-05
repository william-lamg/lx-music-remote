"""
LX Music 智能推薦下一首歌
根據當前播放歌曲，用 Last.fm 搵相似歌曲推薦並播放

用法：
  python scripts/recommend_next.py              # 用環境變數 LASTFM_API_KEY
  python scripts/recommend_next.py YOUR_API_KEY  # 直接傳 API Key

需要 Last.fm API Key（免費）：
  https://www.last.fm/api/account/create
"""

import sys
import os
import json
import urllib.request
import urllib.parse
import random
import subprocess

API_KEY = os.environ.get('LASTFM_API_KEY', '')
API_URL = 'https://ws.audioscrobbler.com/2.0/'

# LX Music API
LX_HOST = 'http://127.0.0.1:23330'


def lx_get(path):
    try:
        req = urllib.request.Request(LX_HOST + path)
        resp = urllib.request.urlopen(req, timeout=5)
        return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {'error': str(e)}


def lastfm_get(method, params):
    params['method'] = method
    params['api_key'] = API_KEY
    params['format'] = 'json'
    url = API_URL + '?' + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'LX-Music-Remote/1.0'})
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {'error': str(e)}


def get_current_song():
    """從 LX Music 攞當前歌曲"""
    data = lx_get('/status')
    if 'error' in data:
        return data
    return {
        'song': data.get('name', ''),
        'artist': data.get('singer', ''),
        'status': data.get('status'),
    }


def get_recommendations(artist, song=''):
    """用 Last.fm 攞推薦歌曲"""
    results = []

    # 方法 1：攞相似藝人嘅熱門歌
    similar = lastfm_get('artist.getSimilar', {'artist': artist, 'limit': 3})
    if 'error' not in similar:
        for sa in similar.get('similarartists', {}).get('artist', []):
            sa_name = sa.get('name', '')
            if not sa_name:
                continue
            tops = lastfm_get('artist.getTopTracks', {'artist': sa_name, 'limit': 2})
            if 'error' not in tops:
                for t in tops.get('toptracks', {}).get('track', []):
                    name = t.get('name', '')
                    artist_name = t.get('artist', {}).get('name', '')
                    if name and artist_name:
                        results.append({'song': name, 'artist': artist_name,
                                       'source': f'相似於 {sa_name}'})

    # 方法 2：攞當前歌手嘅其他熱門歌
    tops = lastfm_get('artist.getTopTracks', {'artist': artist, 'limit': 5})
    if 'error' not in tops:
        for t in tops.get('toptracks', {}).get('track', []):
            name = t.get('name', '')
            artist_name = t.get('artist', {}).get('name', '')
            if name and artist_name and name != song:
                results.append({'song': name, 'artist': artist_name,
                               'source': f'{artist} 熱門歌曲'})

    return results


def search_play(song, artist):
    """用 LX Music search-play 搜歌"""
    params = {'name': song, 'playLater': False}
    if artist:
        params['singer'] = artist
    data = urllib.parse.quote(json.dumps(params, ensure_ascii=False))
    url = 'lxmusic://music/searchPlay?data=' + data
    try:
        subprocess.run(['cmd', '/c', 'start', url], check=False, timeout=5)
        return True
    except Exception:
        return False


def main():
    global API_KEY

    if len(sys.argv) > 1:
        API_KEY = sys.argv[1]

    if not API_KEY:
        print(json.dumps({
            'error': '需要 Last.fm API Key',
            'hint': '去 https://www.last.fm/api/account/create 免費申請',
            'usage': 'recommend_next.py YOUR_API_KEY',
            'env': '或設定環境變數 LASTFM_API_KEY'
        }, ensure_ascii=False))
        return

    # Step 1: 攞當前歌曲
    current = get_current_song()
    if 'error' in current:
        print(json.dumps(current, ensure_ascii=False))
        return
    if current.get('status') != 'playing' and current.get('status') != 'paused':
        print(json.dumps({'error': 'LX Music 未在播放'}, ensure_ascii=False))
        return

    artist = current.get('artist', '')
    song = current.get('song', '')
    print(json.dumps({'step': 1, 'action': '當前歌曲',
                      'song': song, 'artist': artist}, ensure_ascii=False))

    # Step 2: 用 Last.fm 攞推薦
    recs = get_recommendations(artist, song)
    if not recs:
        print(json.dumps({'error': '無法獲取推薦', 'hint': '檢查 Last.fm API Key 是否正確'}, ensure_ascii=False))
        return

    print(json.dumps({'step': 2, 'action': '找到推薦',
                      'count': len(recs), 'recommendations': recs[:5]}, ensure_ascii=False))

    # Step 3: 隨機揀一首推薦歌
    pick = random.choice(recs[:8])
    print(json.dumps({'step': 3, 'action': '推薦播放',
                      'pick': pick}, ensure_ascii=False))

    # Step 4: 搜歌
    ok = search_play(pick['song'], pick['artist'])
    if ok:
        print(json.dumps({
            'ok': True,
            'message': f"推薦播放: {pick['song']} - {pick['artist']}",
            'song': pick['song'],
            'artist': pick['artist'],
            'source': pick['source'],
            'hint': '請喺 LX Music 揀選版本播放'
        }, ensure_ascii=False))
    else:
        print(json.dumps({'error': '搜歌失敗'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
