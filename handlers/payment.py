from aiogram import Router, F, Bot
from aiogram.types import (
    CallbackQuery, Message, BufferedInputFile,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from utils.qr import make_upi_qr
from utils.logger import log_sale
from keyboards import (
    payment_kb, screenshot_done_kb,
    admin_approve_kb, reveal_number_kb
)
from config import ADMIN_IDS

router = Router()


class ScreenshotState(StatesGroup):
    waiting = State()


# ── Check if Gmail is configured ──────────────────────────────────────────────

def _gmail_ready() -> bool:
    import os
    return bool(
        os.getenv("GMAIL_USER", "").strip() and
        os.getenv("GMAIL_APP_PASSWORD", "").strip()
    )


# ── SEND ACCOUNT DETAILS ──────────────────────────────────────────────────────

async def send_account_details(user_id: int, account: dict, bot: Bot, order_id: str = None):
    """AUTO SEND ACCOUNT DETAILS AFTER PAYMENT"""
    msg = (
        f"🎉 <b>ACCOUNT UNLOCKED!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🌍 {account.get('country_flag', '🏳️')} {account.get('country', 'Unknown')}\n"
        f"📱 <code>{account.get('number', 'N/A')}</code>\n"
        f"🔑 Password: <code>{account.get('password', 'N/A')}</code>\n"
        f"📧 Email: <code>{account.get('email', 'N/A')}</code>\n"
        f"📋 UTR: <code>{account.get('utr', 'N/A')}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ <b>IMPORTANT:</b>\n"
        f"• Login immediately\n"
        f"• Don't share with anyone\n"
        f"• No refund after 5 mins\n"
        f"• Contact @UnknownGuy9876 for support"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📋 Copy Password",
            callback_data=f"copy_pass:{account.get('_id', '')}"
        )],
        [InlineKeyboardButton(
            text="🆘 Report Issue",
            callback_data=f"report_issue:{order_id or ''}"
        )],
        [InlineKeyboardButton(
            text="📞 Support",
            url="https://t.me/UnknownGuy9876"
        )]
    ])
    
    try:
        await bot.send_message(
            user_id,
            msg,
            parse_mode="HTML",
            reply_markup=kb
        )
        return True
    except Exception as e:
        print(f"❌ Send account error: {e}")
        return False


# ── Payment QR Keyboard ────────────────────────────────────────────────────────

def _payment_kb_with_auto(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="⚡ Auto-Check Payment",
            callback_data=f"auto_check:{order_id}"
        )],
        [InlineKeyboardButton(
            text="📸 Manual: Upload Screenshot",
            callback_data=f"upload_ss:{order_id}"
        )],
        [InlineKeyboardButton(
            text="❌ Cancel Order",
            callback_data=f"cancel_order:{order_id}"
        )],
    ])


def _recheck_kb(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔄 Check Again",
            callback_data=f"auto_check:{order_id}"
        )],
        [InlineKeyboardButton(
            text="📸 Upload Screenshot Instead",
            callback_data=f"upload_ss:{order_id}"
        )],
        [InlineKeyboardButton(
            text="❌ Cancel",
            callback_data=f"cancel_order:{order_id}"
        )],
    ])


# ── Admin: Test Gmail ──────────────────────────────────────────────────────────

