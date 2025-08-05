import logging
import csv
import io
from aiogram import Router, F, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import Settings
from db.dal import promo_code_dal
from db.models import PromoCode, PromoCodeActivation
from bot.states.admin_states import AdminStates
from bot.keyboards.inline.admin_keyboards import get_back_to_admin_panel_keyboard, get_admin_panel_keyboard
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from bot.middlewares.i18n import JsonI18n

router = Router(name="promo_manage_router")


async def get_promo_detail_text_and_keyboard(promo_id: int, session: AsyncSession, i18n: JsonI18n, current_lang: str):
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)
    promo = await promo_code_dal.get_promo_code_by_id(session, promo_id)
    if not promo:
        return None, None

    status = _("admin_promo_status_active") if promo.is_active else _("admin_promo_status_inactive")
    if promo.valid_until and promo.valid_until < datetime.now(timezone.utc):
        status = _("admin_promo_status_expired")
    elif promo.current_activations >= promo.max_activations:
        status = _("admin_promo_status_used_up")

    validity = _("admin_promo_valid_indefinitely")
    if promo.valid_until:
        validity = promo.valid_until.strftime("%d.%m.%Y %H:%M")

    created = promo.created_at.strftime("%d.%m.%Y %H:%M") if promo.created_at else "N/A"

    text = "\n".join([
        _("admin_promo_card_title", code=promo.code),
        _("admin_promo_card_bonus_days", days=promo.bonus_days),
        _("admin_promo_card_activations", current=promo.current_activations, max=promo.max_activations),
        _("admin_promo_card_validity", validity=validity),
        _("admin_promo_card_status", status=status),
        _("admin_promo_card_created", created=created),
        _("admin_promo_card_created_by", creator=promo.created_by_admin_id)
    ])

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=_("admin_promo_edit_button"), callback_data=f"promo_edit_select:{promo_id}"))
    builder.row(InlineKeyboardButton(text=_("admin_promo_toggle_status_button"), callback_data=f"promo_toggle:{promo_id}"))
    builder.row(InlineKeyboardButton(text=_("admin_promo_view_activations_button"), callback_data=f"promo_activations:{promo_id}:0"))
    builder.row(InlineKeyboardButton(text=_("admin_promo_delete_button"), callback_data=f"promo_delete:{promo_id}"))
    builder.row(InlineKeyboardButton(text=_("admin_promo_back_to_list_button"), callback_data="admin_action:promo_management"))

    return text, builder.as_markup()


async def view_promo_codes_handler(callback: types.CallbackQuery, i18n_data: dict, settings: Settings, session: AsyncSession):
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    if not i18n or not callback.message:
        await callback.answer("Error processing request.", show_alert=True)
        return
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)

    promo_models = await promo_code_dal.get_all_active_promo_codes(session, limit=20, offset=0)
    text = f"{_('admin_active_promos_list_header')}\n\n{_('admin_no_active_promos')}" if not promo_models else "\n".join(
        [_("admin_active_promos_list_header"), ""] + [
            f"🎟 <code>{p.code}</code> | 🎁 {p.bonus_days}д | 📊 {p.current_activations}/{p.max_activations} | ⏰ {p.valid_until.strftime('%d.%m.%Y') if p.valid_until else _('admin_promo_valid_indefinitely')}"
            for p in promo_models
        ]
    )
    
    await callback.message.edit_text(text, reply_markup=get_back_to_admin_panel_keyboard(current_lang, i18n), parse_mode="HTML")
    await callback.answer()


async def promo_management_handler(callback: types.CallbackQuery, i18n_data: dict, settings: Settings, session: AsyncSession):
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    if not i18n or not callback.message:
        await callback.answer("Error processing request.", show_alert=True)
        return
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)

    promo_models = await promo_code_dal.get_all_promo_codes_with_details(session, limit=50, offset=0)
    if not promo_models:
        await callback.message.edit_text(_("admin_promo_management_empty"), reply_markup=get_back_to_admin_panel_keyboard(current_lang, i18n), parse_mode="HTML")
        await callback.answer()
        return

    builder = InlineKeyboardBuilder()
    for promo in promo_models:
        builder.row(InlineKeyboardButton(text=f"📝 {promo.code}", callback_data=f"promo_detail:{promo.promo_code_id}"))
    builder.row(InlineKeyboardButton(text=_("back_to_admin_panel_button"), callback_data="admin_action:main"))
    
    await callback.message.edit_text(_("admin_promo_management_title"), reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("promo_detail:"))
