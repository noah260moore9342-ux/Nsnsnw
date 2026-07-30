from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

import database as db
import utils.bot_config as cfg
from keyboards import user_main_kb, country_list_kb, account_detail_kb, developer_kb, force_join_kb

router = Router()

_DEV      = "@BOTMAKERGARVIT"
_DEV_LINK = "https://t.me/BOTMAKERGARVIT"


async def banned_check(user_id, obj) -> bool:
    if await db.is_banned(user_id):
        text = "🚫 <b>You are banned!</b>\n\nContact support."
        if isinstance(obj, Message):
            await obj.answer(text, parse_mode="HTML")
        else:
            await obj.answer("🚫 You are banned!", show_alert=True)
        return True
    return False


async def maintenance_check(user_id, obj) -> bool:
    from config import ADMIN_IDS
    if user_id in ADMIN_IDS:
        return False
    if await db.is_maintenance():
        m = await db.get_maintenance_msg()
        if isinstance(obj, Message):
            await obj.answer(m)
        else:
            await obj.answer(m, show_alert=True)
        return True
    return False


async def force_join_check(bot, user_id, obj) -> bool:
    channels = await cfg.force_join_channels()
    if not channels:
        return False
    from utils.force_join import check_joined
    not_joined = await check_joined(bot, user_id)
    if not not_joined:
        return False
    text = "🔒 <b>Access Restricted!</b>\n\nJoin our channel(s) first:\n\n👇 Join then tap <b>I've Joined</b>"
    kb   = force_join_kb(not_joined)
    if isinstance(obj, Message):
        await obj.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        await obj.message.answer(text, parse_mode="HTML", reply_markup=kb)
        await obj.answer()
    return True


