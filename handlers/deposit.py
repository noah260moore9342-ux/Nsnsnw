from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from utils.qr import make_upi_qr
from keyboards import deposit_payment_kb, deposit_confirm_kb, admin_deposit_kb
from config import ADMIN_IDS

router = Router()


class DepositState(StatesGroup):
    custom_amount = State()
    screenshot    = State()


# ── My Wallet ──────────────────────────────────────────────────────────────────

@router.message(F.text == "💰 My Wallet")
async def my_wallet(msg: Message):
    try:
        bal    = await db.get_balance(msg.from_user.id)
        orders = await db.get_user_orders(msg.from_user.id)
        done   = [o for o in orders if o["status"] == "approved"]
        spent  = sum(o["amount"] for o in done)
    except Exception:
        bal   = 0.0
        done  = []
        spent = 0.0

    await msg.answer(
        f"💼 <b>My Wallet</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Balance  : <b>₹{bal:.2f}</b>\n"
        f"📦 Orders   : {len(done)} completed\n"
        f"💸 Spent    : ₹{spent:.2f}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Tap <b>➕ Deposit</b> to add money!",
        parse_mode="HTML"
    )


# ── Deposit Menu ───────────────────────────────────────────────────────────────

@router.message(F.text == "➕ Deposit")
async def deposit_menu(msg: Message):
    from keyboards import deposit_amount_kb
    bal = await db.get_balance(msg.from_user.id)
    await msg.answer(
        f"💳 <b>Add Money to Wallet</b>\n\n"
        f"💼 Balance: <b>₹{bal:.2f}</b>\n\n"
        f"Amount select karo:",
        parse_mode="HTML",
        reply_markup=deposit_amount_kb()
    )


# ── Amount Selected ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("dep:"))
async def dep_amount(cq: CallbackQuery, state: FSMContext):
    val = cq.data.split(":", 1)[1]
    if val == "custom":
        await state.set_state(DepositState.custom_amount)
        await cq.message.answer(
            "✏️ <b>Custom Amount</b>\n\nKitna deposit karna hai (₹)?\nMin: ₹10",
            parse_mode="HTML"
        )
        await cq.answer()
        return

    await _send_qr(cq.message, cq.from_user.id, cq.from_user.username or "", float(val))
    await cq.answer()


# ── Custom Amount ──────────────────────────────────────────────────────────────

@router.message(DepositState.custom_amount)
async def dep_custom(msg: Message, state: FSMContext):
    try:
        amount = float(msg.text.strip().replace("₹", "").replace(",", ""))
        if amount < 10:
            return await msg.answer("❌ Minimum ₹10!")
    except ValueError:
        return await msg.answer("❌ Valid amount daalo!")
    await state.clear()
    await _send_qr(msg, msg.from_user.id, msg.from_user.username or "", amount)


# ── Generate QR ────────────────────────────────────────────────────────────────

async def _send_qr(target, user_id: int, username: str, amount: float):
    deposit_id = await db.create_deposit(user_id, username, amount, 0)
    try:
        qr_bytes, exact, upi_id = await make_upi_qr(amount, deposit_id[:6])
    except Exception:
        from utils.qr import make_upi_qr as _qr
        result = await _qr(amount, deposit_id[:6])
        qr_bytes, exact, upi_id = result

    await db.update_deposit_exact(deposit_id, exact)

    caption = (
        f"💳 <b>Deposit QR</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Amount  : ₹{amount:.2f}\n"
        f"💸 Pay     : <b>₹{exact:.2f}</b>\n"
        f"🏦 UPI ID  : <code>{upi_id}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ Exact amount pay karo!\n\n"
        f"📸 Screenshot le aur upload karo 👇"
    )
    qr_file = BufferedInputFile(qr_bytes, filename="deposit.png")
    await target.answer_photo(
        photo=qr_file,
        caption=caption,
        parse_mode="HTML",
        reply_markup=deposit_payment_kb(deposit_id)
    )


