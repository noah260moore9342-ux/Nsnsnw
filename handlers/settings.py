from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Filter

import utils.bot_config as cfg
from config import ADMIN_IDS

router = Router()


class IsAdmin(Filter):
    async def __call__(self, obj) -> bool:
        return obj.from_user.id in ADMIN_IDS


# ── States ─────────────────────────────────────────────────────────────────────

class SettingsState(StatesGroup):
    upi_id          = State()
    upi_name        = State()
    support_group   = State()
    admin_username  = State()
    log_channel_id  = State()
    log_channel_link= State()
    bot_name        = State()
    add_fj_id       = State()
    add_fj_link     = State()
    remove_fj       = State()


# ── Settings Main Menu ─────────────────────────────────────────────────────────

async def settings_menu_text() -> str:
    return (
        f"⚙️ <b>Bot Settings</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 UPI ID       : <code>{await cfg.upi_id()}</code>\n"
        f"🏦 UPI Name     : {await cfg.upi_name()}\n"
        f"💬 Support      : {await cfg.support_group()}\n"
        f"👤 Admin User   : {await cfg.admin_username()}\n"
        f"📢 Log Channel  : {await cfg.log_channel_link()}\n"
        f"🤖 Bot Name     : {await cfg.bot_name()}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔒 Force Join Channels:\n"
        + await _fj_list_text()
    )


async def _fj_list_text() -> str:
    channels = await cfg.force_join_channels()
    if not channels:
        return "  None added"
    return "\n".join(f"  • {c['link']} (<code>{c['id']}</code>)" for c in channels)


def settings_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💳 UPI ID",       callback_data="set:upi_id"),
            InlineKeyboardButton(text="🏦 UPI Name",     callback_data="set:upi_name"),
        ],
        [
            InlineKeyboardButton(text="💬 Support Group", callback_data="set:support"),
            InlineKeyboardButton(text="👤 Admin Username",callback_data="set:admin_user"),
        ],
        [
            InlineKeyboardButton(text="📢 Log Channel ID",   callback_data="set:log_id"),
            InlineKeyboardButton(text="🔗 Log Channel Link", callback_data="set:log_link"),
        ],
        [
            InlineKeyboardButton(text="🤖 Bot Name", callback_data="set:bot_name"),
        ],
        [
            InlineKeyboardButton(text="➕ Add Force Join",    callback_data="set:fj_add"),
            InlineKeyboardButton(text="➖ Remove Force Join", callback_data="set:fj_remove"),
        ],
        [
            InlineKeyboardButton(text="🔄 Refresh", callback_data="set:refresh"),
        ],
    ])


@router.message(IsAdmin(), F.text == "⚙️ Settings")
async def settings_panel(msg: Message):
    text = await settings_menu_text()
    await msg.answer(text, parse_mode="HTML", reply_markup=settings_kb())


@router.callback_query(IsAdmin(), F.data == "set:refresh")
async def settings_refresh(cq: CallbackQuery):
    text = await settings_menu_text()
    try:
        await cq.message.edit_text(text, parse_mode="HTML", reply_markup=settings_kb())
    except Exception:
        pass
    await cq.answer("✅ Refreshed!")


# ── UPI ID ────────────────────────────────────────────────────────────────────

@router.callback_query(IsAdmin(), F.data == "set:upi_id")
async def set_upi_id_start(cq: CallbackQuery, state: FSMContext):
    current = await cfg.upi_id()
    await state.set_state(SettingsState.upi_id)
    await cq.message.answer(
        f"💳 <b>Change UPI ID</b>\n\n"
        f"Current: <code>{current}</code>\n\n"
        f"Naya UPI ID daalo:\nExample: <code>yourname@upi</code>",
        parse_mode="HTML"
    )
    await cq.answer()


@router.message(IsAdmin(), SettingsState.upi_id)
async def set_upi_id_done(msg: Message, state: FSMContext):
    val = msg.text.strip()
    await state.clear()
    await cfg.set("upi_id", val)
    await msg.answer(f"✅ UPI ID updated!\n<code>{val}</code>", parse_mode="HTML")


# ── UPI Name ──────────────────────────────────────────────────────────────────