@router.message(CommandStart())
async def start(msg: Message, bot: Bot):
    await db.upsert_user(msg.from_user.id, msg.from_user.username or "", msg.from_user.full_name)

    from config import ADMIN_IDS
    if msg.from_user.id in ADMIN_IDS:
        from keyboards import admin_main_kb
        return await msg.answer("👑 <b>Welcome back, Admin!</b>", parse_mode="HTML", reply_markup=admin_main_kb())

    if await maintenance_check(msg.from_user.id, msg): return
    if await banned_check(msg.from_user.id, msg): return
    if await force_join_check(bot, msg.from_user.id, msg): return

    ch_link  = await cfg.log_channel_link()
    support  = await cfg.support_group()
    bot_name = await cfg.bot_name()

    await msg.answer(
        f"🔥 <b>Welcome to {bot_name}!</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🛒 Verified Telegram accounts\n"
        f"🌍 Multiple countries\n"
        f"💳 UPI Payment · Auto OTP\n"
        f"💰 Wallet system available\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        + (f"📢 {ch_link}\n" if ch_link else "")
        + (f"💬 {support}\n" if support else "")
        + f"\nTap <b>Browse Accounts</b> to start! 👇",
        parse_mode="HTML",
        reply_markup=user_main_kb(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "check_joined")
async def check_joined_cb(cq: CallbackQuery, bot: Bot):
    from utils.force_join import check_joined
    not_joined = await check_joined(bot, cq.from_user.id)
    if not_joined:
        await cq.message.edit_text(
            "❌ <b>Still not joined!</b>\n\nJoin all then check again 👇",
            parse_mode="HTML",
            reply_markup=force_join_kb(not_joined)
        )
        await cq.answer("❌ Not joined yet!", show_alert=True)
    else:
        try:
            await cq.message.delete()
        except Exception:
            pass
        await cq.message.answer(
            "✅ <b>Access Granted!</b>\n\nTap Browse Accounts! 👇",
            parse_mode="HTML",
            reply_markup=user_main_kb()
        )
        await cq.answer("✅ Welcome!")


@router.message(F.text == "🛒 Browse Accounts")
async def browse(msg: Message, bot: Bot):
    if await maintenance_check(msg.from_user.id, msg): return
    if await banned_check(msg.from_user.id, msg): return
    if await force_join_check(bot, msg.from_user.id, msg): return

    stock = await db.get_country_stock()
    if not stock:
        return await msg.answer("😔 <b>No accounts available right now.</b>", parse_mode="HTML")
    await msg.answer("🌍 <b>Select Country</b>", parse_mode="HTML", reply_markup=country_list_kb(stock))


@router.callback_query(F.data == "back_countries")
async def back_countries(cq: CallbackQuery):
    stock = await db.get_country_stock()
    if not stock:
        return await cq.message.edit_text("😔 No accounts available.")
    await cq.message.edit_text("🌍 <b>Select Country</b>", parse_mode="HTML", reply_markup=country_list_kb(stock))


@router.callback_query(F.data.startswith("country:"))
async def show_country(cq: CallbackQuery, bot: Bot):
    if await maintenance_check(cq.from_user.id, cq): return
    if await banned_check(cq.from_user.id, cq): return

    country  = cq.data.split(":", 1)[1]
    accounts = await db.get_available_by_country(country)
    if not accounts:
        return await cq.answer("😔 No accounts left!", show_alert=True)

    acc          = accounts[0]
    masked       = f"{acc['number'][:4]}****{acc['number'][-3:]}"
    bal          = await db.get_balance(cq.from_user.id)
    can_wallet   = bal >= acc["price"]

    await cq.message.edit_text(
        f"{acc['country_flag']} <b>{acc['country']} Account</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 <b>Number:</b> <code>{masked}</code>\n"
        f"💰 <b>Price:</b> ₹{acc['price']:.2f}\n"
        f"📝 <b>Info:</b> {acc['description'] or 'Fresh account, ready to use'}\n"
        f"📦 <b>Stock:</b> {len(accounts)} available\n"
        f"💼 <b>Your Balance:</b> ₹{bal:.2f}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ UPI Payment · Auto OTP · Instant Delivery",
        parse_mode="HTML",
        reply_markup=account_detail_kb(acc["id"], can_use_wallet=can_wallet)
    )


@router.callback_query(F.data == "back_main")
async def back_main(cq: CallbackQuery):
    try:
        await cq.message.delete()
    except Exception:
        pass


@router.message(F.text == "📦 My Orders")
async def my_orders(msg: Message, bot: Bot):
    if await maintenance_check(msg.from_user.id, msg): return
    if await banned_check(msg.from_user.id, msg): return

    orders = await db.get_user_orders(msg.from_user.id)
    if not orders:
        return await msg.answer("📦 <b>No orders yet!</b>", parse_mode="HTML")

    text = "📦 <b>Your Orders</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for o in orders[:10]:
        e = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(o["status"], "❔")
        text += f"{e} ₹{o['amount']:.2f} · {o['status'].upper()} · {o['created_at'][:10]}\n"
    await msg.answer(text, parse_mode="HTML")


@router.message(F.text == "📢 Channel")
async def channel(msg: Message):
    link = await cfg.log_channel_link()
    await msg.answer(f"📢 <b>Our Channel</b>\n\n{link or 'Not set yet'}", parse_mode="HTML", disable_web_page_preview=False)


@router.message(F.text == "💬 Support")
async def support(msg: Message):
    s = await cfg.support_group()
    a = await cfg.admin_username()
    await msg.answer(f"💬 <b>Support</b>\n\n📩 {s}\n👤 {a}", parse_mode="HTML")


@router.message(F.text == "ℹ️ How It Works")
async def how_it_works(msg: Message):
    await msg.answer(
        "ℹ️ <b>How It Works</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "1️⃣ Browse accounts by country\n"
        "2️⃣ Buy via UPI QR <b>or</b> Wallet\n"
        "3️⃣ Upload payment screenshot\n"
        "4️⃣ Admin approves → Account delivered\n"
        "5️⃣ Tap <b>Get Latest OTP</b> — instant! ⚡\n\n"
        "💰 <b>Wallet:</b> Deposit → Buy instantly!\n\n"
        "✅ Safe · Fast · Auto OTP",
        parse_mode="HTML"
    )


@router.message(F.text == "👨‍💻 Developer")
async def developer(msg: Message):
    await msg.answer(
        f"👨‍💻 <b>Bot Developer</b>\n\nBuilt by <b>{_DEV}</b>\n\nWant a custom bot? Contact! 👇",
        parse_mode="HTML",
        reply_markup=developer_kb()
    )