# ── Upload Screenshot ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("dep_ss:"))
async def dep_ss_prompt(cq: CallbackQuery, state: FSMContext):
    deposit_id = cq.data.split(":", 1)[1]
    dep = await db.get_deposit(deposit_id)

    if not dep:
        return await cq.answer("❌ Deposit not found!", show_alert=True)
    if dep["user_id"] != cq.from_user.id:
        return await cq.answer("❌ Not your deposit!", show_alert=True)
    if dep["status"] != "pending":
        return await cq.answer("⚠️ Already processed.", show_alert=True)

    await state.set_state(DepositState.screenshot)
    await state.update_data(deposit_id=deposit_id)
    await cq.message.answer(
        "📸 <b>Screenshot Bhejo</b>\n\n"
        "• Gallery se photo select karo\n"
        "• Image send karo (file nahi)",
        parse_mode="HTML"
    )
    await cq.answer()


@router.message(DepositState.screenshot, F.photo)
async def dep_ss_recv(msg: Message, state: FSMContext):
    data       = await state.get_data()
    deposit_id = data.get("deposit_id")
    await state.clear()

    if not deposit_id:
        return await msg.answer("❌ Session expire. Dobara try karo.")

    file_id = msg.photo[-1].file_id
    await db.set_deposit_screenshot(deposit_id, file_id)
    dep = await db.get_deposit(deposit_id)

    await msg.answer(
        f"✅ <b>Screenshot Received!</b>\n\n"
        f"💰 ₹{dep['amount']:.2f}\n\n"
        f"Ab admin ko notify karo 👇",
        parse_mode="HTML",
        reply_markup=deposit_confirm_kb(deposit_id)
    )


@router.message(DepositState.screenshot, F.document)
async def dep_ss_doc(msg: Message):
    await msg.answer("❌ File nahi! Gallery se photo bhejo.")


@router.message(DepositState.screenshot, ~F.photo)
async def dep_ss_wrong(msg: Message):
    await msg.answer("❌ Sirf photo bhejo!")