@router.callback_query(IsAdmin(), F.data == "set:upi_name")
async def set_upi_name_start(cq: CallbackQuery, state: FSMContext):
    current = await cfg.upi_name()
    await state.set_state(SettingsState.upi_name)
    await cq.message.answer(
        f"🏦 <b>Change UPI Name</b>\n\n"
        f"Current: <b>{current}</b>\n\n"
        f"Naya UPI Name daalo:",
        parse_mode="HTML"
    )
    await cq.answer()


@router.message(IsAdmin(), SettingsState.upi_name)
async def set_upi_name_done(msg: Message, state: FSMContext):
    val = msg.text.strip()
    await state.clear()
    await cfg.set("upi_name", val)
    await msg.answer(f"✅ UPI Name updated!\n<b>{val}</b>", parse_mode="HTML")


# ── Support Group ─────────────────────────────────────────────────────────────

@router.callback_query(IsAdmin(), F.data == "set:support")
async def set_support_start(cq: CallbackQuery, state: FSMContext):
    current = await cfg.support_group()
    await state.set_state(SettingsState.support_group)
    await cq.message.answer(
        f"💬 <b>Change Support Group</b>\n\n"
        f"Current: {current}\n\n"
        f"Naya username daalo:\nExample: <code>@mysupport</code>",
        parse_mode="HTML"
    )
    await cq.answer()


@router.message(IsAdmin(), SettingsState.support_group)
async def set_support_done(msg: Message, state: FSMContext):
    val = msg.text.strip()
    await state.clear()
    await cfg.set("support_group", val)
    await msg.answer(f"✅ Support Group updated!\n{val}", parse_mode="HTML")


# ── Admin Username ────────────────────────────────────────────────────────────

@router.callback_query(IsAdmin(), F.data == "set:admin_user")
async def set_admin_user_start(cq: CallbackQuery, state: FSMContext):
    current = await cfg.admin_username()
    await state.set_state(SettingsState.admin_username)
    await cq.message.answer(
        f"👤 <b>Change Admin Username</b>\n\n"
        f"Current: {current}\n\n"
        f"Naya username daalo:\nExample: <code>@EVILTALKS</code>",
        parse_mode="HTML"
    )
    await cq.answer()


@router.message(IsAdmin(), SettingsState.admin_username)
async def set_admin_user_done(msg: Message, state: FSMContext):
    val = msg.text.strip()
    await state.clear()
    await cfg.set("admin_username", val)
    await msg.answer(f"✅ Admin Username updated!\n{val}", parse_mode="HTML")


# ── Log Channel ID ────────────────────────────────────────────────────────────

@router.callback_query(IsAdmin(), F.data == "set:log_id")
async def set_log_id_start(cq: CallbackQuery, state: FSMContext):
    current = await cfg.log_channel_id()
    await state.set_state(SettingsState.log_channel_id)
    await cq.message.answer(
        f"📢 <b>Change Log Channel ID</b>\n\n"
        f"Current: <code>{current}</code>\n\n"
        f"Naya Channel ID daalo:\n"
        f"(Channel mein koi bhi message forward karo @userinfobot ko, ID milega)\n"
        f"Example: <code>-1001234567890</code>",
        parse_mode="HTML"
    )
    await cq.answer()


@router.message(IsAdmin(), SettingsState.log_channel_id)
async def set_log_id_done(msg: Message, state: FSMContext):
    val = msg.text.strip()
    await state.clear()
    try:
        int(val)  # validate it's a number
        await cfg.set("log_channel_id", val)
        await msg.answer(f"✅ Log Channel ID updated!\n<code>{val}</code>", parse_mode="HTML")
    except ValueError:
        await msg.answer("❌ Valid channel ID daalo! Example: <code>-1001234567890</code>", parse_mode="HTML")


# ── Log Channel Link ──────────────────────────────────────────────────────────

@router.callback_query(IsAdmin(), F.data == "set:log_link")
async def set_log_link_start(cq: CallbackQuery, state: FSMContext):
    current = await cfg.log_channel_link()
    await state.set_state(SettingsState.log_channel_link)
    await cq.message.answer(
        f"🔗 <b>Change Log Channel Link</b>\n\n"
        f"Current: {current}\n\n"
        f"Naya link daalo:\nExample: <code>https://t.me/mychannel</code>",
        parse_mode="HTML"
    )
    await cq.answer()


