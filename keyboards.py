from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)

_DEV      = "@BOTMAKERGARVIT"
_DEV_LINK = "https://t.me/BOTMAKERGARVIT"


def user_main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🛒 Browse Accounts"), KeyboardButton(text="📦 My Orders")],
        [KeyboardButton(text="💰 My Wallet"),       KeyboardButton(text="➕ Deposit")],
        [KeyboardButton(text="📢 Channel"),         KeyboardButton(text="💬 Support")],
        [KeyboardButton(text="ℹ️ How It Works"),    KeyboardButton(text="👨‍💻 Developer")],
    ], resize_keyboard=True)


def developer_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"👨‍💻 Contact — {_DEV}", url=_DEV_LINK)],
    ])


def country_list_kb(stock: list):
    buttons = []
    for s in stock:
        flag = s.get("flag") or "🌍"
        buttons.append([InlineKeyboardButton(
            text=f"{flag} {s['country']}  ·  ₹{s['price']:.0f}  ·  {s['count']} in stock",
            callback_data=f"country:{s['country']}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def account_detail_kb(account_id: str, can_use_wallet: bool = False):
    buttons = [
        [InlineKeyboardButton(text="✅ Buy — Pay via UPI", callback_data=f"confirm_pay:{account_id}")],
    ]
    if can_use_wallet:
        buttons.append([InlineKeyboardButton(
            text="💰 Buy — Use Wallet Balance",
            callback_data=f"wallet_pay:{account_id}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="back_countries")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def payment_kb(order_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Upload Screenshot", callback_data=f"upload_ss:{order_id}")],
        [InlineKeyboardButton(text="❌ Cancel",            callback_data=f"cancel_order:{order_id}")],
    ])


def screenshot_done_kb(order_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Notify Admin — I've Paid", callback_data=f"paid_notify:{order_id}")],
        [InlineKeyboardButton(text="❌ Cancel",                   callback_data=f"cancel_order:{order_id}")],
    ])


def reveal_number_kb(order_id: str, session_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👁 Reveal Account Details", callback_data=f"reveal:{order_id}")],
        [InlineKeyboardButton(text="🔐 Get Latest OTP",         callback_data=f"get_otp:{session_id}")],
    ])


def otp_kb(session_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Get Latest OTP", callback_data=f"get_otp:{session_id}")],
    ])


def force_join_kb(not_joined: list):
    buttons = []
    for i, ch in enumerate(not_joined, 1):
        buttons.append([InlineKeyboardButton(text=f"📢 Join Channel {i}", url=ch["link"])])
    buttons.append([InlineKeyboardButton(text="✅ I've Joined — Check Again", callback_data="check_joined")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ── Deposit ────────────────────────────────────────────────────────────────────

def deposit_amount_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="₹50",       callback_data="dep:50"),
            InlineKeyboardButton(text="₹100",      callback_data="dep:100"),
            InlineKeyboardButton(text="₹200",      callback_data="dep:200"),
        ],
        [
            InlineKeyboardButton(text="₹500",      callback_data="dep:500"),
            InlineKeyboardButton(text="₹1000",     callback_data="dep:1000"),
            InlineKeyboardButton(text="✏️ Custom", callback_data="dep:custom"),
        ],
    ])


def deposit_payment_kb(deposit_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Upload Screenshot", callback_data=f"dep_ss:{deposit_id}")],
        [InlineKeyboardButton(text="❌ Cancel",            callback_data=f"dep_cancel:{deposit_id}")],
    ])


def deposit_confirm_kb(deposit_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Notify Admin — I've Paid", callback_data=f"dep_notify:{deposit_id}")],
        [InlineKeyboardButton(text="❌ Cancel",                   callback_data=f"dep_cancel:{deposit_id}")],
    ])


def admin_deposit_kb(deposit_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve", callback_data=f"dep_approve:{deposit_id}"),
            InlineKeyboardButton(text="❌ Reject",  callback_data=f"dep_reject:{deposit_id}"),
        ],
    ])


# ── Admin ──────────────────────────────────────────────────────────────────────

def admin_main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="➕ Add Account"),     KeyboardButton(text="📋 View Accounts")],
        [KeyboardButton(text="⏳ Pending Orders"),  KeyboardButton(text="💳 Pending Deposits")],
        [KeyboardButton(text="📊 Statistics"),      KeyboardButton(text="📜 Order History")],
        [KeyboardButton(text="👥 User Management"), KeyboardButton(text="🔐 OTP Sessions")],
        [KeyboardButton(text="📱 Session Manager"), KeyboardButton(text="📢 Broadcast")],
        [KeyboardButton(text="⚙️ Settings"),        KeyboardButton(text="🔧 Maintenance")],
        [KeyboardButton(text="🏠 User Mode")],
    ], resize_keyboard=True)


def admin_approve_kb(order_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve", callback_data=f"admin_approve:{order_id}"),
            InlineKeyboardButton(text="❌ Reject",  callback_data=f"admin_reject:{order_id}"),
        ],
        [InlineKeyboardButton(text="📸 View Screenshot", callback_data=f"admin_view_ss:{order_id}")],
    ])


def admin_account_kb(account_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Edit Price",   callback_data=f"edit_price:{account_id}"),
            InlineKeyboardButton(text="🔑 Edit Session", callback_data=f"edit_session:{account_id}"),
        ],
        [
            InlineKeyboardButton(text="📱 Create Session", callback_data=f"sm:edit:{account_id}"),
            InlineKeyboardButton(text="🗑 Delete",         callback_data=f"del_acc:{account_id}"),
        ],
    ])


def admin_otp_kb(session_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Send OTP Manually", callback_data=f"manual_otp:{session_id}")],
    ])


def maintenance_kb(is_on: bool):
    toggle_text = "✅ Turn OFF" if is_on else "🔴 Turn ON"
    toggle_cb   = "maintenance_off" if is_on else "maintenance_on"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle_text,       callback_data=toggle_cb)],
        [InlineKeyboardButton(text="✏️ Edit Message", callback_data="maintenance_edit_msg")],
    ])


def cancel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Cancel")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
