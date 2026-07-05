"""
LX Music 搜歌直接播放（跳過結果選擇）
用公開搜尋 API 拎到歌曲 ID，然後直接調用 music/play 即播

用法：
  python scripts/search_direct.py "歌名" [歌手]
  
示例：
  python scripts/search_direct.py "別為我好" "許靖韻"
  python scripts/search_direct.py "莎士比亞的天分" "林俊杰"
"""

import sys
import json
import urllib.request
import urllib.parse
import subprocess

# 搜尋引擎配置（按優先度排列 — kg 酷狗排第一）
SOURCES = {
    'kg': {  # 酷狗音樂（默認）
        'name': '酷狗',
        'search_url': 'https://songsearch.kugou.com/song_search_v2?keyword={query}&page=1&pagesize=5',
        'headers': {'User-Agent': 'Mozilla/5.0'},
        'parse': lambda data: [
            {
                'hash': s.get('FileHash', ''),
                'name': s.get('SongName', ''),
                'singer': s.get('SingerName', ''),
                'albumName': s.get('AlbumName', ''),
                'duration': int(s.get('Duration', 0)),
                'interval': f"{int(s.get('Duration', 0)) // 60}:{int(s.get('Duration', 0)) % 60:02d}",
            }
            for s in data.get('data', {}).get('lists', [])
        ],
        'play_params': lambda info: {
            'name': info['name'],
            'singer': info['singer'],
            'source': 'kg',
            'hash': info['hash'],
            'songmid': info['hash'],
            'albumName': info['albumName'],
            'interval': info['interval'],
            'types': [{"type": "128k"}, {"type": "320k"}],
        }
    },
    'wy': {  # 網易雲音樂（fallback）
        'name': '網易雲',
        'search_url': 'https://music.163.com/api/search/get?s={query}&type=1&limit=3',
        'headers': {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://music.163.com/'},
        'parse': lambda data: [
            {
                'songmid': str(s['id']),
                'name': s['name'],
                'singer': s['artists'][0]['name'] if s.get('artists') else '',
                'albumName': s.get('album', {}).get('name', ''),
                'interval': f"{s.get('duration', 0) // 60000}:{(s.get('duration', 0) % 60000) // 1000:02d}",
            }
            for s in data.get('result', {}).get('songs', [])
        ],
        'play_params': lambda info: {
            'name': info['name'],
            'singer': info['singer'],
            'source': 'wy',
            'songmid': info['songmid'],
            'albumName': info['albumName'],
            'interval': info['interval'],
            'types': [{"type": "128k"}, {"type": "320k"}],
        }
    },
    'tx': {  # QQ 音樂（fallback）
        'name': 'QQ音樂',
        'search_url': 'https://c.y.qq.com/splcloud/fcgi-bin/smartbox_new.fcg?key={query}&format=json',
        'headers': {'User-Agent': 'Mozilla/5.0'},
        'parse': lambda data: [
            {
                'songmid': s.get('mid', ''),
                'strMediaMid': s.get('id', ''),
                'name': s.get('name', ''),
                'singer': s.get('singer', ''),
            }
            for s in data.get('data', {}).get('song', {}).get('itemlist', [])
        ],
        'play_params': lambda info: {
            'name': info['name'],
            'singer': info['singer'],
            'source': 'tx',
            'songmid': info['strMediaMid'],
            'strMediaMid': info['strMediaMid'],
            'types': [{"type": "128k"}, {"type": "320k"}],
        }
    },
}


def search_song(song_name, artist=''):
    """多引擎搜歌，返回第一個 match 嘅結果"""
    results = []
    for source_key, source in SOURCES.items():
        # 先用歌名搜（唔加 artist，避免干擾搜尋結果）
        url = source['search_url'].format(query=urllib.parse.quote(song_name))
        try:
            req = urllib.request.Request(url, headers=source['headers'])
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            songs = source['parse'](data)

            # 如果有 artist，優先 match 歌手名
            if artist:
                matched = [s for s in songs if artist.lower() in s.get('singer', '').lower()]
                if matched:
                    songs = matched

            if songs:
                best = songs[0]
                # 驗證 duration：酷狗有時回傳錯誤 hash，duration 少過 2分鐘嘅 skip
                dur = best.get('duration', 0)
                if source_key == 'kg' and isinstance(dur, (int, float)) and 0 < dur < 120:
                    # Duration 太短，可能係錯 hash，跳過
                    continue
                best['_source'] = source_key
                best['_source_name'] = source['name']
                results.append(best)
        except Exception as e:
            results.append({'_source': source_key, '_source_name': source['name'],
                           'error': str(e)[:50]})

    # 優先返有結果嘅
    for r in results:
        if 'error' not in r and r.get('name'):
            return r
    # 全部失敗，返第一個有結果嘅（就算有 error 都照出）
    for r in results:
        if r.get('name'):
            return r
    return results[0] if results else {'error': '所有引擎搜尋失敗'}


def play_song(info):
    """用 music/play Scheme URL 直接播放"""
    source_key = info.get('_source', 'wy')
    source_config = SOURCES.get(source_key, SOURCES['wy'])
    params = source_config['play_params'](info)
    params['playLater'] = False

    data = urllib.parse.quote(json.dumps(params, ensure_ascii=False))
    url = f'lxmusic://music/play?data={data}'

    try:
        subprocess.run(['cmd', '/c', 'start', url], check=False, timeout=5)
        return {'ok': True, 'source': info.get('_source_name', '?'), 'song': info.get('name', '?'),
                'singer': info.get('singer', '?'), 'scheme': url}
    except Exception as e:
        return {'error': str(e)}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({'error': '請輸入歌名', 'usage': 'search_direct.py <歌名> [歌手]'},
                        ensure_ascii=False))
        return

    song_name = sys.argv[1]
    artist = sys.argv[2] if len(sys.argv) > 2 else ''

    print(json.dumps({'step': 'search', 'query': f'{song_name} {artist}'.strip()},
                     ensure_ascii=False))

    result = search_song(song_name, artist)
    if result.get('error'):
        print(json.dumps(result, ensure_ascii=False))
        return

    print(json.dumps({'step': 'found', 'source': result.get('_source_name'),
                      'name': result.get('name'), 'singer': result.get('singer'),
                      'id': result.get('songmid')}, ensure_ascii=False))

    play_result = play_song(result)
    print(json.dumps(play_result, ensure_ascii=False))


if __name__ == '__main__':
    main()
