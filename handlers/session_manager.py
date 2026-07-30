import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Filter

import database as db
from config import ADMIN_IDS, API_ID, API_HASH

router  = Router()
_clients = {}  # Store active Telethon clients in memory


class IsAdmin(Filter):
    async def __call__(self, obj) -> bool:
        return obj.from_user.id in ADMIN_IDS


class SessionState(StatesGroup):
    phone  = State()
    otp    = State()
    twofa  = State()
    attach = State()


# ── Session Manager Menu ───────────────────────────────────────────────────────

@router.message(IsAdmin(), F.text == "📱 Session Manager")
async def session_manager(msg: Message):
    accounts = await db.get_all_accounts()
    with_sess  = sum(1 for a in accounts if a.get("session_str"))
    no_sess    = len(accounts) - with_sess

    await msg.answer(
        f"📱 <b>Session Manager</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ With Session : {with_sess}\n"
        f"❌ No Session   : {no_sess}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Number bhejo → Bot OTP bhejega → Session auto-create!",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📲 Create New Session", callback_data="sm:new")],
            [InlineKeyboardButton(text="📋 View All Sessions",  callback_data="sm:view")],
        ])
    )


# ── View Sessions ──────────────────────────────────────────────────────────────

@router.callback_query(IsAdmin(), F.data == "sm:view")
async def view_sessions(cq: CallbackQuery):
    accounts = await db.get_all_accounts()
    if not accounts:
        return await cq.answer("No accounts!", show_alert=True)

    text = "📋 <b>All Account Sessions</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for acc in accounts:
        sess   = "✅" if acc.get("session_str") else "❌"
        status = "🟢" if acc["status"] == "available" else "🔴"
        text  += f"{status} {sess} <code>{acc['number']}</code> · {acc['country_flag']} · ₹{acc['price']:.0f}\n"

    await cq.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📲 Create New Session", callback_data="sm:new")],
            [InlineKeyboardButton(text="🔄 Refresh",            callback_data="sm:view")],
        ])
    )
    await cq.answer()


# ── Step 1 — Start / Enter Number ─────────────────────────────────────────────

@router.callback_query(IsAdmin(), F.data == "sm:new")
async def sm_new(cq: CallbackQuery, state: FSMContext):
    if not API_ID or not API_HASH:
        return await cq.answer(
            "❌ API_ID aur API_HASH Railway variables mein set karo!",
            show_alert=True
        )
    await state.set_state(SessionState.phone)
    await cq.message.answer(
        "📲 <b>Create Session — Step 1/3</b>\n\n"
        "Account ka phone number bhejo:\n"
        "Example: <code>+917001234567</code>\n\n"
        "❌ Cancel: /cancel",
        parse_mode="HTML"
    )
    await cq.answer()


@router.callback_query(IsAdmin(), F.data.startswith("sm:edit:"))
async def sm_edit(cq: CallbackQuery, state: FSMContext):
    if not API_ID or not API_HASH:
        return await cq.answer("❌ API_ID/API_HASH missing!", show_alert=True)
    account_id = cq.data.split(":", 2)[2]
    acc = await db.get_account(account_id)
    if not acc:
        return await cq.answer("❌ Account not found!", show_alert=True)
    await state.set_state(SessionState.phone)
    await state.update_data(force_attach=account_id)
    await cq.message.answer(
        f"📲 <b>Edit Session</b>\n\n"
        f"Account: <code>{acc['number']}</code>\n\n"
        f"Phone number bhejo:\nExample: <code>{acc['number']}</code>\n\n"
        f"❌ Cancel: /cancel",
        parse_mode="HTML"
    )
    await cq.answer()