async def promo_detail_handler(callback: types.CallbackQuery, i18n_data: dict, session: AsyncSession):
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    current_lang = i18n_data.get("current_language")
    if not i18n or not callback.message or not current_lang:
        await callback.answer("Error processing request.", show_alert=True)
        return
    
    try:
        promo_id = int(callback.data.split(":")[1])
        text, keyboard = await get_promo_detail_text_and_keyboard(promo_id, session, i18n, current_lang)
        if text:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await callback.answer(i18n.gettext(current_lang, "admin_promo_not_found"), show_alert=True)
    except (ValueError, IndexError):
        await callback.answer(i18n.gettext(current_lang, "admin_promo_not_found"), show_alert=True)
    await callback.answer()


@router.callback_query(F.data.startswith("promo_toggle:"))
async def promo_toggle_handler(callback: types.CallbackQuery, i18n_data: dict, session: AsyncSession):
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    current_lang = i18n_data.get("current_language")
    if not i18n or not callback.message or not current_lang:
        return await callback.answer("Language service error.", show_alert=True)
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)
    
    try:
        promo_id = int(callback.data.split(":")[1])
        promo = await promo_code_dal.get_promo_code_by_id(session, promo_id)
        if not promo:
            return await callback.answer(_("admin_promo_not_found"), show_alert=True)

        new_status = not promo.is_active
        if await promo_code_dal.update_promo_code(session, promo_id, {"is_active": new_status}):
            await session.commit()
            status_text = _("admin_promo_status_activated") if new_status else _("admin_promo_status_deactivated")
            await callback.answer(_("admin_promo_toggle_success", code=promo.code, status=status_text))
            
            text, keyboard = await get_promo_detail_text_and_keyboard(promo_id, session, i18n, current_lang)
            if text:
                await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await callback.answer(_("error_occurred_try_again"), show_alert=True)
    except (ValueError, IndexError):
        await callback.answer(_("admin_promo_not_found"), show_alert=True)


@router.callback_query(F.data.startswith("promo_activations:"))
async def promo_activations_handler(callback: types.CallbackQuery, i18n_data: dict, settings: Settings, session: AsyncSession):
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    current_lang = i18n_data.get("current_language")
    if not i18n or not callback.message or not current_lang:
        return await callback.answer("Error processing request.", show_alert=True)
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)

    try:
        parts = callback.data.split(":")
        promo_id = int(parts[1])
        page = int(parts[2])
        page_size = settings.LOGS_PAGE_SIZE

        promo = await promo_code_dal.get_promo_code_by_id(session, promo_id)
        if not promo:
            return await callback.answer(_("admin_promo_not_found"), show_alert=True)

        total_activations = await promo_code_dal.count_promo_activations_by_code_id(session, promo_id)
        activations = await promo_code_dal.get_promo_activations_by_code_id(session, promo_id, limit=page_size, offset=page * page_size)
        
        builder = InlineKeyboardBuilder()
        if not activations:
            text = _("admin_promo_no_activations", code=promo.code)
        else:
            text = _("admin_promo_activations_header", code=promo.code) + "\n\n"
            text += "\n".join([_("admin_promo_activation_item", user_id=a.user_id, date=a.activated_at.strftime("%d.%m.%Y %H:%M")) for a in activations])

        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"promo_activations:{promo_id}:{page-1}"))
        if (page + 1) * page_size < total_activations:
            nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"promo_activations:{promo_id}:{page+1}"))
        if nav_buttons:
            builder.row(*nav_buttons)

        builder.row(InlineKeyboardButton(text=_("admin_promo_export_csv_button"), callback_data=f"promo_export:{promo_id}"))
        builder.row(InlineKeyboardButton(text=_("admin_promo_back_to_detail_button"), callback_data=f"promo_detail:{promo_id}"))

        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except (ValueError, IndexError):
        await callback.answer(_("admin_promo_not_found"), show_alert=True)
    await callback.answer()


@router.callback_query(F.data.startswith("promo_export:"))
async def promo_export_activations_handler(callback: types.CallbackQuery, i18n_data: dict, session: AsyncSession):
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    current_lang = i18n_data.get("current_language")
    if not i18n or not callback.message or not current_lang:
        return await callback.answer("Error processing request.", show_alert=True)
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)

    try:
        promo_id = int(callback.data.split(":")[1])
        promo = await promo_code_dal.get_promo_code_by_id(session, promo_id)
        if not promo:
            return await callback.answer(_("admin_promo_not_found"), show_alert=True)

        activations = await promo_code_dal.get_promo_activations_by_code_id(session, promo_id)
        if not activations:
            return await callback.answer(_("admin_promo_no_activations", code=promo.code), show_alert=True)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["User ID", "Activation Date"])
        for act in activations:
            writer.writerow([act.user_id, act.activated_at.strftime("%Y-%m-%d %H:%M:%S")])
        
        output.seek(0)
        file = types.BufferedInputFile(output.getvalue().encode('utf-8'), filename=f"promo_{promo.code}_activations.csv")
        await callback.message.answer_document(file, caption=_("admin_promo_export_caption", code=promo.code))

    except (ValueError, IndexError):
        await callback.answer(_("admin_promo_not_found"), show_alert=True)
    await callback.answer()


