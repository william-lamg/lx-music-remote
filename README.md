# LX Music 遙控器

一個網頁版嘅 LX Music（洛雪音樂）遙控器，支援區域網手機控制。

> 基於 [LX Music 開放 API](https://lxmusic.toside.cn/desktop/open-api)（v2.7.0+）開發

## 功能

- 📱 **手機遙控** — 同一 Wi-Fi 用手機控制電腦嘅 LX Music
- 🎵 **播放控制** — 上一首、播放/暫停、下一首、進度跳轉
- 🔊 **音量管理** — 音量滑桿、靜音切換
- 📃 **歌詞顯示** — LRC 歌詞即時同步，當前唱到邊行 Highlight
- ⚡ **實時更新** — 支援 SSE 推送，狀態即時同步
- 🔄 **自動監測** — 開 LX Music 自動啟動，關 LX Music 自動停止

## 用法

### 快速啟動（推薦）
雙擊 `LX音樂遙控.bat`，會自動：
1. 等 LX Music 啟動
2. 啟動代理伺服器
3. 打開瀏覽器遙控頁面
4. 關 LX Music 時自動停止

### 手機控制
1. 電腦行起個遙控器
2. 手機（同一 Wi-Fi）打開 Terminal 顯示嘅網址
3. 開始控制 🎶

## 檔案說明

| 檔案 | 用途 |
|------|------|
| `LX音樂遙控.bat` | 雙擊啟動捷徑 |
| `LX音樂遙控.py` | 一體化 Python 應用（監測 + 代理 + 自動開關） |
| `lx-remote.html` | 遙控器網頁界面 |

## 技術細節

- 通過 LX Music Open API（v2.7.0+）控制播放器
- 使用 Python `http.server` 做 API 代理，解決 CORS 跨域問題
- SSE（Server-Sent Events）實現即時狀態推送
- 支援 `/status`、`/lyric`、`/subscribe-player-status` 等完整 API

## 授權

MIT
