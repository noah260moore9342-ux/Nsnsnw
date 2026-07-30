from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Filter

import database as db
from keyboards import (
    admin_main_kb, user_main_kb, cancel_kb,
    admin_account_kb, admin_approve_kb,
    admin_otp_kb, maintenance_kb, admin_deposit_kb
)
from config import ADMIN_IDS
from utils.logger import log_sale

router = Router()


class IsAdmin(Filter):
    async def __call__(self, obj) -> bool:
        return obj.from_user.id in ADMIN_IDS


# ── States ─────────────────────────────────────────────────────────────────────

class AddAccState(StatesGroup):
    number = State(); country = State(); price = State()
    password = State(); twofa = State(); session_str = State(); description = State()

class EditPriceState(StatesGroup):
    price = State()

class EditSessionState(StatesGroup):
    session = State()

class BroadcastState(StatesGroup):
    message = State()

class BanState(StatesGroup):
    user_input = State()   # admin types user_id to ban
    reason     = State()

class UnbanState(StatesGroup):
    user_input = State()

class MsgUserState(StatesGroup):
    user_input = State()
    message    = State()

class MaintenanceMsgState(StatesGroup):
    message = State()


# ── User Mode ──────────────────────────────────────────────────────────────────

@router.message(IsAdmin(), F.text == "🏠 User Mode")
async def user_mode(msg: Message):
    await msg.answer("👤 User mode.", reply_markup=user_main_kb())


# ── Add Account ────────────────────────────────────────────────────────────────

@router.message(IsAdmin(), F.text == "➕ Add Account")
async def add_start(msg: Message, state: FSMContext):
    await state.set_state(AddAccState.number)
    await msg.answer(
        "➕ <b>Add Account — Step 1/7</b>\n\n"
        "📱 Phone number (with country code):\n"
        "Example: <code>+917001234567</code>",
        parse_mode="HTML", reply_markup=cancel_kb()
    )

@router.message(IsAdmin(), AddAccState.number)
async def add_number(msg: Message, state: FSMContext):
    if msg.text == "❌ Cancel":
        await state.clear()
        return await msg.answer("Cancelled.", reply_markup=admin_main_kb())
    await state.update_data(number=msg.text.strip())
    await state.set_state(AddAccState.country)
    await msg.answer(
        "✅ Number saved!\n\n<b>Step 2/7 — Country + Flag:</b>\n\n"
        "Format: <code>🇮🇳 India</code>\n"
        "Examples: <code>🇺🇸 USA</code> · <code>🇷🇺 Russia</code> · <code>🇧🇩 Bangladesh</code>",
        parse_mode="HTML"
    )

@router.message(IsAdmin(), AddAccState.country)
async def add_country(msg: Message, state: FSMContext):
    if msg.text == "❌ Cancel":
        await state.clear()
        return await msg.answer("Cancelled.", reply_markup=admin_main_kb())
    parts   = msg.text.strip().split(None, 1)
    flag    = parts[0] if len(parts) == 2 else "🌍"
    country = parts[1] if len(parts) == 2 else msg.text.strip()
    await state.update_data(country=country, country_flag=flag)
    await state.set_state(AddAccState.price)
    await msg.answer(f"✅ {flag} {country}\n\n<b>Step 3/7 — Price (₹):</b>\nExample: <code>199</code>", parse_mode="HTML")

@router.message(IsAdmin(), AddAccState.price)
async def add_price(msg: Message, state: FSMContext):
    if msg.text == "❌ Cancel":
        await state.clear()
        return await msg.answer("Cancelled.", reply_markup=admin_main_kb())
    try:
        price = float(msg.text.strip())
    except ValueError:
        return await msg.answer("❌ Valid number daalo.")
    await state.update_data(price=price)
    await state.set_state(AddAccState.password)
    await msg.answer(f"✅ ₹{price:.2f}\n\n<b>Step 4/7 — Password</b> (ya <code>skip</code>):", parse_mode="HTML")