@router.message(F.text == "/testgmail")
async def test_gmail(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    await msg.answer("⏳ Gmail connection test kar raha hoon...")
    from utils.payment_checker import test_connection
    result = await test_connection()
    if result["ok"]:
        await msg.answer(f"✅ <b>Gmail Connected!</b>\n\n{result['message']}", parse_mode="HTML")
    else:
        await msg.answer(
            f"❌ <b>Gmail Error!</b>\n\n<code>{result['message']}</code>\n\n"
            f"Fix:\n"
            f"• GMAIL_USER → apna gmail\n"
            f"• GMAIL_APP_PASSWORD → spaces hata ke daalo\n"
            f"  Example: <code>hsthcecnesbldzp</code>",
            parse_mode="HTML"
        )


# ── Confirm Pay → Generate QR ──────────────────────────────────────────────────

@router.callback_query(F.data.startswith("confirm_pay:"))
async def confirm_pay(cq: CallbackQuery, bot: Bot):
    account_id = cq.data.split(":", 1)[1]
    acc        = await db.get_account(account_id)

    if not acc or acc["status"] != "available":
        return await cq.answer("❌ Account no longer available!", show_alert=True)

    u        = cq.from_user
    order_id = await db.create_order(
        u.id, u.username or "", u.full_name or "", account_id, acc["price"]
    )

    try:
        qr_bytes, exact, upi_id = await make_upi_qr(acc["price"], order_id[:6])
    except Exception as e:
        return await cq.answer(f"❌ QR error: {str(e)[:40]}", show_alert=True)

    await db.set_order_exact_amount(order_id, exact)

    gmail_ok = _gmail_ready()

    caption = (
        f"💳 <b>UPI Payment</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{acc['country_flag']} {acc['country']} Account\n"
        f"💰 Pay EXACTLY: <b>₹{exact:.2f}</b>\n"
        f"🏦 UPI ID: <code>{upi_id}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        + (
            f"⚡ <b>Auto-Verify Available!</b>\n"
            f"Pay karo → Button dabao → Auto confirm!\n\n"
            if gmail_ok else
            f"📸 Pay karo → Screenshot lo → Upload karo\n\n"
        )
        + f"⏰ 15 min mein pay karo!"
    )

    qr_file = BufferedInputFile(qr_bytes, filename="pay.png")
    kb = _payment_kb_with_auto(order_id) if gmail_ok else payment_kb(order_id)

    try:
        await cq.message.answer_photo(
            photo=qr_file,
            caption=caption,
            parse_mode="HTML",
            reply_markup=kb
        )
        try:
            await cq.message.delete()
        except Exception:
            pass
    except Exception as e:
        return await cq.answer(f"❌ Error: {str(e)[:50]}", show_alert=True)

    for aid in ADMIN_IDS:
        try:
            await bot.send_message(
                aid,
                f"🛎 <b>New Order!</b>\n\n"
                f"👤 @{u.username or 'N/A'} (<code>{u.id}</code>)\n"
                f"{acc['country_flag']} <code>{acc['number']}</code>\n"
                f"💸 ₹{exact:.2f}",
                parse_mode="HTML"
            )
        except Exception:
            pass

    await cq.answer("✅ QR ready!")


