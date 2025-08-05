import logging
import random
import string
from aiogram import Router, F, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import Settings
from db.dal import promo_code_dal
from bot.states.admin_states import AdminStates
from bot.keyboards.inline.admin_keyboards import get_back_to_admin_panel_keyboard, get_admin_panel_keyboard
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from bot.middlewares.i18n import JsonI18n

router = Router(name="promo_bulk_router")


async def create_bulk_promo_prompt_handler(callback: types.CallbackQuery,
                                          state: FSMContext, i18n_data: dict,
                                          settings: Settings,
                                          session: AsyncSession):
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    if not i18n or not callback.message:
        await callback.answer("Error preparing bulk promo creation.",
                              show_alert=True)
        return
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)

    # Step 1: Ask for quantity
    prompt_text = _(
        "admin_bulk_promo_step1_quantity",
        default="🎟 <b>Массовое создание промокодов</b>\n\n<b>Шаг 1 из 4:</b> Количество\n\nВведите количество промокодов для создания (1-100):"
    )

    try:
        await callback.message.edit_text(
            prompt_text,
            reply_markup=get_back_to_admin_panel_keyboard(current_lang, i18n),
            parse_mode="HTML")
    except Exception as e:
        logging.warning(
            f"Could not edit message for bulk promo prompt: {e}. Sending new.")
        await callback.message.answer(
            prompt_text,
            reply_markup=get_back_to_admin_panel_keyboard(current_lang, i18n),
            parse_mode="HTML")
    await callback.answer()
    await state.set_state(AdminStates.waiting_for_bulk_promo_quantity)