@router.message(IsAdmin(), AddAccState.password)
async def add_password(msg: Message, state: FSMContext):
    if msg.text == "❌ Cancel":
        await state.clear()
        return await msg.answer("Cancelled.", reply_markup=admin_main_kb())
    pw = "" if msg.text.strip().lower() == "skip" else msg.text.strip()
    await state.update_data(password=pw)
    await state.set_state(AddAccState.twofa)
    await msg.answer("✅ Password!\n\n<b>Step 5/7 — 2FA</b> (ya <code>skip</code>):", parse_mode="HTML")

@router.message(IsAdmin(), AddAccState.twofa)
async def add_twofa(msg: Message, state: FSMContext):
    if msg.text == "❌ Cancel":
        await state.clear()
        return await msg.answer("Cancelled.", reply_markup=admin_main_kb())
    twofa = "" if msg.text.strip().lower() == "skip" else msg.text.strip()
    await state.update_data(twofa=twofa)
    await state.set_state(AddAccState.session_str)
    await msg.answer("✅ 2FA!\n\n<b>Step 6/7 — Session String</b> (ya <code>skip</code>):", parse_mode="HTML")

@router.message(IsAdmin(), AddAccState.session_str)
async def add_session(msg: Message, state: FSMContext):
    if msg.text == "❌ Cancel":
        await state.clear()
        return await msg.answer("Cancelled.", reply_markup=admin_main_kb())
    sess = "" if msg.text.strip().lower() == "skip" else msg.text.strip()
    await state.update_data(session_str=sess)
    await state.set_state(AddAccState.description)
    await msg.answer("<b>Step 7/7 — Description</b> (ya <code>skip</code>):", parse_mode="HTML")

@router.message(IsAdmin(), AddAccState.description)
async def add_done(msg: Message, state: FSMContext):
    if msg.text == "❌ Cancel":
        await state.clear()
        return await msg.answer("Cancelled.", reply_markup=admin_main_kb())
    desc = "" if msg.text.strip().lower() == "skip" else msg.text.strip()
    d = await state.get_data()
    await state.clear()
    await db.add_account(
        number=d["number"], price=d["price"], country=d["country"],
        country_flag=d["country_flag"], password=d.get("password",""),
        twofa=d.get("twofa",""), session_str=d.get("session_str",""), description=desc
    )
    sess_status = "✅ Auto OTP" if d.get("session_str") else "⚠️ Manual OTP"
    await msg.answer(
        f"✅ <b>Account Added!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 <code>{d['number']}</code>\n"
        f"{d['country_flag']} {d['country']} · ₹{d['price']:.2f}\n"
        f"🔑 {d.get('password') or 'N/A'} · 🔐 {d.get('twofa') or 'N/A'}\n"
        f"📡 {sess_status} · 📝 {desc or 'No desc'}",
        parse_mode="HTML", reply_markup=admin_main_kb()
    )


# ── View Accounts ──────────────────────────────────────────────────────────────

@router.message(IsAdmin(), F.text == "📋 View Accounts")
async def view_accounts(msg: Message):
    accounts = await db.get_all_accounts()
    if not accounts:
        return await msg.answer("📋 Koi account nahi hai abhi.")
    avail = [a for a in accounts if a["status"] == "available"]
    sold  = [a for a in accounts if a["status"] == "sold"]
    await msg.answer(f"📋 <b>All Accounts</b>\n🟢 Available: {len(avail)}  ·  🔴 Sold: {len(sold)}", parse_mode="HTML")
    for acc in accounts[:20]:
        emoji = "🟢" if acc["status"] == "available" else "🔴"
        sess  = "📡✅" if acc.get("session_str") else "📡❌"
        await msg.answer(
            f"{emoji} <b>#{acc['id'][:8]}</b> · {acc['country_flag']} {acc['country']}\n"
            f"📱 <code>{acc['number']}</code>\n"
            f"💰 ₹{acc['price']:.2f} · {acc['status'].upper()} · {sess}\n"
            f"🔑 {acc['password'] or 'N/A'} · 🔐 {acc['twofa'] or 'N/A'}",
            parse_mode="HTML", reply_markup=admin_account_kb(acc["id"])
        )