# ── Auto Payment Check ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("auto_check:"))
async def auto_check(cq: CallbackQuery, bot: Bot):
    order_id = cq.data.split(":", 1)[1]
    order    = await db.get_order(order_id)

    if not order:
        return await cq.answer("❌ Order not found!", show_alert=True)
    if order["user_id"] != cq.from_user.id:
        return await cq.answer("❌ Not your order!", show_alert=True)
    if order["status"] != "pending":
        return await cq.answer(
            "✅ Order already processed!" if order["status"] == "approved" else "❌ Order cancelled.",
            show_alert=True
        )

    await cq.answer("⏳ Checking... 30 sec wait karo", show_alert=False)

    try:
        await cq.message.edit_caption(
            caption=(
                f"🔄 <b>Payment Check Ho Raha Hai...</b>\n\n"
                f"💸 ₹{order.get('exact_amount', order['amount']):.2f}\n\n"
                f"Gmail scan ho raha hai...\n"
                f"Kripya 30 seconds wait karo ⏳"
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass

    from utils.payment_checker import verify_payment
    exact = order.get("exact_amount") or order["amount"]

    try:
        result = await verify_payment(float(exact), timeout_minutes=15)
    except Exception as e:
        result = {"verified": False, "message": str(e)}

    if result.get("verified"):
        # ── AUTO APPROVE ──────────────────────────────────────────────────────
        acc = await db.get_account(order["account_id"])
        
        if not acc:
            return await cq.answer("❌ Account not found!", show_alert=True)
        
        # Mark sold and approve
        await db.approve_order(order_id)
        await db.mark_account_sold(order["account_id"], order["user_id"])
        await db.update_user_stats(order["user_id"], order["amount"])
        session_id = await db.create_otp_session(order_id, order["user_id"], order["account_id"])

        utr = result.get("utr", "N/A")
        amt = result.get("amount", order["amount"])
        
        # Save UTR to account
        acc['utr'] = utr

        # 🔥 SEND ACCOUNT DETAILS TO USER 🔥
        await send_account_details(order["user_id"], acc, bot, order_id)

        try:
            await cq.message.edit_caption(
                caption=(
                    f"✅ <b>Payment Verified!</b>\n\n"
                    f"💸 ₹{amt:.2f} received\n"
                    f"🔖 UTR: <code>{utr}</code>\n\n"
                    f"📬 Account details sent in DM!"
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass

        # Send reveal button too
        await bot.send_message(
            cq.from_user.id,
            f"🔐 <b>Click to reveal number</b>",
            parse_mode="HTML",
            reply_markup=reveal_number_kb(order_id, session_id)
        )

        try:
            await log_sale(
                bot, acc["number"], order["amount"],
                acc["country"], acc["country_flag"],
                order["user_id"], order["username"], order_id
            )
        except Exception:
            pass

        for aid in ADMIN_IDS:
            try:
                await bot.send_message(
                    aid,
                    f"✅ <b>Auto-Payment Verified!</b>\n\n"
                    f"👤 @{order['username'] or 'N/A'}\n"
                    f"📱 <code>{acc['number']}</code>\n"
                    f"💸 ₹{amt:.2f} · UTR: <code>{utr}</code>\n"
                    f"✅ Account details sent to user",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    else:
        # ── NOT FOUND ─────────────────────────────────────────────────────────
        msg_text = result.get("message", "Payment nahi mila")
        try:
            await cq.message.edit_caption(
                caption=(
                    f"❌ <b>Payment Not Found</b>\n\n"
                    f"💸 ₹{exact:.2f} abhi nahi mila\n\n"
                    f"ℹ️ {msg_text}\n\n"
                    f"• Pay kiya? 2-3 min baad dobara check karo\n"
                    f"• Ya screenshot upload karo"
                ),
                parse_mode="HTML",
                reply_markup=_recheck_kb(order_id)
            )
        except Exception:
            pass


# ── Upload Screenshot ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("upload_ss:"))
async def upload_ss(cq: CallbackQuery, state: FSMContext):
    order_id = cq.data.split(":", 1)[1]
    order    = await db.get_order(order_id)

    if not order:
        return await cq.answer("❌ Order not found!", show_alert=True)
    if order["user_id"] != cq.from_user.id:
        return await cq.answer("❌ Not your order!", show_alert=True)
    if order["status"] != "pending":
        return await cq.answer("⚠️ Already processed.", show_alert=True)

    await state.set_state(ScreenshotState.waiting)
    await state.update_data(order_id=order_id)
    await cq.message.answer(
        "📸 <b>Screenshot Bhejo</b>\n\n"
        "Gallery se photo select karo (file nahi)",
        parse_mode="HTML"
    )
    await cq.answer()


@router.message(ScreenshotState.waiting, F.photo)
async def recv_ss(msg: Message, state: FSMContext, bot: Bot):
    data     = await state.get_data()
    order_id = data.get("order_id")
    await state.clear()

    if not order_id:
        return await msg.answer("❌ Session expire. Dobara try karo.")

    file_id = msg.photo[-1].file_id
    await db.set_order_screenshot(order_id, file_id)
    order = await db.get_order(order_id)

    await msg.answer(
        f"✅ <b>Screenshot Received!</b>\n💸 ₹{order['amount']:.2f}\n\nAdmin ko notify karo 👇",
        parse_mode="HTML",
        reply_markup=screenshot_done_kb(order_id)
    )


@router.message(ScreenshotState.waiting, ~F.photo)
async def ss_wrong(msg: Message):
    await msg.answer("❌ Sirf photo bhejo! File ya text nahi.")


@router.callback_query(F.data.startswith("paid_notify:"))
async def paid_notify(cq: CallbackQuery, bot: Bot):
    order_id = cq.data.split(":", 1)[1]
    order    = await db.get_order(order_id)

    if not order:
        return await cq.answer("❌ Not found!", show_alert=True)
    if order["user_id"] != cq.from_user.id:
        return await cq.answer("❌ Not yours!", show_alert=True)
    if order["status"] != "pending":
        return await cq.answer("⚠️ Already processed.", show_alert=True)
    if not order.get("screenshot"):
        return await cq.answer("❌ Pehle screenshot upload karo!", show_alert=True)

    acc = await db.get_account(order["account_id"])
    try:
        await cq.message.edit_caption(
            caption="⏳ <b>Admin ko notify kar diya!</b>\n5-10 min mein approve hoga.",
            parse_mode="HTML"
        )
    except Exception:
        pass

    for aid in ADMIN_IDS:
        try:
            await bot.send_photo(
                aid, order["screenshot"],
                caption=(
                    f"🔔 <b>PAYMENT CLAIMED!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 @{order['username'] or 'N/A'} · <code>{order['user_id']}</code>\n"
                    f"📱 <code>{acc['number'] if acc else 'N/A'}</code>\n"
                    f"💸 ₹{order['amount']:.2f}"
                ),
                parse_mode="HTML",
                reply_markup=admin_approve_kb(order_id)
            )
        except Exception:
            try:
                await bot.send_message(
                    aid,
                    f"🔔 <b>PAYMENT!</b>\n<code>{order['user_id']}</code>\n₹{order['amount']:.2f}",
                    parse_mode="HTML",
                    reply_markup=admin_approve_kb(order_id)
                )
            except Exception:
                pass

    await cq.answer("✅ Admin notify kiya!")


# ── ADMIN APPROVE WITH ACCOUNT SEND ──────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_approve:"))
async def admin_approve(cq: CallbackQuery, bot: Bot):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ Only admin!", show_alert=True)
    
    order_id = cq.data.split(":", 1)[1]
    order = await db.get_order(order_id)
    
    if not order:
        return await cq.answer("❌ Order not found!")
    
    acc = await db.get_account(order["account_id"])
    if not acc:
        return await cq.answer("❌ Account not found!")
    
    # Approve
    await db.approve_order(order_id)
    await db.mark_account_sold(order["account_id"], order["user_id"])
    await db.update_user_stats(order["user_id"], order["amount"])
    session_id = await db.create_otp_session(order_id, order["user_id"], order["account_id"])
    
    # 🔥 SEND ACCOUNT DETAILS 🔥
    await send_account_details(order["user_id"], acc, bot, order_id)
    
    await cq.message.edit_caption(
        caption=(
            f"✅ <b>Approved by Admin!</b>\n\n"
            f"👤 @{order['username'] or 'N/A'}\n"
            f"📱 <code>{acc['number']}</code>\n"
            f"💸 ₹{order['amount']:.2f}\n"
            f"📬 Account details sent to user"
        ),
        parse_mode="HTML"
    )
    
    await bot.send_message(
        order["user_id"],
        f"✅ <b>Payment Approved!</b>\nAccount details DM mein aa gaye 📬",
        parse_mode="HTML",
        reply_markup=reveal_number_kb(order_id, session_id)
    )
    
    await cq.answer("✅ Approved!")


# ── CANCEL ORDER ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cancel_order:"))
async def cancel_order(cq: CallbackQuery):
    order_id = cq.data.split(":", 1)[1]
    order    = await db.get_order(order_id)

    if not order or order["user_id"] != cq.from_user.id:
        return await cq.answer("❌ Not yours!", show_alert=True)
    if order["status"] != "pending":
        return await cq.answer("⚠️ Cannot cancel.", show_alert=True)

    await db.reject_order(order_id)
    try:
        await cq.message.edit_caption(caption="❌ Order cancelled.", parse_mode="HTML")
    except Exception:
        await cq.message.answer("❌ Cancelled.")
    await cq.answer("Cancelled.")


# ── COPY PASSWORD ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("copy_pass:"))
async def copy_pass(cq: CallbackQuery):
    await cq.answer("🔑 Password copied to clipboard!", show_alert=True)


# ── REPORT ISSUE ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("report_issue:"))
async def report_issue(cq: CallbackQuery, bot: Bot):
    order_id = cq.data.split(":", 1)[1]
    await cq.answer("📞 Contact @UnknownGuy9876 for support", show_alert=True)
    
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(
                aid,
                f"⚠️ <b>Issue Reported!</b>\n"
                f"User: @{cq.from_user.username or 'N/A'} (<code>{cq.from_user.id}</code>)\n"
                f"Order: <code>{order_id}</code>",
                parse_mode="HTML"
            )
        except Exception:
            pass
