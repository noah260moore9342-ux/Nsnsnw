import datetime
import utils.bot_config as cfg


def _half(number: str) -> str:
    n    = number.strip()
    half = len(n) // 2
    return n[:half] + "*" * (len(n) - half)


async def log_sale(bot, number, amount, country, flag, user_id, username, order_id):
    ch_id = await cfg.log_channel_id()
    if not ch_id:
        return
    now   = datetime.datetime.now().strftime("%d %b %Y %I:%M %p")
    uname = f"@{username}" if username else f"ID:{user_id}"
    text  = (
        f"💰 <b>NEW SALE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 <code>{_half(number)}</code>\n"
        f"{flag} {country}\n"
        f"💸 ₹{amount:.2f}\n"
        f"👤 {uname}\n"
        f"🕐 {now}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    try:
        await bot.send_message(ch_id, text, parse_mode="HTML")
    except Exception as e:
        print(f"[LOG ERROR] {e}")


async def log_otp(bot, number, otp, user_id, username):
    ch_id = await cfg.log_channel_id()
    if not ch_id:
        return
    now   = datetime.datetime.now().strftime("%d %b %Y %I:%M %p")
    uname = f"@{username}" if username else f"ID:{user_id}"
    text  = (
        f"🔐 <b>OTP DELIVERED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 <code>{_half(number)}</code>\n"
        f"👤 {uname}\n"
        f"🕐 {now}"
    )
    try:
        await bot.send_message(ch_id, text, parse_mode="HTML")
    except Exception:
        pass