@router.message(IsAdmin(), SettingsState.log_channel_link)
async def set_log_link_done(msg: Message, state: FSMContext):
    val = msg.text.strip()
    await state.clear()
    await cfg.set("log_channel_link", val)
    await msg.answer(f"✅ Log Channel Link updated!\n{val}", parse_mode="HTML")


# ── Bot Name ──────────────────────────────────────────────────────────────────

@router.callback_query(IsAdmin(), F.data == "set:bot_name")
async def set_bot_name_start(cq: CallbackQuery, state: FSMContext):
    current = await cfg.bot_name()
    await state.set_state(SettingsState.bot_name)
    await cq.message.answer(
        f"🤖 <b>Change Bot Name</b>\n\n"
        f"Current: <b>{current}</b>\n\n"
        f"Naya naam daalo:",
        parse_mode="HTML"
    )
    await cq.answer()


@router.message(IsAdmin(), SettingsState.bot_name)
async def set_bot_name_done(msg: Message, state: FSMContext):
    val = msg.text.strip()
    await state.clear()
    await cfg.set("bot_name", val)
    await msg.answer(f"✅ Bot Name updated!\n<b>{val}</b>", parse_mode="HTML")


# ── Force Join — Add ──────────────────────────────────────────────────────────

@router.callback_query(IsAdmin(), F.data == "set:fj_add")
async def fj_add_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsState.add_fj_id)
    await cq.message.answer(
        "➕ <b>Add Force Join Channel</b>\n\n"
        "<b>Step 1:</b> Channel ID daalo\n"
        "(@userinfobot se milega)\n"
        "Example: <code>-1001234567890</code>",
        parse_mode="HTML"
    )
    await cq.answer()


@router.message(IsAdmin(), SettingsState.add_fj_id)
async def fj_add_id(msg: Message, state: FSMContext):
    try:
        ch_id = int(msg.text.strip())
        await state.update_data(fj_id=ch_id)
        await state.set_state(SettingsState.add_fj_link)
        await msg.answer(
            f"✅ ID: <code>{ch_id}</code>\n\n"
            f"<b>Step 2:</b> Channel link daalo:\n"
            f"Example: <code>https://t.me/mychannel</code>",
            parse_mode="HTML"
        )
    except ValueError:
        await msg.answer("❌ Valid channel ID daalo! Example: <code>-1001234567890</code>", parse_mode="HTML")


@router.message(IsAdmin(), SettingsState.add_fj_link)
async def fj_add_link(msg: Message, state: FSMContext):
    data    = await state.get_data()
    ch_id   = data["fj_id"]
    ch_link = msg.text.strip()
    await state.clear()

    await cfg.add_force_join_channel(ch_id, ch_link)
    channels = await cfg.force_join_channels()
    await msg.answer(
        f"✅ <b>Force Join Channel Added!</b>\n\n"
        f"🔗 {ch_link}\n"
        f"🆔 <code>{ch_id}</code>\n\n"
        f"Total channels: {len(channels)}\n\n"
        f"⚠️ Bot ko us channel ka Admin banao!",
        parse_mode="HTML"
    )


# ── Force Join — Remove ───────────────────────────────────────────────────────

@router.callback_query(IsAdmin(), F.data == "set:fj_remove")
async def fj_remove_start(cq: CallbackQuery, state: FSMContext):
    channels = await cfg.force_join_channels()
    if not channels:
        return await cq.answer("❌ Koi force join channel nahi hai!", show_alert=True)

    text = "➖ <b>Remove Force Join Channel</b>\n\nKaunsa channel remove karna hai? ID daalo:\n\n"
    for c in channels:
        text += f"• <code>{c['id']}</code> — {c['link']}\n"

    await state.set_state(SettingsState.remove_fj)
    await cq.message.answer(text, parse_mode="HTML")
    await cq.answer()


@router.message(IsAdmin(), SettingsState.remove_fj)
async def fj_remove_done(msg: Message, state: FSMContext):
    await state.clear()
    try:
        ch_id = int(msg.text.strip())
        await cfg.remove_force_join_channel(ch_id)
        await msg.answer(f"✅ Channel <code>{ch_id}</code> removed!", parse_mode="HTML")
    except ValueError:
        await msg.answer("❌ Valid channel ID daalo!")