def generate_unique_promo_code(length: int = 8) -> str:
    """Generate a unique random promo code"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


# Step 1: Process quantity
@router.message(AdminStates.waiting_for_bulk_promo_quantity, F.text)
async def process_bulk_promo_quantity_handler(message: types.Message,
                                             state: FSMContext,
                                             i18n_data: dict,
                                             settings: Settings):
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    if not i18n:
        await message.reply("Language service error.")
        return
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)

    try:
        quantity = int(message.text.strip())
        if not (1 <= quantity <= 100):
            await message.answer(_(
                "admin_bulk_promo_invalid_quantity",
                default="❌ Количество промокодов должно быть от 1 до 100"
            ))
            return
        
        await state.update_data(quantity=quantity)
        
        # Step 2: Ask for bonus days
        prompt_text = _(
            "admin_bulk_promo_step2_bonus_days",
            default="🎟 <b>Массовое создание промокодов</b>\n\n<b>Шаг 2 из 4:</b> Бонусные дни\n\nКоличество: <b>{quantity}</b>\n\nВведите количество бонусных дней для каждого промокода (1-365):",
            quantity=quantity
        )
        
        await message.answer(
            prompt_text,
            reply_markup=get_back_to_admin_panel_keyboard(current_lang, i18n),
            parse_mode="HTML"
        )
        await state.set_state(AdminStates.waiting_for_bulk_promo_bonus_days)
        
    except ValueError:
        await message.answer(_(
            "admin_promo_invalid_number",
            default="❌ Введите корректное число"
        ))
    except Exception as e:
        logging.error(f"Error processing bulk promo quantity: {e}")
        await message.answer(_("error_occurred_try_again"))


# Step 2: Process bonus days
@router.message(AdminStates.waiting_for_bulk_promo_bonus_days, F.text)
async def process_bulk_promo_bonus_days_handler(message: types.Message,
                                               state: FSMContext,
                                               i18n_data: dict,
                                               settings: Settings):
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    if not i18n:
        await message.reply("Language service error.")
        return
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)

    try:
        bonus_days = int(message.text.strip())
        if not (1 <= bonus_days <= 365):
            await message.answer(_(
                "admin_promo_invalid_bonus_days",
                default="❌ Количество бонусных дней должно быть от 1 до 365"
            ))
            return
        
        await state.update_data(bonus_days=bonus_days)
        
        # Step 3: Ask for max activations
        data = await state.get_data()
        prompt_text = _(
            "admin_bulk_promo_step3_max_activations",
            default="🎟 <b>Массовое создание промокодов</b>\n\n<b>Шаг 3 из 4:</b> Лимит активаций\n\nКоличество: <b>{quantity}</b>\nБонусные дни: <b>{bonus_days}</b>\n\nВведите максимальное количество активаций для каждого промокода (1-10000):",
            quantity=data.get("quantity"),
            bonus_days=bonus_days
        )
        
        await message.answer(
            prompt_text,
            reply_markup=get_back_to_admin_panel_keyboard(current_lang, i18n),
            parse_mode="HTML"
        )
        await state.set_state(AdminStates.waiting_for_bulk_promo_max_activations)
        
    except ValueError:
        await message.answer(_(
            "admin_promo_invalid_number",
            default="❌ Введите корректное число"
        ))
    except Exception as e:
        logging.error(f"Error processing bulk promo bonus days: {e}")
        await message.answer(_("error_occurred_try_again"))


# Step 3: Process max activations
@router.message(AdminStates.waiting_for_bulk_promo_max_activations, F.text)
async def process_bulk_promo_max_activations_handler(message: types.Message,
                                                    state: FSMContext,
                                                    i18n_data: dict,
                                                    settings: Settings):
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    if not i18n:
        await message.reply("Language service error.")
        return
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)

    try:
        max_activations = int(message.text.strip())
        if not (1 <= max_activations <= 10000):
            await message.answer(_(
                "admin_promo_invalid_max_activations",
                default="❌ Максимальное количество активаций должно быть от 1 до 10000"
            ))
            return
        
        await state.update_data(max_activations=max_activations)
        
        # Step 4: Ask for validity
        data = await state.get_data()
        prompt_text = _(
            "admin_bulk_promo_step4_validity",
            default="🎟 <b>Массовое создание промокодов</b>\n\n<b>Шаг 4 из 4:</b> Срок действия\n\nКоличество: <b>{quantity}</b>\nБонусные дни: <b>{bonus_days}</b>\nМакс. активаций: <b>{max_activations}</b>\n\nВыберите срок действия промокодов:",
            quantity=data.get("quantity"),
            bonus_days=data.get("bonus_days"),
            max_activations=max_activations
        )
        
        # Create keyboard for validity options
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("admin_promo_unlimited_validity", default="🔄 Без ограничений"),
                callback_data="bulk_promo_unlimited_validity"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=_("admin_promo_set_validity_days", default="📅 Указать дни"),
                callback_data="bulk_promo_set_validity"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=_("admin_back_to_panel", default="🔙 В админ панель"),
                callback_data="admin_action:main"
            )
        )
        
        await message.answer(
            prompt_text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        await state.set_state(AdminStates.waiting_for_bulk_promo_validity_days)
        
    except ValueError:
        await message.answer(_(
            "admin_promo_invalid_number",
            default="❌ Введите корректное число"
        ))
    except Exception as e:
        logging.error(f"Error processing bulk promo max activations: {e}")
        await message.answer(_("error_occurred_try_again"))


# Step 4: Handle unlimited validity
@router.callback_query(F.data == "bulk_promo_unlimited_validity", StateFilter(AdminStates.waiting_for_bulk_promo_validity_days))
async def process_bulk_promo_unlimited_validity(callback: types.CallbackQuery,
                                               state: FSMContext,
                                               i18n_data: dict,
                                               settings: Settings,
                                               session: AsyncSession):
    await state.update_data(validity_days=None)
    await create_bulk_promo_codes_final(callback, state, i18n_data, settings, session)


# Step 4: Handle set validity
@router.callback_query(F.data == "bulk_promo_set_validity", StateFilter(AdminStates.waiting_for_bulk_promo_validity_days))
async def process_bulk_promo_set_validity(callback: types.CallbackQuery,
                                         state: FSMContext,
                                         i18n_data: dict,
                                         settings: Settings):
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    if not i18n or not callback.message:
        await callback.answer("Error processing validity.", show_alert=True)
        return
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)

    data = await state.get_data()
    prompt_text = _(
        "admin_bulk_promo_enter_validity_days",
        default="🎟 <b>Массовое создание промокодов</b>\n\n<b>Шаг 4 из 4:</b> Срок действия\n\nКоличество: <b>{quantity}</b>\nБонусные дни: <b>{bonus_days}</b>\nМакс. активаций: <b>{max_activations}</b>\n\nВведите количество дней действия промокодов (1-365):",
        quantity=data.get("quantity"),
        bonus_days=data.get("bonus_days"),
        max_activations=data.get("max_activations")
    )
    
    try:
        await callback.message.edit_text(
            prompt_text,
            reply_markup=get_back_to_admin_panel_keyboard(current_lang, i18n),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            prompt_text,
            reply_markup=get_back_to_admin_panel_keyboard(current_lang, i18n),
            parse_mode="HTML"
        )
    await callback.answer()


# Step 4: Process validity days
@router.message(AdminStates.waiting_for_bulk_promo_validity_days, F.text)
async def process_bulk_promo_validity_days_handler(message: types.Message,
                                                  state: FSMContext,
                                                  i18n_data: dict,
                                                  settings: Settings,
                                                  session: AsyncSession):
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    if not i18n:
        await message.reply("Language service error.")
        return
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)

    try:
        validity_days = int(message.text.strip())
        if not (1 <= validity_days <= 365):
            await message.answer(_(
                "admin_promo_invalid_validity_days",
                default="❌ Срок действия должен быть от 1 до 365 дней"
            ))
            return
        
        await state.update_data(validity_days=validity_days)
        await create_bulk_promo_codes_final(message, state, i18n_data, settings, session)
        
    except ValueError:
        await message.answer(_(
            "admin_promo_invalid_number",
            default="❌ Введите корректное число"
        ))
    except Exception as e:
        logging.error(f"Error processing bulk promo validity days: {e}")
        await message.answer(_("error_occurred_try_again"))


async def create_bulk_promo_codes_final(callback_or_message,
                                       state: FSMContext,
                                       i18n_data: dict,
                                       settings: Settings,
                                       session: AsyncSession):
    """Final step - create multiple promo codes in database"""
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    if not i18n:
        return
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)

    try:
        data = await state.get_data()
        quantity = data["quantity"]
        
        # Show progress message
        progress_text = _(
            "admin_bulk_promo_creating",
            default="🔄 Создание {quantity} промокодов...",
            quantity=quantity
        )
        
        if hasattr(callback_or_message, 'message'):  # CallbackQuery
            try:
                await callback_or_message.message.edit_text(progress_text, parse_mode="HTML")
            except Exception:
                await callback_or_message.message.answer(progress_text, parse_mode="HTML")
            await callback_or_message.answer()
        else:  # Message
            await callback_or_message.answer(progress_text, parse_mode="HTML")
        
        # Generate and create promo codes
        created_codes = []
        failed_codes = []
        
        for i in range(quantity):
            try:
                # Generate unique code
                attempts = 0
                while attempts < 10:  # Max 10 attempts to generate unique code
                    promo_code = generate_unique_promo_code()
                    existing_promo = await promo_code_dal.get_promo_code_by_code(session, promo_code)
                    if not existing_promo:
                        break
                    attempts += 1
                
                if attempts >= 10:
                    failed_codes.append(f"Код #{i+1} (не удалось сгенерировать уникальный)")
                    continue
                
                # Prepare promo code data
                promo_data = {
                    "code": promo_code,
                    "bonus_days": data["bonus_days"],
                    "max_activations": data["max_activations"],
                    "current_activations": 0,
                    "is_active": True,
                    "created_by_admin_id": callback_or_message.from_user.id,
                    "created_at": datetime.now(timezone.utc)
                }
                
                # Set validity
                if data.get("validity_days"):
                    promo_data["valid_until"] = datetime.now(timezone.utc) + timedelta(days=data["validity_days"])
                else:
                    promo_data["valid_until"] = None
                
                # Create promo code
                created_promo = await promo_code_dal.create_promo_code(session, promo_data)
                created_codes.append(created_promo.code)
                
            except Exception as e:
                logging.error(f"Error creating bulk promo code #{i+1}: {e}")
                failed_codes.append(f"Код #{i+1} ({str(e)[:50]})")
        
        await session.commit()
        
        # Success message
        success_lines = [
            _(
                "admin_bulk_promo_created_title",
                default="✅ <b>Массовое создание завершено!</b>\n"
            ),
            _(
                "admin_bulk_promo_created_stats",
                default="📊 Создано: <b>{created}</b> из <b>{total}</b>",
                created=len(created_codes),
                total=quantity
            )
        ]
        
        if data.get("validity_days"):
            validity_text = f"{data['validity_days']} дней"
        else:
            validity_text = _("admin_promo_unlimited", default="Без ограничений")
        
        success_lines.append(
            _(
                "admin_bulk_promo_settings",
                default="🎁 Бонусные дни: <b>{bonus_days}</b>\n"
                       "📊 Макс. активаций: <b>{max_activations}</b>\n"
                       "⏰ Срок действия: <b>{validity}</b>",
                bonus_days=data["bonus_days"],
                max_activations=data["max_activations"],
                validity=validity_text
            )
        )
        
        if created_codes:
            success_lines.append("\n🎟 <b>Созданные коды:</b>")
            # Show first 20 codes, then indicate if there are more
            codes_to_show = created_codes[:20]
            for code in codes_to_show:
                success_lines.append(f"<code>{code}</code>")
            
            if len(created_codes) > 20:
                success_lines.append(f"... и еще {len(created_codes) - 20} кодов")
        
        if failed_codes:
            success_lines.append(f"\n❌ <b>Ошибки ({len(failed_codes)}):</b>")
            for error in failed_codes[:5]:  # Show first 5 errors
                success_lines.append(error)
            if len(failed_codes) > 5:
                success_lines.append(f"... и еще {len(failed_codes) - 5} ошибок")
        
        success_text = "\n".join(success_lines)
        
        if hasattr(callback_or_message, 'message'):  # CallbackQuery
            try:
                await callback_or_message.message.edit_text(
                    success_text,
                    reply_markup=get_back_to_admin_panel_keyboard(current_lang, i18n),
                    parse_mode="HTML"
                )
            except Exception:
                await callback_or_message.message.answer(
                    success_text,
                    reply_markup=get_back_to_admin_panel_keyboard(current_lang, i18n),
                    parse_mode="HTML"
                )
        else:  # Message
            await callback_or_message.answer(
                success_text,
                reply_markup=get_back_to_admin_panel_keyboard(current_lang, i18n),
                parse_mode="HTML"
            )
        
        await state.clear()
        
    except Exception as e:
        logging.error(f"Error creating bulk promo codes: {e}")
        error_text = _("error_occurred_try_again", default="❌ Произошла ошибка. Попробуйте снова.")
        
        if hasattr(callback_or_message, 'message'):  # CallbackQuery
            await callback_or_message.message.answer(error_text)
        else:  # Message
            await callback_or_message.answer(error_text)
        
        await state.clear()


# Cancel bulk promo creation
@router.callback_query(
    F.data == "admin_action:main",
    StateFilter(
        AdminStates.waiting_for_bulk_promo_quantity,
        AdminStates.waiting_for_bulk_promo_bonus_days,
        AdminStates.waiting_for_bulk_promo_max_activations,
        AdminStates.waiting_for_bulk_promo_validity_days,
    ),
)
async def cancel_bulk_promo_creation_state_to_menu(callback: types.CallbackQuery,
                                                   state: FSMContext,
                                                   settings: Settings,
                                                   i18n_data: dict,
                                                   session: AsyncSession):
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    if not i18n or not callback.message:
        await callback.answer("Error cancelling.", show_alert=True)
        return
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)

    try:
        await callback.message.edit_text(
            _(key="admin_panel_title"),
            reply_markup=get_admin_panel_keyboard(i18n, current_lang, settings)
        )
    except Exception:
        await callback.message.answer(
            _(key="admin_panel_title"),
            reply_markup=get_admin_panel_keyboard(i18n, current_lang, settings)
        )
    
    await callback.answer(_("admin_bulk_promo_creation_cancelled", default="Массовое создание промокодов отменено"))
    await state.clear()