# ── Account Actions ────────────────────────────────────────────────────────────

@router.callback_query(IsAdmin(), F.data.startswith("del_acc:"))
async def del_acc(cq: CallbackQuery):
    await db.delete_account(cq.data.split(":", 1)[1])
    await cq.message.edit_text("🗑 Account deleted.")
    await cq.answer("Deleted!")

@router.callback_query(IsAdmin(), F.data.startswith("edit_price:"))
async def edit_price_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(EditPriceState.price)
    await state.update_data(acc_id=cq.data.split(":", 1)[1])
    await cq.message.answer("✏️ Naya price enter karo:", reply_markup=cancel_kb())
    await cq.answer()

@router.message(IsAdmin(), EditPriceState.price)
async def edit_price_done(msg: Message, state: FSMContext):
    if msg.text == "❌ Cancel":
        await state.clear()
        return await msg.answer("Cancelled.", reply_markup=admin_main_kb())
    try:
        price = float(msg.text.strip())
    except ValueError:
        return await msg.answer("❌ Valid number daalo.")
    d = await state.get_data()
    await state.clear()
    await db.update_account(d["acc_id"], price=price)
    await msg.answer(f"✅ Price updated: ₹{price:.2f}", reply_markup=admin_main_kb())

@router.callback_query(IsAdmin(), F.data.startswith("edit_session:"))
async def edit_session_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(EditSessionState.session)
    await state.update_data(acc_id=cq.data.split(":", 1)[1])
    await cq.message.answer("🔑 Naya session string paste karo:\n(<code>clear</code> = remove)", parse_mode="HTML", reply_markup=cancel_kb())
    await cq.answer()

@router.message(IsAdmin(), EditSessionState.session)
async def edit_session_done(msg: Message, state: FSMContext):
    if msg.text == "❌ Cancel":
        await state.clear()
        return await msg.answer("Cancelled.", reply_markup=admin_main_kb())
    sess = "" if msg.text.strip().lower() == "clear" else msg.text.strip()
    d = await state.get_data()
    await state.clear()
    await db.update_account(d["acc_id"], session_str=sess)
    await msg.answer("✅ Session updated!" if sess else "✅ Session removed!", reply_markup=admin_main_kb())


# ── Pending Orders ─────────────────────────────────────────────────────────────

@router.message(IsAdmin(), F.text == "⏳ Pending Orders")
async def pending(msg: Message):
    orders = await db.get_pending_orders()
    if not orders:
        return await msg.answer("✅ Koi pending order nahi!")
    for o in orders:
        acc = await db.get_account(o["account_id"])
        await msg.answer(
            f"⏳ <b>Order #{o['id'][:8]}</b>\n"
            f"👤 @{o['username'] or 'N/A'} · <code>{o['user_id']}</code>\n"
            f"📱 <code>{acc['number'] if acc else 'N/A'}</code>\n"
            f"{acc['country_flag'] if acc else ''} {acc['country'] if acc else ''} · ₹{o['amount']:.2f}\n"
            f"📸 {'✅' if o.get('screenshot') else '❌ No screenshot'}\n"
            f"🗓 {o['created_at'][:19]}",
            parse_mode="HTML", reply_markup=admin_approve_kb(o["id"])
        )

@router.callback_query(IsAdmin(), F.data.startswith("admin_approve:"))
async def approve(cq: CallbackQuery, bot: Bot):
    order_id = cq.data.split(":", 1)[1]
    order    = await db.get_order(order_id)
    if not order or order["status"] != "pending":
        return await cq.answer("⚠️ Already processed.", show_alert=True)

    acc = await db.get_account(order["account_id"])
    await db.approve_order(order_id)
    await db.mark_account_sold(order["account_id"], order["user_id"])
    await db.update_user_stats(order["user_id"], order["amount"])
    session_id = await db.create_otp_session(order_id, order["user_id"], order["account_id"])

    from keyboards import reveal_number_kb
    try:
        await bot.send_message(
            order["user_id"],
            f"🎉 <b>Payment Approved!</b>\n\nOrder ₹{order['amount']:.2f} · {acc['country_flag']} {acc['country']}\n\n👇 Account details:",
            parse_mode="HTML", reply_markup=reveal_number_kb(order_id, session_id)
        )
    except Exception:
        pass

    await log_sale(bot, acc["number"], order["amount"], acc["country"], acc["country_flag"], order["user_id"], order["username"], order_id)

    try:
        await cq.message.edit_caption(caption=f"✅ Order approved! {acc['number']} delivered.", parse_mode="HTML")
    except Exception:
        await cq.message.edit_text(f"✅ Order approved! {acc['number']} delivered.")
    await cq.answer("✅ Approved!")

