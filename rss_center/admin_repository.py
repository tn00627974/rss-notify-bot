"""Discord 指令的資料庫寫入/查詢層。

職責：純粹的 asyncpg 存取，不依賴 discord，方便獨立測試。
對應資料表：rss_source、platform、target、rss_source_target（見 db/schema.sql）。
"""

import asyncpg
from typing import List, Optional


async def insert_rss_source(dsn: str, rss_url: str, display_name: str) -> int:
    """新增 RSS 來源，回傳新建立的 rss_source.id。"""
    conn = await asyncpg.connect(dsn)
    try:
        row = await conn.fetchrow(
            "INSERT INTO rss_source (rss_url, display_name) VALUES ($1, $2) RETURNING id",
            rss_url,
            display_name,
        )
        return row["id"]
    finally:
        await conn.close()


async def list_rss_sources(
    dsn: str, query: Optional[str] = None, limit: int = 25
) -> List[asyncpg.Record]:
    """查詢現有 RSS 來源，可用 query 過濾 display_name（供 /rss_list 與 autocomplete 共用）。"""
    conn = await asyncpg.connect(dsn)
    try:
        if query:
            return await conn.fetch(
                "SELECT id, rss_url, display_name, is_active FROM rss_source "
                "WHERE display_name ILIKE $1 ORDER BY id DESC LIMIT $2",
                f"%{query}%",
                limit,
            )
        return await conn.fetch(
            "SELECT id, rss_url, display_name, is_active FROM rss_source "
            "ORDER BY id DESC LIMIT $1",
            limit,
        )
    finally:
        await conn.close()


async def get_or_create_platform_id(dsn: str, platform_name: str) -> int:
    """依平台名稱查詢 platform.id，不存在則自動建立。"""
    conn = await asyncpg.connect(dsn)
    try:
        row = await conn.fetchrow(
            "SELECT id FROM platform WHERE name = $1", platform_name
        )
        if row:
            return row["id"]
        row = await conn.fetchrow(
            "INSERT INTO platform (name) VALUES ($1) RETURNING id", platform_name
        )
        return row["id"]
    finally:
        await conn.close()


async def insert_target(
    dsn: str,
    platform_id: int,
    external_id: str,
    mention_user_id: Optional[str],
    description: Optional[str],
) -> int:
    """新增推播目標，回傳新建立的 target.id。"""
    conn = await asyncpg.connect(dsn)
    try:
        row = await conn.fetchrow(
            "INSERT INTO target (platform_id, external_id, mention_user_id, description) "
            "VALUES ($1, $2, $3, $4) RETURNING id",
            platform_id,
            external_id,
            mention_user_id,
            description,
        )
        return row["id"]
    except asyncpg.UniqueViolationError:
        raise RuntimeError("此平台與 external_id 的組合已經存在")
    finally:
        await conn.close()


async def list_targets(
    dsn: str, query: Optional[str] = None, limit: int = 25
) -> List[asyncpg.Record]:
    """查詢現有推播目標，可用 query 過濾 description（供 /subscribe autocomplete 使用）。"""
    conn = await asyncpg.connect(dsn)
    try:
        if query:
            return await conn.fetch(
                "SELECT t.id, t.external_id, t.description, p.name AS platform "
                "FROM target t JOIN platform p ON p.id = t.platform_id "
                "WHERE t.description ILIKE $1 OR t.external_id ILIKE $1 "
                "ORDER BY t.id DESC LIMIT $2",
                f"%{query}%",
                limit,
            )
        return await conn.fetch(
            "SELECT t.id, t.external_id, t.description, p.name AS platform "
            "FROM target t JOIN platform p ON p.id = t.platform_id "
            "ORDER BY t.id DESC LIMIT $1",
            limit,
        )
    finally:
        await conn.close()


async def link_rss_target(dsn: str, rss_source_id: int, target_id: int) -> int:
    """建立 RSS 來源與推播目標的訂閱關聯，回傳新建立的 rss_source_target.id。"""
    conn = await asyncpg.connect(dsn)
    try:
        row = await conn.fetchrow(
            "INSERT INTO rss_source_target (rss_source_id, target_id) "
            "VALUES ($1, $2) RETURNING id",
            rss_source_id,
            target_id,
        )
        return row["id"]
    except asyncpg.UniqueViolationError:
        raise RuntimeError("此訂閱關聯已經存在")
    except asyncpg.ForeignKeyViolationError:
        raise RuntimeError("找不到對應的 RSS 來源或推播目標，請確認 ID 是否正確")
    finally:
        await conn.close()
