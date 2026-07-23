# 多源快訊 Bot

![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![Discord.py](https://img.shields.io/badge/Discord.py-2.5.0-5865F2?logo=discord&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

多平台 RSS 訂閱推播 Bot，支援 **Discord、LINE、飛書（Feishu）** 三大平台。
每 5 分鐘自動輪詢 RSS Feed（Yahoo 台股、YouTube 等），偵測新文章後推播到指定頻道，以 ID 去重避免重複推播。

![](/assets/Rss-bot-preview-1.jpg)

---

## 目錄

- [功能特色](#功能特色)
- [架構概覽](#架構概覽)
- [快速開始](#快速開始)
- [訂閱設定](#訂閱設定)
- [環境變數](#環境變數)
- [CLI 指令](#cli-指令)
- [部署指南](#部署指南)
- [開發與測試](#開發與測試)
- [常見問題](#常見問題)
- [依賴套件](#依賴套件)

---

## 功能特色

| 功能 | 說明 |
|------|------|
| 多平台推播 | 同時推送至 Discord、LINE、飛書，任意組合 |
| 自動輪詢 | 每 5 分鐘抓取一次 RSS，無需手動觸發 |
| 啟動去重 | 啟動時預載已讀 ID，重啟後不洗版 |
| 批量推送 | 多則訊息合併為單次 API 呼叫，降低請求頻率 |
| 雙資料來源 | 支援本地 JSON 檔或 PostgreSQL 資料庫切換 |
| YouTube 支援 | 自動辨識 YouTube RSS，格式化影片通知 |
| Discord @提及 | 推播時可自動 @ 指定成員 |
| HTTP 健康檢查 | 內建 `/health` 端點，供 Render 等平台存活偵測 |

---

## 架構概覽

```
bot.py                    # 程式入口，生命週期管理
└── rss_center/
    ├── config.py         # 設定載入（JSON / PostgreSQL）
    ├── models.py         # Subscription dataclass
    ├── formatters.py     # RSS 條目 → 文字訊息
    ├── notifiers.py      # BaseNotifier、NotificationRouter
    ├── batch_queue.py    # 批量隊列（數量/超時雙觸發）
    ├── batch_notifier.py # DiscordBatchNotifier、LineBatchNotifier、FeishuBatchNotifier
    └── service.py        # RSS 輪詢、去重、分派
```

資料流：`config → models → service → router → batch_notifier → 各平台 API`

---

## 快速開始

### 1. 建立虛擬環境並安裝依賴

```bash
# Windows PowerShell
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 設定環境變數

複製範本並填入必要的值：

```bash
cp .env.example .env
```

最小設定（JSON 模式）：

```env
DISCORD_TOKEN=your_discord_bot_token
SUBSCRIPTIONS_SOURCE=json
SUBSCRIPTIONS_FILE=subscriptions.json
```

### 3. 設定訂閱來源

編輯 `subscriptions.json`，詳見[訂閱設定](#訂閱設定)一節。

### 4. 發送測試訊息

```bash
python bot.py --test "Bot 連線測試"
```

訊息出現在目標頻道即代表設定正確。

### 5. 正式啟動

```bash
python bot.py
```

出現以下日誌代表啟動成功：

```
[INFO] Primed 50 items from https://tw.stock.yahoo.com/rss?category=tw-market
[INFO] Shard ID None has connected to Gateway
[INFO] Health check server running on port 10000
```

> **注意：** 啟動時會先預載現有 RSS 條目，僅推播啟動後**新出現**的文章。

---

## 訂閱設定

### subscriptions.json 格式

```json
[
  {
    "rss_url": "https://tw.stock.yahoo.com/rss?category=tw-market",
    "display_name": "台股市場",
    "targets": [
      {
        "platform": "discord",
        "channel_id": 123456789012345678,
        "mention_user_id": 987654321098765432
      },
      {
        "platform": "line",
        "target_id": "Uxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
      },
      {
        "platform": "feishu",
        "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx"
      }
    ]
  }
]
```

### 支援的平台值

| 平台 | 可用 platform 值 | 必填欄位 |
|------|-----------------|---------|
| Discord | `discord`、`dc` | `channel_id`；`mention_user_id` 可選 |
| LINE | `line`、`linebot`、`line-bot` | `target_id` |
| 飛書 | `feishu`、`lark` | `webhook_url` |

新增 RSS 來源只需在此檔案加入新項目，無需修改程式碼。

---

## 環境變數

| 變數名稱 | 說明 | 必填 |
|---------|------|------|
| `DISCORD_TOKEN` | Discord Bot Token | ✅ |
| `SUBSCRIPTIONS_SOURCE` | 資料來源：`json`（預設）或 `pgsql` | 否 |
| `SUBSCRIPTIONS_FILE` | JSON 訂閱設定路徑，預設 `subscriptions.json` | JSON 模式必填 |
| `DATABASE_URL` | PostgreSQL 連線字串（DSN） | pgsql 模式必填 |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Messaging API Channel Access Token | LINE 平台必填 |
| `FEISHU_WEBHOOK_URL` | 飛書 Webhook URL（全域預設） | 飛書平台必填 |
| `PORT` | HTTP 健康檢查埠號，預設 `10000` | Render 必填 |

---

## CLI 指令

```bash
# 正式啟動（持續輪詢）
python bot.py

# 測試：推播一則訊息到所有訂閱目標
python bot.py --test "測試訊息內容"

# 測試：僅推播到 LINE 目標
python bot.py --test-line "LINE 測試"

# 測試：推播最新 YouTube 影片到訂閱目標
python bot.py --test-yt

# 開啟 DEBUG 等級日誌
python bot.py --debug
```

---

## 部署指南

### Render（推薦）

1. 在 [Render](https://render.com/) 建立 **Web Service**，連接 GitHub Repository
2. 設定啟動命令：`python bot.py`
3. 在 Environment 頁籤填入所有必要環境變數
4. 健康檢查路徑設為 `/health`

Render 免費方案支援 24/7 長期運行，依賴 `PORT` 環境變數和 `/health` 端點。

### Docker

```bash
# 建置映像
docker build -t rss-notify-bot .

# 執行（使用 .env 檔案）
docker run -d --name rss-bot --env-file .env rss-notify-bot

# 查看日誌
docker logs -f rss-bot
```

或使用 docker-compose：

```bash
docker-compose up -d      # 背景執行
docker-compose logs -f    # 查看日誌
docker-compose down       # 停止
```

### Oracle Cloud（Always Free）

參考專案根目錄的 `Oracle Cloud 佈署.md`。

### Railway

Railway 自 2020/12/08 起不再提供完全免費方案，每月有 $5 免費額度。
部署方式：連接 GitHub Repository，設定環境變數後自動偵測 `python bot.py` 啟動。

---

## 開發與測試

### 執行測試套件

```bash
python -m pytest tests/
```

### 新增 RSS 來源

只需在 `subscriptions.json` 加入新項目，無需修改程式碼。

### 新增通知平台

1. 在 `rss_center/notifiers.py` 新增繼承 `BaseNotifier` 的類別
2. 在 `rss_center/batch_notifier.py` 新增繼承 `BaseBatchNotifier` 的子類別
3. 在 `rss_center/config.py` 的 `normalize_platform()` 加入平台別名
4. 在 `bot.py` 的 `_async_main()` 中的 `NotificationRouter` 字典裡註冊

---

## 常見問題

**Q: 啟動後為什麼沒有立刻推播？**
> 設計行為。啟動時會預載現有條目到 `seen_ids_map`，僅推播啟動後新出現的文章，避免重啟洗版。

**Q: Discord Bot 顯示 `Forbidden` 錯誤？**
> 確認 Bot 已加入目標伺服器，且對目標頻道擁有「View Channel」和「Send Messages」權限。

**Q: LINE 訊息未收到？**
> 確認 `LINE_CHANNEL_ACCESS_TOKEN` 正確，且 `target_id` 是有效的 User ID 或 Group ID。

**Q: 如何取得 LINE Group ID？**
> 使用 `line_userid_webhook.py` 工具，詳見檔案內說明。

**Q: 如何切換為 PostgreSQL 資料來源？**
> 設定 `SUBSCRIPTIONS_SOURCE=pgsql` 並提供 `DATABASE_URL`，資料表結構詳見 `db/schema.sql`。

**Q: 如何確認 Bot 正常運行？**
> 檢查日誌是否每 5 分鐘出現 `Primed` 或 `poll_loop` 相關訊息，或呼叫 `/health` 端點確認回應 `OK`。

---

## 依賴套件

| 套件 | 版本 | 用途 |
|------|------|------|
| discord.py | 2.5.0 | Discord Bot 框架與連線管理 |
| feedparser | 6.0.11 | RSS / Atom Feed 解析 |
| aiohttp | 3.13.5 | 非同步 HTTP 客戶端與健康檢查伺服器 |
| python-dotenv | 1.0.1 | 載入 `.env` 環境變數 |
| asyncpg | 0.30.0 | PostgreSQL 非同步客戶端 |
| pytest | 9.0.3 | 測試框架 |

---

## 授權

MIT License

## 致謝

- [discord.py](https://discordpy.readthedocs.io/)
- [feedparser](https://feedparser.readthedocs.io/)
- [Render](https://render.com/)