@router.callback_query(F.data.startswith("promo_delete:"))
async def promo_delete_handler(callback: types.CallbackQuery, i18n_data: dict, session: AsyncSession):
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    current_lang = i18n_data.get("current_language")
    if not i18n or not callback.message or not current_lang:
        return await callback.answer("Language service error.", show_alert=True)
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)

    try:
        promo_id = int(callback.data.split(":")[1])
        promo = await promo_code_dal.delete_promo_code(session, promo_id)
        if promo:
            await session.commit()
            await callback.answer(_("admin_promo_deleted_success", code=promo.code), show_alert=True)
            await promo_management_handler(callback, i18n_data, {}, session) # Settings not needed here
        else:
            await callback.answer(_("admin_promo_not_found"), show_alert=True)
    except (ValueError, IndexError):
        await callback.answer(_("admin_promo_not_found"), show_alert=True)


# --- Promo Edit Handlers ---
@router.callback_query(F.data.startswith("promo_edit_select:"))
async def promo_edit_select_handler(callback: types.CallbackQuery, i18n_data: dict):
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    current_lang = i18n_data.get("current_language")
    if not i18n or not callback.message or not current_lang:
        return
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)
    promo_id = int(callback.data.split(":")[1])
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=_("admin_promo_edit_bonus_days"), callback_data=f"promo_edit_field:bonus_days:{promo_id}"))
    builder.row(InlineKeyboardButton(text=_("admin_promo_edit_max_activations"), callback_data=f"promo_edit_field:max_activations:{promo_id}"))
    builder.row(InlineKeyboardButton(text=_("admin_promo_edit_validity"), callback_data=f"promo_edit_field:valid_until:{promo_id}"))
    builder.row(InlineKeyboardButton(text=_("admin_promo_back_to_detail_button"), callback_data=f"promo_detail:{promo_id}"))
    
    await callback.message.edit_text(_("admin_promo_edit_select_field"), reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("promo_edit_field:"))
async def promo_edit_field_handler(callback: types.CallbackQuery, state: FSMContext, i18n_data: dict):
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    current_lang = i18n_data.get("current_language")
    if not i18n or not callback.message or not current_lang: return
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)
    
    _, field, promo_id_str = callback.data.split(":")
    await state.update_data(promo_id=int(promo_id_str), field_to_edit=field)
    
    prompts = {
        "bonus_days": "admin_promo_prompt_bonus_days",
        "max_activations": "admin_promo_prompt_max_activations",
        "valid_until": "admin_promo_prompt_validity_days"
    }
    await state.set_state(AdminStates.waiting_for_promo_edit_details)
    await callback.message.edit_text(_(prompts.get(field, "error_occurred_try_again")))
    await callback.answer()

@router.message(StateFilter(AdminStates.waiting_for_promo_edit_details))
async def process_promo_edit_details(message: types.Message, state: FSMContext, session: AsyncSession, i18n_data: dict):
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    current_lang = i18n_data.get("current_language")
    if not i18n or not message or not current_lang: return
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)
    
    data = await state.get_data()
    promo_id = data.get("promo_id")
    field = data.get("field_to_edit")
    
    try:
        value = message.text
        update_data = {}
        
        if field == "bonus_days":
            update_data["bonus_days"] = int(value)
        elif field == "max_activations":
            update_data["max_activations"] = int(value)
        elif field == "valid_until":
            if value.lower() in ['0', 'вечно', 'бессрочно', 'indefinite']:
                 update_data["valid_until"] = None
            else:
                days = int(value)
                update_data["valid_until"] = datetime.now(timezone.utc) + timedelta(days=days)

        if await promo_code_dal.update_promo_code(session, promo_id, update_data):
            await session.commit()
            await message.answer(_("admin_promo_edit_success"))
            
            # Reset state and show updated details
            await state.clear()
            text, keyboard = await get_promo_detail_text_and_keyboard(promo_id, session, i18n, current_lang)
            if text:
                await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await message.answer(_("error_occurred_try_again"))
            await state.clear()

    except (ValueError, TypeError):
        await message.answer(_("admin_promo_invalid_input"))
        # Don't clear state, let them try again


async def manage_promo_codes_handler(callback: types.CallbackQuery, i18n_data: dict, settings: Settings, session: AsyncSession):
    await promo_management_handler(callback, i18n_data, settings, session)
