import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN        = os.getenv("BOT_TOKEN", "8746962237:AAE2UTwDhsnlbB_U8HQI9QJ0VWX0_HmDtok")
ADMIN_IDS        = list(map(int, os.getenv("ADMIN_IDS", "5416091579").split(",")))
ADMIN_USERNAME   = os.getenv("ADMIN_USERNAME", "@BOTMAKERGARVIT")
LOG_CHANNEL_ID   = int(os.getenv("LOG_CHANNEL_ID", "-1003589850886"))
LOG_CHANNEL_LINK = os.getenv("LOG_CHANNEL_LINK", "https://t.me/indsocialhub")
SUPPORT_GROUP    = os.getenv("SUPPORT_GROUP", "@indsocialhub")
UPI_ID           = os.getenv("UPI_ID", "imvishal739@fam")
UPI_NAME         = os.getenv("UPI_NAME", "VISHAL KUMAR")
API_ID           = int(os.getenv("API_ID", "36772021"))
API_HASH         = os.getenv("API_HASH", "9f0cdb1047c9042567a40ee221df330f")
DATABASE_URL     = os.getenv("DATABASE_URL", "bot.db")
BOT_NAME         = "GARVIT AccountBot"

FORCE_JOIN_RAW = os.getenv("FORCE_JOIN_CHANNELS", "")

def get_force_join_channels():
    if not FORCE_JOIN_RAW.strip():
        return []
    channels = []
    for entry in FORCE_JOIN_RAW.split(","):
        entry = entry.strip()
        if ":" not in entry:
            continue
        idx     = entry.index(":")
        ch_id   = entry[:idx].strip()
        ch_link = entry[idx+1:].strip()
        try:
            channels.append({"id": int(ch_id), "link": ch_link})
        except Exception:
            pass
    return channels

FORCE_JOIN_CHANNELS = get_force_join_channels()