@router.callback_query(IsAdmin(), F.data.startswith("admin_reject:"))
async def reject(cq: CallbackQuery, bot: Bot):
    order_id = cq.data.split(":", 1)[1]
    order    = await db.get_order(order_id)
    if not order or order["status"] != "pending":
        return await cq.answer("⚠️ Already processed.", show_alert=True)
    await db.reject_order(order_id)
    try:
        await bot.send_message(order["user_id"], f"❌ <b>Order Rejected</b>\n\nPayment verify nahi ho payi.\nSupport se contact karo.", parse_mode="HTML")
    except Exception:
        pass
    try:
        await cq.message.edit_caption(caption="❌ Order rejected.")
    except Exception:
        await cq.message.edit_text("❌ Order rejected.")
    await cq.answer("❌ Rejected!")

@router.callback_query(IsAdmin(), F.data.startswith("admin_view_ss:"))
async def view_screenshot(cq: CallbackQuery, bot: Bot):
    order = await db.get_order(cq.data.split(":", 1)[1])
    if not order or not order.get("screenshot"):
        return await cq.answer("📸 Screenshot nahi mila!", show_alert=True)
    await bot.send_photo(cq.from_user.id, order["screenshot"], caption=f"📸 Order · @{order['username'] or 'N/A'}")
    await cq.answer()


# ── Pending Deposits ───────────────────────────────────────────────────────────

@router.message(IsAdmin(), F.text == "💳 Pending Deposits")
async def pending_deposits(msg: Message):
    deposits = await db.get_pending_deposits()
    if not deposits:
        return await msg.answer("✅ Koi pending deposit nahi!")
    for d in deposits:
        await msg.answer(
            f"💳 <b>Deposit #{d['id'][:8]}</b>\n"
            f"👤 @{d['username'] or 'N/A'} · <code>{d['user_id']}</code>\n"
            f"💰 Amount: ₹{d['amount']:.2f}\n"
            f"💸 Exact Paid: ₹{d['exact_amount']:.2f}\n"
            f"📸 {'✅ Screenshot' if d.get('screenshot') else '❌ No screenshot'}\n"
            f"🗓 {d['created_at'][:19]}",
            parse_mode="HTML", reply_markup=admin_deposit_kb(d["id"])
        )

