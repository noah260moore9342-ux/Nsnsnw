from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import utils.bot_config as cfg


async def check_joined(bot: Bot, user_id: int) -> list:
    """Returns list of channels user has NOT joined."""
    channels   = await cfg.force_join_channels()
    not_joined = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch["id"], user_id)
            if member.status in ("left", "kicked", "banned"):
                not_joined.append(ch)
        except Exception:
            not_joined.append(ch)
    return not_joined


def force_join_kb(not_joined: list) -> InlineKeyboardMarkup:
    buttons = []
    for i, ch in enumerate(not_joined, 1):
        buttons.append([InlineKeyboardButton(text=f"📢 Join Channel {i}", url=ch["link"])])
    buttons.append([InlineKeyboardButton(
        text="✅ I've Joined — Check Again",
        callback_data="check_joined"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
