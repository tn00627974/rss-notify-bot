# Plan: 訂閱來源可切換模式（JSON / PostgreSQL）

## TL;DR
在 `.env` 新增 `SUBSCRIPTIONS_SOURCE` 開關，讓 `bot.py` 的 `_async_main()` 依此決定呼叫同步的 `load_subscriptions()`（JSON）或非同步的 `load_subscriptions_from_db()`（PgSQL）。`Subscription` dataclass 與下游（RssPollingService、notifiers）完全不動。

---

## Tasks

### Task 1 — `.env` + `.env.example`
新增兩個環境變數：
- `SUBSCRIPTIONS_SOURCE=json`（預設值，json | pgsql）
- `DATABASE_URL=`（空值，pgsql 模式必填）

### Task 2 — `requirements.txt`
新增一行：`asyncpg==0.30.0`

### Task 3 — `rss_center/config.py`（主要改動）
新增 async 函式 `load_subscriptions_from_db(dsn: str) -> List[Subscription]`：
1. 用 `asyncpg.connect(dsn)` 取得連線
2. 執行 JOIN 查詢（rss_source_target + rss_source + target + platform）
3. 依 platform 欄位分流：
   - discord → channel_id=int(external_id), mention_user_id=int(...)
   - line → target_id=external_id
   - feishu → webhook_url=external_id
4. 回傳 `List[Subscription]`（與 JSON 模式相同輸出）

核心 SQL：
```sql
SELECT rs.rss_url, rs.display_name, p.name AS platform,
       t.external_id, t.mention_user_id
FROM rss_source_target rst
JOIN rss_source rs ON rs.id = rst.rss_source_id
JOIN target     t  ON t.id  = rst.target_id
JOIN platform   p  ON p.id  = t.platform_id
WHERE rs.is_active = TRUE
```

### Task 4 — `bot.py` `_async_main()`（最小改動）
將第 112 行：
```python
subscriptions = load_subscriptions(get_env_var("SUBSCRIPTIONS_FILE"))
```
改為：
```python
source = os.getenv("SUBSCRIPTIONS_SOURCE", "json").strip().lower()
if source == "pgsql":
    subscriptions = await load_subscriptions_from_db(get_env_var("DATABASE_URL"))
else:
    subscriptions = load_subscriptions(get_env_var("SUBSCRIPTIONS_FILE"))
```
同時在 import 行新增 `load_subscriptions_from_db`。

### Task 5 — `db/schema.sql`（新增檔案）
建立 db/ 資料夾並放入使用者的 DDL + seed INSERT SQL。

---

## Relevant Files
- `rss_center/config.py` — 新增 `load_subscriptions_from_db()`
- `bot.py` 第 112 行 `_async_main()` — 新增來源分流邏輯
- `.env` / `.env.example` — 新增兩個環境變數
- `requirements.txt` — 新增 asyncpg
- `db/schema.sql` — 新建

## Decisions
- asyncpg（純 async）優於 psycopg3，因為整個 bot 已是 asyncio 架構
- `Subscription` dataclass 不改動，確保下游零影響
- JSON 路徑完全不動，既有測試不受影響
