---
name: lx-music-control
description: 控制 LX Music（洛雪音樂）播放器。當用戶要求播放/暫停/切歌/調整音量/查詢當前播放時使用。
agent_created: true
---

# LX Music Control Skill

控制 LX Music（洛雪音樂桌面版）播放器。

## 觸發場景

- 播放控制：播放、暫停、下一首、上一首
- 音量調節：大聲啲、細聲啲、靜音
- 進度控制：跳到幾多秒
- 查詢：而家播緊咩歌、歌手、歌詞
- 搜歌：搜索指定歌曲（打開搜索結果）
- 收藏/取消收藏

## 可用命令

```bash
# 播放控制
python scripts/lx_api.py play
python scripts/lx_api.py pause
python scripts/lx_api.py toggle-play
python scripts/lx_api.py next
python scripts/lx_api.py prev

# 音量
python scripts/lx_api.py volume 70       # 0-100
python scripts/lx_api.py mute true       # true/false

# 進度
python scripts/lx_api.py seek 120        # 跳到 2:00

# 查詢
python scripts/lx_api.py status          # 完整狀態
python scripts/lx_api.py current-song    # 精簡版
python scripts/lx_api.py lyric           # LRC 歌詞
python scripts/lx_api.py lyric-all       # 所有歌詞

# 搜歌（打開 LX Music 搜索結果，手動揀版本播放）
python scripts/lx_api.py search-play "歌名" "歌手"

# 收藏
python scripts/lx_api.py collect
python scripts/lx_api.py uncollect
```

## 對話示例

**用戶：** 「下一首」
→ 執行 `python scripts/lx_api.py next` → 回覆「已跳至下一首」

**用戶：** 「而家播緊咩？」
→ 執行 `python scripts/lx_api.py current-song` → 讀取結果並轉述

**用戶：** 「大聲啲」
→ 執行 `python scripts/lx_api.py volume 70` → 回覆「已調到 70」

**用戶：** 「播七里香」
→ 執行 `python scripts/lx_api.py search-play "七里香" "周杰倫"`
→ 回覆「已幫你搜索《七里香》，請喺 LX Music 揀選版本播放」

## 智能推薦（需 Last.fm API Key）

根據當前播放歌曲，用 Last.fm 搵相似歌曲推薦並播放。

**前置：** 去 https://www.last.fm/api/account/create 免費申請 API Key

```bash
# 用環境變數
set LASTFM_API_KEY=your_key_here
python scripts/recommend_next.py

# 或者直接傳 key
python scripts/recommend_next.py your_key_here
```

流程：
1. 攞 LX Music 當前播放嘅歌曲 + 歌手
2. 用 Last.fm 搵相似藝人嘅熱門歌
3. 隨機揀一首推薦
4. 用 `search-play` 搜歌

### 對話示例

**用戶：** 「推薦下一首」
→ 執行 `python scripts/recommend_next.py`
→ 回覆「推薦播放: 不為誰而作的歌 - 林俊杰（相似於林俊杰熱門歌曲），請喺 LX Music 揀選版本播放 🎵」

## 注意事項

1. LX Music 必須已開啟「開放 API 服務」（設定 > 開放 API），默認端口 23330
2. **search-play 只係打開 LX Music 嘅搜索結果頁面**，需要你手動㩒一下揀版本先會播（LX Music 官方 API 限制）
3. 所有 script 執行路徑：skill 目錄下嘅 `scripts/` folder
4. 操作前建議先 `status` 確認 LX Music 在線