@router.callback_query(IsAdmin(), F.data.startswith("dep_approve:"))
async def dep_approve(cq: CallbackQuery, bot: Bot):
    deposit_id = cq.data.split(":", 1)[1]
    dep = await db.get_deposit(deposit_id)
    if not dep or dep["status"] != "pending":
        return await cq.answer("⚠️ Already processed.", show_alert=True)
    await db.approve_deposit(deposit_id)
    bal = await db.get_balance(dep["user_id"])
    try:
        await bot.send_message(
            dep["user_id"],
            f"✅ <b>Deposit Approved!</b>\n\n"
            f"💰 ₹{dep['amount']:.2f} added to your wallet!\n"
            f"💼 New Balance: ₹{bal:.2f}",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await cq.message.edit_text(f"✅ Deposit ₹{dep['amount']:.2f} approved for <code>{dep['user_id']}</code>.", parse_mode="HTML")
    await cq.answer("✅ Deposit approved!")

@router.callback_query(IsAdmin(), F.data.startswith("dep_reject:"))
async def dep_reject(cq: CallbackQuery, bot: Bot):
    deposit_id = cq.data.split(":", 1)[1]
    dep = await db.get_deposit(deposit_id)
    if not dep or dep["status"] != "pending":
        return await cq.answer("⚠️ Already processed.", show_alert=True)
    await db.reject_deposit(deposit_id)
    try:
        await bot.send_message(dep["user_id"], f"❌ <b>Deposit Rejected</b>\n\n₹{dep['amount']:.2f} ka deposit verify nahi hua.", parse_mode="HTML")
    except Exception:
        pass
    await cq.message.edit_text(f"❌ Deposit rejected.")
    await cq.answer("❌ Rejected!")


# ── Statistics ─────────────────────────────────────────────────────────────────

@router.message(IsAdmin(), F.text == "📊 Statistics")
async def stats(msg: Message):
    s     = await db.get_stats()
    stock = await db.get_country_stock()
    c_txt = "\n".join(f"  {cs['flag']} {cs['country']}: {cs['count']} · ₹{cs['price']:.0f}" for cs in stock) or "  No stock"
    m_st  = "🔴 ON" if await db.is_maintenance() else "🟢 OFF"
    await msg.answer(
        f"📊 <b>Statistics</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Accounts  : {s['total_accounts']} (🟢{s['available']} 🔴{s['sold']})\n"
        f"👥 Users     : {s['users']} (🚫{s['banned']} banned)\n"
        f"💰 Revenue   : ₹{s['revenue']:.2f}\n"
        f"⏳ Pending   : {s['pending']} orders · {s.get('pending_deposits',0)} deposits\n"
        f"✅ Approved  : {s['approved_orders']} orders\n"
        f"🔧 Maint.    : {m_st}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🌍 <b>Stock:</b>\n{c_txt}",
        parse_mode="HTML"
    )


# ── User Management — Clean text list, no per-user buttons ─────────────────────

@router.message(IsAdmin(), F.text == "👥 User Management")
async def user_management(msg: Message):
    users = await db.get_all_users()
    if not users:
        return await msg.answer("👥 Koi user nahi hai.")

    # Send in chunks of 30 users per message
    header = f"👥 <b>All Users ({len(users)})</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    chunk  = ""
    count  = 0

    for u in users:
        banned = u.get("is_banned", False)
        status = "🚫" if banned else "✅"
        uname  = f"@{u['username']}" if u.get("username") else "No username"
        line   = (
            f"{status} <code>{u['user_id']}</code> · {uname}\n"
            f"   ₹{u.get('total_spent',0):.0f} spent · {u.get('total_orders',0)} orders"
            + (f" · <b>BANNED</b>" if banned else "") + "\n"
        )
        chunk += line
        count += 1
        if count % 25 == 0:
            await msg.answer(header + chunk, parse_mode="HTML")
            chunk = ""

    if chunk:
        await msg.answer(header + chunk, parse_mode="HTML")

    # Admin action instructions
    await msg.answer(
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b>Actions:</b>\n"
        "🚫 Ban: <code>/ban USER_ID reason</code>\n"
        "✅ Unban: <code>/unban USER_ID</code>\n"
        "📨 Message: <code>/msg USER_ID text</code>",
        parse_mode="HTML"
    )


# ── Ban / Unban via commands ───────────────────────────────────────────────────

@router.message(IsAdmin(), F.text.startswith("/ban "))
async def ban_cmd(msg: Message, bot: Bot):
    parts = msg.text.split(None, 2)
    if len(parts) < 2:
        return await msg.answer("Usage: <code>/ban USER_ID reason</code>", parse_mode="HTML")
    try:
        user_id = int(parts[1])
    except ValueError:
        return await msg.answer("❌ Valid user ID daalo.")
    reason = parts[2] if len(parts) > 2 else "No reason provided"
    await db.ban_user(user_id, reason)
    try:
        await bot.send_message(user_id, f"🚫 <b>You have been banned!</b>\n\nReason: {reason}", parse_mode="HTML")
    except Exception:
        pass
    await msg.answer(f"🚫 User <code>{user_id}</code> banned!\nReason: {reason}", parse_mode="HTML")


@router.message(IsAdmin(), F.text.startswith("/unban "))
async def unban_cmd(msg: Message, bot: Bot):
    parts = msg.text.split()
    if len(parts) < 2:
        return await msg.answer("Usage: <code>/unban USER_ID</code>", parse_mode="HTML")
    try:
        user_id = int(parts[1])
    except ValueError:
        return await msg.answer("❌ Valid user ID daalo.")
    await db.unban_user(user_id)
    try:
        await bot.send_message(user_id, "✅ <b>You have been unbanned!</b>\n\nYou can use the bot again.", parse_mode="HTML")
    except Exception:
        pass
    await msg.answer(f"✅ User <code>{user_id}</code> unbanned!", parse_mode="HTML")


@router.message(IsAdmin(), F.text.startswith("/msg "))
async def msg_cmd(msg: Message, bot: Bot):
    parts = msg.text.split(None, 2)
    if len(parts) < 3:
        return await msg.answer("Usage: <code>/msg USER_ID message text</code>", parse_mode="HTML")
    try:
        user_id = int(parts[1])
    except ValueError:
        return await msg.answer("❌ Valid user ID daalo.")
    text = parts[2]
    try:
        await bot.send_message(user_id, f"📨 <b>Admin Message:</b>\n\n{text}", parse_mode="HTML")
        await msg.answer(f"✅ Message sent to <code>{user_id}</code>!", parse_mode="HTML")
    except Exception:
        await msg.answer(f"❌ Send nahi hua — user ne bot block kiya hoga.")


# ── Order History ──────────────────────────────────────────────────────────────

@router.message(IsAdmin(), F.text == "📜 Order History")
async def order_history(msg: Message):
    orders = await db.get_all_orders(50)
    if not orders:
        return await msg.answer("📜 Koi order nahi hai.")
    text = "📜 <b>Last 50 Orders</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for o in orders:
        e = {"pending":"⏳","approved":"✅","rejected":"❌"}.get(o["status"],"❔")
        text += f"{e} @{o['username'] or 'N/A'} · ₹{o['amount']:.2f} · {o['created_at'][:10]}\n"
    await msg.answer(text, parse_mode="HTML")


# ── OTP Sessions ───────────────────────────────────────────────────────────────

@router.message(IsAdmin(), F.text == "🔐 OTP Sessions")
async def otp_sessions(msg: Message):
    sessions = await db.get_waiting_otp_sessions()
    if not sessions:
        return await msg.answer("🔐 Koi active OTP session nahi hai.")
    for s in sessions:
        acc = await db.get_account(s["account_id"])
        await msg.answer(
            f"🔐 <b>Session #{s['id'][:8]}</b>\n"
            f"📱 <code>{acc['number'] if acc else 'N/A'}</code>\n"
            f"👤 <code>{s['user_id']}</code>\n"
            f"📡 {'✅ Auto' if acc and acc.get('session_str') else '❌ Manual needed'}\n"
            f"🗓 {s['created_at'][:19]}",
            parse_mode="HTML", reply_markup=admin_otp_kb(s["id"])
        )


# ── Broadcast ──────────────────────────────────────────────────────────────────

@router.message(IsAdmin(), F.text == "📢 Broadcast")
async def broadcast_start(msg: Message, state: FSMContext):
    await state.set_state(BroadcastState.message)
    await msg.answer("📢 Sab users ko bhejne ke liye message type karo:", reply_markup=cancel_kb())

@router.message(IsAdmin(), BroadcastState.message)
async def broadcast_send(msg: Message, state: FSMContext, bot: Bot):
    if msg.text == "❌ Cancel":
        await state.clear()
        return await msg.answer("Cancelled.", reply_markup=admin_main_kb())
    await state.clear()
    users = await db.get_all_users()
    sent = failed = 0
    status_msg = await msg.answer(f"📢 Sending to {len(users)} users...")
    for u in users:
        try:
            await bot.send_message(u["user_id"], f"📢 <b>Admin Message:</b>\n\n{msg.text}", parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
    try:
        await status_msg.edit_text(f"✅ <b>Broadcast Done!</b>\n✅ Sent: {sent} · ❌ Failed: {failed}", parse_mode="HTML")
    except Exception:
        pass
    await msg.answer("Done!", reply_markup=admin_main_kb())


# ── Maintenance ────────────────────────────────────────────────────────────────

@router.message(IsAdmin(), F.text == "🔧 Maintenance")
async def maintenance_panel(msg: Message):
    is_on = await db.is_maintenance()
    m_msg = await db.get_maintenance_msg()
    await msg.answer(
        f"🔧 <b>Maintenance Mode</b>\n"
        f"Status: <b>{'🔴 ON' if is_on else '🟢 OFF'}</b>\n\n"
        f"📝 Message:\n<i>{m_msg}</i>",
        parse_mode="HTML", reply_markup=maintenance_kb(is_on)
    )

@router.callback_query(IsAdmin(), F.data == "maintenance_on")
async def maint_on(cq: CallbackQuery):
    await db.set_setting("maintenance", "1")
    await cq.message.edit_reply_markup(reply_markup=maintenance_kb(True))
    await cq.answer("🔴 Maintenance ON!", show_alert=True)

@router.callback_query(IsAdmin(), F.data == "maintenance_off")
async def maint_off(cq: CallbackQuery):
    await db.set_setting("maintenance", "0")
    await cq.message.edit_reply_markup(reply_markup=maintenance_kb(False))
    await cq.answer("🟢 Maintenance OFF!", show_alert=True)

@router.callback_query(IsAdmin(), F.data == "maintenance_edit_msg")
async def maint_edit(cq: CallbackQuery, state: FSMContext):
    await state.set_state(MaintenanceMsgState.message)
    await cq.message.answer("✏️ Naya maintenance message:", reply_markup=cancel_kb())
    await cq.answer()

@router.message(IsAdmin(), MaintenanceMsgState.message)
async def maint_msg_done(msg: Message, state: FSMContext):
    if msg.text == "❌ Cancel":
        await state.clear()
        return await msg.answer("Cancelled.", reply_markup=admin_main_kb())
    await state.clear()
    await db.set_setting("maintenance_msg", msg.text.strip())
    await msg.answer("✅ Message updated!", reply_markup=admin_main_kb())


# ── Manual OTP ─────────────────────────────────────────────────────────────────

class ManualOTPState(StatesGroup):
    otp = State()

@router.callback_query(IsAdmin(), F.data.startswith("manual_otp:"))
async def manual_otp_start(cq: CallbackQuery, state: FSMContext):
    session_id = cq.data.split(":", 1)[1]
    await state.set_state(ManualOTPState.otp)
    await state.update_data(session_id=session_id)
    await cq.message.answer(f"🔐 OTP enter karo session #{session_id[:8]} ke liye:", reply_markup=cancel_kb())
    await cq.answer()

@router.message(IsAdmin(), ManualOTPState.otp)
async def manual_otp_done(msg: Message, state: FSMContext, bot: Bot):
    if msg.text == "❌ Cancel":
        await state.clear()
        return await msg.answer("Cancelled.", reply_markup=admin_main_kb())
    otp_code   = msg.text.strip()
    d          = await state.get_data()
    session_id = d["session_id"]
    await state.clear()

    session = await db.get_otp_session(session_id)
    if not session:
        return await msg.answer("❌ Session not found!")

    await db.deliver_otp(session_id, otp_code)
    acc = await db.get_account(session["account_id"])

    try:
        await bot.send_message(
            session["user_id"],
            f"🔐 <b>Your OTP</b>\n\n"
            f"📱 <code>{acc['number'] if acc else 'N/A'}</code>\n"
            f"🔑 <b><code>{otp_code}</code></b>\n\n"
            f"⚡ Jaldi enter karo!",
            parse_mode="HTML"
        )
    except Exception:
        pass

    from utils.logger import log_otp
    await log_otp(bot, acc["number"] if acc else "N/A", otp_code, session["user_id"], "")
    await msg.answer(f"✅ OTP <code>{otp_code}</code> sent!", parse_mode="HTML", reply_markup=admin_main_kb())
