# LX Music Remote & Control Skill

LX Music（洛雪音樂）全套工具：**網頁遙控器** + **AI 智能體控制 Skill**

> 基於 [LX Music 開放 API](https://lxmusic.toside.cn/desktop/open-api)（v2.7.0+）開發

---

## 📱 網頁遙控器 — 用手機控制電腦播歌

一個無需安裝嘅 HTML 網頁，同一 Wi-Fi 用手機瀏覽器就可以控制 LX Music。

### 快速啟動
雙擊 `啟動遙控器.bat` 或執行：
```bash
python lx-remote-app.py
```

手機打開 Terminal 顯示嘅網址（例如 `http://192.168.1.100:8080/lx-remote.html`）就得。

### 功能
- 播放/暫停、上一首、下一首、進度跳轉
- 音量調節、靜音
- LRC 歌詞即時同步
- SSE 實時狀態推送
- 自動監測 LX Music 開關

---

## 🤖 AI 智能體控制 Skill — 用對話控制音樂

將 Skill 安裝到 WorkBuddy 後，AI 可以透過對話直接控制 LX Music：

### 安裝
```bash
# 將 lx-music-control 複製到 WorkBuddy Skills 目錄
cp -r lx-music-control ~/.workbuddy/skills/
```

### 可用命令

| 命令 | 說明 |
|------|------|
| `play` / `pause` / `toggle-play` | 播放控制 |
| `next` / `prev` | 切歌 |
| `volume 70` / `mute true` | 音量控制 |
| `seek 120` | 跳轉進度 |
| `status` / `current-song` | 查詢狀態 |
| `lyric` | 獲取歌詞 |
| `search-play "歌名" "歌手"` | 搜索並播放 |
| `collect` / `uncollect` | 收藏控制 |
| `recommend-next [api_key]` | 智能推薦下一首（需 Last.fm API Key） |

### 對話示例
> **你：** 「下一首」 → **AI：** 已跳至下一首 ✅
> **你：** 「而家播緊咩？」 → **AI：** 正在播放《演員》- 薛之謙
> **你：** 「推薦下一首」 → **AI：** 推薦播放《不為誰而作的歌》- 林俊杰

---

## 📂 檔案結構

```
├── lx-remote.html          # 網頁遙控器界面
├── lx-remote-app.py        # 一體化應用（監測+代理+自動開關）
├── 啟動遙控器.bat          # 雙擊啟動捷徑
├── lx-music-control/       # AI 智能體控制 Skill
│   ├── SKILL.md
│   └── scripts/
│       ├── lx_api.py           # LX Music 控制命令
│       ├── search_direct.py    # 搜歌即播（實驗性）
│       ├── recommend_next.py   # Last.fm 智能推薦
│       └── lastfm_api.py       # Last.fm Scrobble
└── README.md
```

## 授權

MIT
