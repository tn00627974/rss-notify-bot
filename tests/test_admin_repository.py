"""Tests for rss_center/admin_repository.py

涵蓋範圍：
- insert_rss_source()          INSERT 並回傳新 id
- list_rss_sources()            查詢全部 / 依 keyword 過濾
- get_or_create_platform_id()   既有平台直接回傳 id；不存在則自動建立
- insert_target()                INSERT 並回傳新 id；UniqueViolation 轉換為友善錯誤
- list_targets()                  查詢全部 / 依 keyword 過濾
- link_rss_target()               INSERT 並回傳新 id；UniqueViolation/ForeignKeyViolation 轉換為友善錯誤
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import asyncpg

# 直接執行 (python tests/test_admin_repository.py) 時確保根目錄在 sys.path
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rss_center.admin_repository import (
    get_or_create_platform_id,
    insert_rss_source,
    insert_target,
    link_rss_target,
    list_rss_sources,
    list_targets,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_conn(fetchrow_result=None, fetch_result=None):
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=fetchrow_result)
    conn.fetch = AsyncMock(return_value=fetch_result or [])
    conn.close = AsyncMock()
    return conn


def _patched_connect(conn):
    return patch(
        "rss_center.admin_repository.asyncpg.connect", AsyncMock(return_value=conn)
    )


# ---------------------------------------------------------------------------
# insert_rss_source
# ---------------------------------------------------------------------------


class TestInsertRssSource(unittest.IsolatedAsyncioTestCase):
    async def test_returns_new_id(self):
        conn = _mock_conn(fetchrow_result={"id": 42})
        with _patched_connect(conn):
            new_id = await insert_rss_source("dsn", "https://x.com/rss", "顯示名稱")

        self.assertEqual(new_id, 42)
        conn.fetchrow.assert_awaited_once()
        conn.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# list_rss_sources
# ---------------------------------------------------------------------------


class TestListRssSources(unittest.IsolatedAsyncioTestCase):
    async def test_without_query_lists_all(self):
        rows = [{"id": 1, "rss_url": "u", "display_name": "n", "is_active": True}]
        conn = _mock_conn(fetch_result=rows)
        with _patched_connect(conn):
            result = await list_rss_sources("dsn")

        self.assertEqual(result, rows)
        sql = conn.fetch.call_args.args[0]
        self.assertNotIn("ILIKE", sql)

    async def test_with_query_filters_by_display_name(self):
        conn = _mock_conn(fetch_result=[])
        with _patched_connect(conn):
            await list_rss_sources("dsn", query="台股")

        sql, param = conn.fetch.call_args.args[0], conn.fetch.call_args.args[1]
        self.assertIn("ILIKE", sql)
        self.assertEqual(param, "%台股%")


# ---------------------------------------------------------------------------
# get_or_create_platform_id
# ---------------------------------------------------------------------------


class TestGetOrCreatePlatformId(unittest.IsolatedAsyncioTestCase):
    async def test_returns_existing_id_without_insert(self):
        conn = _mock_conn(fetchrow_result={"id": 1})
        with _patched_connect(conn):
            platform_id = await get_or_create_platform_id("dsn", "discord")

        self.assertEqual(platform_id, 1)
        self.assertEqual(conn.fetchrow.await_count, 1)

    async def test_creates_platform_when_missing(self):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(side_effect=[None, {"id": 3}])
        conn.close = AsyncMock()
        with _patched_connect(conn):
            platform_id = await get_or_create_platform_id("dsn", "feishu")

        self.assertEqual(platform_id, 3)
        self.assertEqual(conn.fetchrow.await_count, 2)


# ---------------------------------------------------------------------------
# insert_target
# ---------------------------------------------------------------------------


class TestInsertTarget(unittest.IsolatedAsyncioTestCase):
    async def test_returns_new_id(self):
        conn = _mock_conn(fetchrow_result={"id": 7})
        with _patched_connect(conn):
            new_id = await insert_target("dsn", 1, "123456", "999", "備註")

        self.assertEqual(new_id, 7)

    async def test_unique_violation_raises_friendly_error(self):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(side_effect=asyncpg.UniqueViolationError("dup"))
        conn.close = AsyncMock()
        with _patched_connect(conn):
            with self.assertRaises(RuntimeError):
                await insert_target("dsn", 1, "123456", None, None)

        conn.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# list_targets
# ---------------------------------------------------------------------------


class TestListTargets(unittest.IsolatedAsyncioTestCase):
    async def test_without_query_lists_all(self):
        rows = [{"id": 1, "external_id": "123", "description": "d", "platform": "discord"}]
        conn = _mock_conn(fetch_result=rows)
        with _patched_connect(conn):
            result = await list_targets("dsn")

        self.assertEqual(result, rows)
        sql = conn.fetch.call_args.args[0]
        self.assertNotIn("ILIKE", sql)

    async def test_with_query_filters_by_description_or_external_id(self):
        conn = _mock_conn(fetch_result=[])
        with _patched_connect(conn):
            await list_targets("dsn", query="阿母")

        sql, param = conn.fetch.call_args.args[0], conn.fetch.call_args.args[1]
        self.assertIn("ILIKE", sql)
        self.assertEqual(param, "%阿母%")


# ---------------------------------------------------------------------------
# link_rss_target
# ---------------------------------------------------------------------------


class TestLinkRssTarget(unittest.IsolatedAsyncioTestCase):
    async def test_returns_new_id(self):
        conn = _mock_conn(fetchrow_result={"id": 9})
        with _patched_connect(conn):
            new_id = await link_rss_target("dsn", 1, 2)

        self.assertEqual(new_id, 9)

    async def test_unique_violation_raises_friendly_error(self):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(side_effect=asyncpg.UniqueViolationError("dup"))
        conn.close = AsyncMock()
        with _patched_connect(conn):
            with self.assertRaises(RuntimeError):
                await link_rss_target("dsn", 1, 2)

    async def test_foreign_key_violation_raises_friendly_error(self):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(side_effect=asyncpg.ForeignKeyViolationError("fk"))
        conn.close = AsyncMock()
        with _patched_connect(conn):
            with self.assertRaises(RuntimeError):
                await link_rss_target("dsn", 999, 2)


if __name__ == "__main__":
    unittest.main()