@router.message(IsAdmin(), F.text == "/cancel")
async def sm_cancel(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    if uid in _clients:
        try:
            await _clients[uid]["client"].disconnect()
        except Exception:
            pass
        del _clients[uid]
    await state.clear()
    from keyboards import admin_main_kb
    await msg.answer("❌ Cancelled.", reply_markup=admin_main_kb())


# ── Step 2 — Send OTP via Telethon ────────────────────────────────────────────

@router.message(IsAdmin(), SessionState.phone)
async def sm_phone(msg: Message, state: FSMContext):
    phone = msg.text.strip()
    if not phone.startswith("+") or len(phone) < 10:
        return await msg.answer(
            "❌ Valid phone daalo with +country code!\nExample: <code>+917001234567</code>",
            parse_mode="HTML"
        )

    status = await msg.answer(f"⏳ <code>{phone}</code> pe OTP bhej raha hoon...", parse_mode="HTML")

    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession

        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        result = await client.send_code_request(phone)

        _clients[msg.from_user.id] = {
            "client":     client,
            "phone":      phone,
            "phone_hash": result.phone_code_hash,
        }

        data = await state.get_data()
        await state.update_data(phone=phone)
        await state.set_state(SessionState.otp)

        await status.edit_text(
            f"✅ <b>OTP Bhej Diya!</b>\n\n"
            f"📱 <code>{phone}</code> pe Telegram OTP aaya hoga.\n\n"
            f"<b>Step 2/3</b> — OTP enter karo:\n"
            f"(Sirf numbers, e.g. <code>12345</code>)\n\n"
            f"❌ Cancel: /cancel",
            parse_mode="HTML"
        )

    except Exception as e:
        uid = msg.from_user.id
        if uid in _clients:
            try:
                await _clients[uid]["client"].disconnect()
            except Exception:
                pass
            del _clients[uid]
        await state.clear()
        from keyboards import admin_main_kb
        await status.edit_text(
            f"❌ <b>Error!</b>\n\n<code>{str(e)}</code>\n\nDobara try karo.",
            parse_mode="HTML"
        )


# ── Step 3 — Verify OTP ────────────────────────────────────────────────────────

@router.message(IsAdmin(), SessionState.otp)
async def sm_otp(msg: Message, state: FSMContext):
    otp_code = msg.text.strip().replace(" ", "")
    uid      = msg.from_user.id

    if uid not in _clients:
        await state.clear()
        return await msg.answer("❌ Session expire. Dobara try karo.")

    client_data = _clients[uid]
    client      = client_data["client"]
    phone       = client_data["phone"]
    phone_hash  = client_data["phone_hash"]

    verifying = await msg.answer("⏳ OTP verify ho raha hai...")

    try:
        await client.sign_in(phone=phone, code=otp_code, phone_code_hash=phone_hash)
        await _save_session(msg, state, client, phone, uid, verifying)

    except Exception as e:
        err = str(e).lower()
        if "password" in err or "two" in err or "2fa" in err or "cloud" in err:
            await state.set_state(SessionState.twofa)
            await verifying.edit_text(
                f"🔐 <b>2FA Password Required!</b>\n\n"
                f"Is account ka 2FA password daalo:\n\n"
                f"❌ Cancel: /cancel",
                parse_mode="HTML"
            )
        else:
            if uid in _clients:
                try:
                    await _clients[uid]["client"].disconnect()
                except Exception:
                    pass
                del _clients[uid]
            await state.clear()
            from keyboards import admin_main_kb
            await verifying.edit_text(
                f"❌ <b>OTP Error!</b>\n\n<code>{str(e)}</code>\n\nDobara try karo.",
                parse_mode="HTML"
            )


# ── Step 3b — 2FA ─────────────────────────────────────────────────────────────

@router.message(IsAdmin(), SessionState.twofa)
async def sm_2fa(msg: Message, state: FSMContext):
    password = msg.text.strip()
    uid      = msg.from_user.id

    if uid not in _clients:
        await state.clear()
        return await msg.answer("❌ Session expire. Dobara try karo.")

    client = _clients[uid]["client"]
    phone  = _clients[uid]["phone"]
    verifying = await msg.answer("⏳ 2FA verify ho raha hai...")

    try:
        await client.sign_in(password=password)
        await _save_session(msg, state, client, phone, uid, verifying)
    except Exception as e:
        if uid in _clients:
            try:
                await _clients[uid]["client"].disconnect()
            except Exception:
                pass
            del _clients[uid]
        await state.clear()
        await verifying.edit_text(f"❌ <b>2FA Error!</b>\n\n<code>{str(e)}</code>", parse_mode="HTML")


# ── Save Session & Attach ──────────────────────────────────────────────────────

async def _save_session(msg: Message, state: FSMContext, client, phone: str, uid: int, status_msg):
    session_str = client.session.save()
    await client.disconnect()
    if uid in _clients:
        del _clients[uid]

    data       = await state.get_data()
    force_id   = data.get("force_attach")

    # If forced attach (from account edit button)
    if force_id:
        await db.update_account(force_id, session_str=session_str)
        await state.clear()
        acc = await db.get_account(force_id)
        await status_msg.edit_text(
            f"🎉 <b>Session Created & Attached!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📱 <code>{phone}</code>\n"
            f"🔗 Account: <code>{acc['number'] if acc else 'N/A'}</code>\n"
            f"✅ Auto OTP ready! ⚡",
            parse_mode="HTML"
        )
        return

    # Try auto-match by number
    accounts = await db.get_all_accounts()
    phone_clean = phone.replace("+", "").strip()
    matching = [
        a for a in accounts
        if a["number"].replace("+", "").strip() == phone_clean
    ]

    if matching:
        acc = matching[0]
        await db.update_account(acc["id"], session_str=session_str)
        await state.clear()
        await status_msg.edit_text(
            f"🎉 <b>Session Auto-Attached!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📱 <code>{acc['number']}</code>\n"
            f"🌍 {acc['country_flag']} {acc['country']} · ₹{acc['price']:.0f}\n"
            f"✅ Auto OTP ready! ⚡",
            parse_mode="HTML"
        )
    else:
        # Manual attach
        await state.update_data(session_str=session_str, phone=phone)
        await state.set_state(SessionState.attach)
        kb = await _account_kb(accounts, session_str)
        await status_msg.edit_text(
            f"✅ <b>Session Created!</b>\n\n"
            f"📱 <code>{phone}</code>\n\n"
            f"Number match nahi mila.\n"
            f"Kaunse account se attach karna hai?",
            parse_mode="HTML",
            reply_markup=kb
        )


@router.callback_query(IsAdmin(), F.data.startswith("sm:attach:"))
async def sm_attach(cq: CallbackQuery, state: FSMContext):
    account_id  = cq.data.split(":", 2)[2]
    data        = await state.get_data()
    session_str = data.get("session_str")
    phone       = data.get("phone")

    if not session_str:
        await state.clear()
        return await cq.answer("❌ Session data missing.", show_alert=True)

    acc = await db.get_account(account_id)
    if not acc:
        return await cq.answer("❌ Account not found!", show_alert=True)

    await db.update_account(account_id, session_str=session_str)
    await state.clear()

    await cq.message.edit_text(
        f"🎉 <b>Session Attached!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 Session: <code>{phone}</code>\n"
        f"🔗 Account: <code>{acc['number']}</code>\n"
        f"🌍 {acc['country_flag']} {acc['country']}\n"
        f"✅ Auto OTP ready! ⚡",
        parse_mode="HTML"
    )
    await cq.answer("✅ Attached!")


async def _account_kb(accounts: list, session_str: str = "") -> InlineKeyboardMarkup:
    buttons = []
    for acc in accounts[:20]:
        sess = "✅" if acc.get("session_str") else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{sess} {acc['number']} · {acc['country_flag']}",
            callback_data=f"sm:attach:{acc['id']}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
