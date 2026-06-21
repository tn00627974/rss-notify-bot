"""Discord Slash Commands：訂閱中心管理指令。

職責：將使用者輸入轉換成 admin_repository 的呼叫，並負責 Discord 互動的回覆格式。
不直接操作 asyncpg，所有資料庫邏輯都委派給 admin_repository。

新增/查詢的訂閱會在下次 poll 週期（≤5 分鐘）自動生效；
為了即時回饋，成功變更後會主動呼叫 reload_now() 立即重載一次。
"""

import logging
from typing import Awaitable, Callable, Optional
from urllib.parse import urlparse

import discord
import feedparser
from discord import app_commands

from .admin_repository import (
    get_or_create_platform_id,
    insert_rss_source,
    insert_target,
    link_rss_target,
    list_rss_sources,
    list_targets,
)

PLATFORM_CHOICES = [
    app_commands.Choice(name="Discord", value="discord"),
    app_commands.Choice(name="LINE", value="line"),
    app_commands.Choice(name="Feishu/Lark", value="feishu"),
]


async def _require_pgsql_mode(
    interaction: discord.Interaction, is_pgsql_mode: Callable[[], bool]
) -> bool:
    if is_pgsql_mode():
        return True
    await interaction.response.send_message(
        "❌ 此指令僅支援 SUBSCRIPTIONS_SOURCE=pgsql 模式", ephemeral=True
    )
    return False


def _is_valid_rss_feed(url: str) -> bool:
    """驗證網址是否能被解析成合法的 RSS/Atom Feed。"""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False
    try:
        feed = feedparser.parse(url)
    except Exception:
        return False
    return bool(feed.get("version")) or bool(feed.get("entries"))


