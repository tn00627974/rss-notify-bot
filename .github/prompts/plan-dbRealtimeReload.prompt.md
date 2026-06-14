## Plan: 每次 poll 週期自動重載訂閱

**TL;DR**：在每次輪詢開始前從 DB/JSON 重新載入訂閱，利用現有的 `poll_loop` 節奏（每 5 分鐘）做到「準即時」更新，不需加 Discord 指令，不需引入新依賴。

---

**Steps**

### Phase 1 — `service.py` 加入 reload 機制

1. `__init__` 新增可選參數 `reload_fn: Optional[Callable[[], Awaitable[List[Subscription]]]] = None`，存為 `self._reload_fn`

2. 新增 `_reload_subscriptions()` 方法：
   - 呼叫 `self._reload_fn()` 取得新訂閱列表
   - 比對 `new_grouped.keys()` 與現有 `self.seen_ids_map.keys()`，找出**新增的 RSS URL**
   - 對新 URL 執行 `feedparser.parse` 預載已讀 ID（避免新訂閱加入後立刻洗版）
   - 用 try/except 包住全程：失敗時 `logging.warning` 並繼續用舊設定

3. `poll_loop` 在每輪 `for rss_url in self.subscriptions_by_feed:` **之前**插入一行：`await self._reload_subscriptions()`（若 `_reload_fn` 為 None 則 no-op）

### Phase 2 — `bot.py` 傳入 reload_fn

4. 在 `_async_main` 的資料來源判斷區塊，根據模式建立對應的 async `reload_fn`：
   - **pgsql 模式**：`async def reload_fn(): return await load_subscriptions_from_db(dsn)`
   - **json 模式**：`async def reload_fn(): return load_subscriptions(subs_file)`（同步包成 async）

5. 建立 `RssPollingService` 時加入 `reload_fn=reload_fn`

---

**Relevant files**
- `rss_center/service.py` — 修改 `__init__`、`poll_loop`；新增 `_reload_subscriptions()`
- `bot.py` — 修改 `_async_main` 的資料載入段落

**Verification**
1. 修改 DB `rss_source.display_name` → 等待下一個 poll 週期（≤5 分鐘）→ 確認推播訊息出現新名稱
2. 新增一個 `rss_source_target` → 等待下一個 poll 週期 → 確認新頻道開始收到訊息，且**不洗版**（舊文章不重推）
3. `reload_fn` 拋例外時（如 DB 斷線）→ 確認日誌出現 `WARNING: 重載訂閱失敗，沿用舊設定` 且 Bot 繼續正常運作
4. 執行 `python -m pytest tests/` 確認現有測試不受影響

**Decisions**
- 更新頻率跟著 `POLL_INTERVAL_SECONDS`（5 分鐘），不需額外 timer
- json 模式也受益：直接改 `subscriptions.json` 即可，同樣 5 分鐘內生效
- 不修改 `seen_ids_map` 的清理邏輯（移除的訂閱只是停止推播，舊 key 留著無害）
- 不引入 DB 連線池（每次 reload 開新連線，5 分鐘一次可接受）
