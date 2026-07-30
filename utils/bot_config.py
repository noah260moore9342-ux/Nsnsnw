"""
bot_config.py
All bot settings loaded from DB first, fallback to .env
Admin can change everything from inside the bot!
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Static (never change from bot) ────────────────────────────────────────────
BOT_TOKEN    = os.getenv("BOT_TOKEN", "8746962237:AAE2UTwDhsnlbB_U8HQI9QJ0VWX0_HmDtok")
ADMIN_IDS    = list(map(int, os.getenv("ADMIN_IDS", "5416091579").split(",")))
DATABASE_URL = os.getenv("DATABASE_URL", "bot.db")
API_ID       = int(os.getenv("API_ID", "36772021"))
API_HASH     = os.getenv("API_HASH", "9f0cdb1047c9042567a40ee221df330f")

# ── Dynamic (changeable from bot admin panel) ──────────────────────────────────

async def get(key: str, fallback: str = "") -> str:
    """Get a setting from DB, fallback to .env or default."""
    try:
        import aiosqlite
        async with aiosqlite.connect(DATABASE_URL) as db:
            r = await (await db.execute(
                "SELECT value FROM settings WHERE key=?", (key,)
            )).fetchone()
            if r and r[0]:
                return r[0]
    except Exception:
        pass
    return fallback


async def set(key: str, value: str):
    """Save a setting to DB."""
    import aiosqlite
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, value))
        await db.commit()


# ── Convenience getters ────────────────────────────────────────────────────────

async def upi_id() -> str:
    return await get("upi_id", os.getenv("UPI_ID", "imvishal739@fam"))

async def upi_name() -> str:
    return await get("upi_name", os.getenv("UPI_NAME", "VISHAL KUMAR"))

async def support_group() -> str:
    return await get("support_group", os.getenv("SUPPORT_GROUP", "@indsocialhub"))

async def admin_username() -> str:
    return await get("admin_username", os.getenv("ADMIN_USERNAME", "@BOTMAKERGARVIT"))

async def log_channel_id() -> int:
    v = await get("log_channel_id", os.getenv("LOG_CHANNEL_ID", "-1003589850886"))
    try:
        return int(v)
    except Exception:
        return 0

async def log_channel_link() -> str:
    return await get("log_channel_link", os.getenv("LOG_CHANNEL_LINK", "https://t.me/indsocialhub"))

async def bot_name() -> str:
    return await get("bot_name", "DELUX AccountBot")

async def force_join_channels() -> list:
    """Returns list of {"id": int, "link": str}"""
    raw = await get("force_join_channels", "")
    if not raw.strip():
        return []
    channels = []
    for entry in raw.split("||"):
        entry = entry.strip()
        if "::" not in entry:
            continue
        parts = entry.split("::", 1)
        try:
            channels.append({"id": int(parts[0].strip()), "link": parts[1].strip()})
        except Exception:
            pass
    return channels

async def add_force_join_channel(ch_id: int, ch_link: str):
    channels = await force_join_channels()
    # Remove if already exists
    channels = [c for c in channels if c["id"] != ch_id]
    channels.append({"id": ch_id, "link": ch_link})
    raw = "||".join(f"{c['id']}::{c['link']}" for c in channels)
    await set("force_join_channels", raw)

async def remove_force_join_channel(ch_id: int):
    channels = await force_join_channels()
    channels = [c for c in channels if c["id"] != ch_id]
    raw = "||".join(f"{c['id']}::{c['link']}" for c in channels)
    await set("force_join_channels", raw)