# ── Notify Admin ───────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("dep_notify:"))
async def dep_notify(cq: CallbackQuery, bot: Bot):
    deposit_id = cq.data.split(":", 1)[1]
    dep = await db.get_deposit(deposit_id)

    if not dep:
        return await cq.answer("❌ Not found!", show_alert=True)
    if dep["user_id"] != cq.from_user.id:
        return await cq.answer("❌ Not yours!", show_alert=True)
    if dep["status"] != "pending":
        return await cq.answer("⚠️ Already processed.", show_alert=True)
    if not dep.get("screenshot"):
        return await cq.answer("❌ Pehle screenshot upload karo!", show_alert=True)

    try:
        await cq.message.edit_caption(
            caption=(
                f"⏳ <b>Verification Pending</b>\n\n"
                f"₹{dep['amount']:.2f} — Admin check kar raha hai...\n"
                f"Approve hone pe wallet mein add hoga! ✅"
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass

    for aid in ADMIN_IDS:
        try:
            await bot.send_photo(
                aid,
                dep["screenshot"],
                caption=(
                    f"💳 <b>DEPOSIT REQUEST!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 @{dep['username'] or 'N/A'} · <code>{dep['user_id']}</code>\n"
                    f"💰 ₹{dep['amount']:.2f} · Paid ₹{dep['exact_amount']:.2f}\n"
                    f"🗓 {dep['created_at'][:19]}"
                ),
                parse_mode="HTML",
                reply_markup=admin_deposit_kb(deposit_id)
            )
        except Exception:
            try:
                await bot.send_message(
                    aid,
                    f"💳 <b>DEPOSIT!</b>\n👤 <code>{dep['user_id']}</code>\n💰 ₹{dep['amount']:.2f}",
                    parse_mode="HTML",
                    reply_markup=admin_deposit_kb(deposit_id)
                )
            except Exception:
                pass

    await cq.answer("✅ Admin ko notify kar diya!")


# ── Cancel Deposit ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("dep_cancel:"))
async def dep_cancel(cq: CallbackQuery):
    deposit_id = cq.data.split(":", 1)[1]
    dep = await db.get_deposit(deposit_id)

    if not dep or dep["user_id"] != cq.from_user.id:
        return await cq.answer("❌ Not yours!", show_alert=True)
    if dep["status"] != "pending":
        return await cq.answer("⚠️ Already processed.", show_alert=True)

    await db.reject_deposit(deposit_id)
    try:
        await cq.message.edit_caption(caption="❌ Deposit cancelled.", parse_mode="HTML")
    except Exception:
        await cq.message.answer("❌ Deposit cancelled.")
    await cq.answer("Cancelled.")


# ── Wallet Pay ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("wallet_pay:"))
async def wallet_pay(cq: CallbackQuery, bot: Bot):
    account_id = cq.data.split(":", 1)[1]
    acc = await db.get_account(account_id)

    if not acc or acc["status"] != "available":
        return await cq.answer("❌ Account no longer available!", show_alert=True)

    bal = await db.get_balance(cq.from_user.id)
    if bal < acc["price"]:
        return await cq.answer(
            f"❌ Insufficient balance!\n"
            f"Balance : ₹{bal:.2f}\n"
            f"Required: ₹{acc['price']:.2f}\n\n"
            f"Pehle deposit karo!",
            show_alert=True
        )

    u        = cq.from_user
    order_id = await db.create_order(u.id, u.username or "", u.full_name or "", account_id, acc["price"])
    deducted = await db.deduct_balance(u.id, acc["price"])

    if not deducted:
        return await cq.answer("❌ Balance error. Try again.", show_alert=True)

    await db.approve_order(order_id)
    await db.mark_account_sold(account_id, u.id)
    await db.update_user_stats(u.id, acc["price"])
    session_id = await db.create_otp_session(order_id, u.id, account_id)
    new_bal    = await db.get_balance(u.id)

    from keyboards import reveal_number_kb
    await cq.message.answer(
        f"✅ <b>Purchase Successful!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💸 ₹{acc['price']:.2f} deducted\n"
        f"💼 Remaining: ₹{new_bal:.2f}\n"
        f"{acc['country_flag']} {acc['country']}\n\n"
        f"👇 Account details ke liye:",
        parse_mode="HTML",
        reply_markup=reveal_number_kb(order_id, session_id)
    )

    try:
        from utils.logger import log_sale
        await log_sale(bot, acc["number"], acc["price"], acc["country"],
                       acc["country_flag"], u.id, u.username or "", order_id)
    except Exception:
        pass

    await cq.answer("✅ Purchase done!")


# ── Admin: Approve Deposit ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("dep_approve:"))
async def dep_approve(cq: CallbackQuery, bot: Bot):
    from config import ADMIN_IDS
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ Not authorized!", show_alert=True)

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
            f"💰 ₹{dep['amount']:.2f} wallet mein add!\n"
            f"💼 New Balance: ₹{bal:.2f}",
            parse_mode="HTML"
        )
    except Exception:
        pass

    try:
        await cq.message.edit_caption(
            caption=f"✅ Deposit ₹{dep['amount']:.2f} approved for <code>{dep['user_id']}</code>.",
            parse_mode="HTML"
        )
    except Exception:
        await cq.message.answer("✅ Deposit approved!")

    await cq.answer("✅ Approved!")


@router.callback_query(F.data.startswith("dep_reject:"))
async def dep_reject(cq: CallbackQuery, bot: Bot):
    from config import ADMIN_IDS
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ Not authorized!", show_alert=True)

    deposit_id = cq.data.split(":", 1)[1]
    dep = await db.get_deposit(deposit_id)

    if not dep or dep["status"] != "pending":
        return await cq.answer("⚠️ Already processed.", show_alert=True)

    await db.reject_deposit(deposit_id)

    try:
        await bot.send_message(
            dep["user_id"],
            f"❌ <b>Deposit Rejected</b>\n\n₹{dep['amount']:.2f} verify nahi hua.",
            parse_mode="HTML"
        )
    except Exception:
        pass

    try:
        await cq.message.edit_caption(caption="❌ Deposit rejected.")
    except Exception:
        await cq.message.answer("❌ Rejected!")

    await cq.answer("❌ Rejected!")