def register_admin_commands(
    tree: app_commands.CommandTree,
    *,
    get_dsn: Callable[[], str],
    is_pgsql_mode: Callable[[], bool],
    reload_now: Callable[[], Awaitable[None]],
) -> None:
    """將 /指令 註冊到指定的 CommandTree。"""

    @tree.error
    async def on_admin_command_error(
        interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            message = "❌ 你沒有權限執行此指令（需要「管理伺服器」權限）"
        else:
            logging.exception("Slash command 執行錯誤", exc_info=error)
            message = f"❌ 發生錯誤：{error}"

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    @tree.command(name="rss_add", description="新增一個 RSS 來源")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(url="RSS Feed 網址", name="顯示名稱（推播訊息標頭）")
    async def rss_add(interaction: discord.Interaction, url: str, name: str) -> None:
        if not await _require_pgsql_mode(interaction, is_pgsql_mode):
            return
        await interaction.response.defer(ephemeral=True) # 延遲回覆，避免 Discord 3 秒超時
        if not _is_valid_rss_feed(url):
            await interaction.followup.send("❌ RSS 網址驗證失敗，請確認網址是否為合法的 RSS/Atom Feed", ephemeral=True)
            return
        try:
            new_id = await insert_rss_source(get_dsn(), url, name)
        except Exception as exc:
            logging.exception("rss_add 失敗")
            await interaction.followup.send(f"❌ 新增失敗：{exc}", ephemeral=True)
            return

        await reload_now()
        await interaction.followup.send(
            f"✅ 已新增 RSS 來源 #{new_id}：{name}\n下一步可用 `/subscribe` 將它訂閱到推播目標",
            ephemeral=True,
        )

    @tree.command(name="rss_list", description="列出目前已設定的 RSS 來源")
    @app_commands.describe(keyword="依顯示名稱篩選（可留空列出全部）")
    async def rss_list(
        interaction: discord.Interaction, keyword: Optional[str] = None
    ) -> None:
        if not await _require_pgsql_mode(interaction, is_pgsql_mode):
            return
        await interaction.response.defer(ephemeral=True)
        try:
            rows = await list_rss_sources(get_dsn(), query=keyword, limit=25)
        except Exception as exc:
            logging.exception("rss_list 失敗")
            await interaction.followup.send(f"❌ 查詢失敗：{exc}", ephemeral=True)
            return

        if not rows:
            await interaction.followup.send("目前沒有任何 RSS 來源", ephemeral=True)
            return

        lines = [
            f"#{r['id']} {'✅' if r['is_active'] else '⏸️'} {r['display_name']} — {r['rss_url']}"
            for r in rows
        ]
        text = "\n".join(lines)
        if len(text) > 1900:
            text = text[:1900] + "\n…（已截斷，請用 keyword 縮小範圍）"
        await interaction.followup.send(f"```\n{text}\n```", ephemeral=True)

    @tree.command(name="target_add", description="新增一個推播目標")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(
        platform="推播平台",
        external_id="頻道 ID / LINE 群組 ID（Discord 平台留空則使用目前頻道）",
        mention_user="發送時要 @ 提及的 Discord 使用者（僅 discord 平台適用）",
        description="備註說明",
    )
    @app_commands.choices(platform=PLATFORM_CHOICES)
    async def target_add(
        interaction: discord.Interaction,
        platform: app_commands.Choice[str],
        external_id: Optional[str] = None,
        mention_user: Optional[discord.User] = None,
        description: Optional[str] = None,
    ) -> None:
        if not await _require_pgsql_mode(interaction, is_pgsql_mode):
            return

        platform_name = platform.value
        if not external_id:
            if platform_name == "discord" and interaction.channel_id:
                external_id = str(interaction.channel_id)
            else:
                await interaction.response.send_message(
                    f"❌ {platform_name} 平台必須提供 external_id", ephemeral=True
                )
                return

        await interaction.response.defer(ephemeral=True)
        try:
            dsn = get_dsn()
            platform_id = await get_or_create_platform_id(dsn, platform_name)
            new_id = await insert_target(
                dsn,
                platform_id,
                external_id,
                str(mention_user.id) if mention_user else None,
                description,
            )
        except Exception as exc:
            logging.exception("target_add 失敗")
            await interaction.followup.send(f"❌ 新增失敗：{exc}", ephemeral=True)
            return

        await reload_now()
        await interaction.followup.send(
            f"✅ 已新增推播目標 #{new_id}（{platform_name} / {external_id}）\n"
            "下一步可用 `/subscribe` 將 RSS 來源訂閱到此目標",
            ephemeral=True,
        )

    @tree.command(name="subscribe", description="將 RSS 來源訂閱到推播目標")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(rss_source="RSS 來源", target="推播目標")
    async def subscribe(
        interaction: discord.Interaction, rss_source: int, target: int
    ) -> None:
        if not await _require_pgsql_mode(interaction, is_pgsql_mode):
            return
        await interaction.response.defer(ephemeral=True)
        try:
            await link_rss_target(get_dsn(), rss_source, target)
        except Exception as exc:
            logging.exception("subscribe 失敗")
            await interaction.followup.send(f"❌ 訂閱失敗：{exc}", ephemeral=True)
            return

        await reload_now()
        await interaction.followup.send("✅ 訂閱成功，已立即套用", ephemeral=True)

    @subscribe.autocomplete("rss_source")
    async def rss_source_autocomplete(
        interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[int]]:
        if not is_pgsql_mode():
            return []
        rows = await list_rss_sources(get_dsn(), query=current or None, limit=25)
        return [
            app_commands.Choice(name=f"#{r['id']} {r['display_name']}"[:100], value=r["id"])
            for r in rows
        ]

    @subscribe.autocomplete("target")
    async def target_autocomplete(
        interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[int]]:
        if not is_pgsql_mode():
            return []
        rows = await list_targets(get_dsn(), query=current or None, limit=25)
        return [
            app_commands.Choice(
                name=f"#{r['id']} [{r['platform']}] {r['description'] or r['external_id']}"[:100],
                value=r["id"],
            )
            for r in rows
        ]
