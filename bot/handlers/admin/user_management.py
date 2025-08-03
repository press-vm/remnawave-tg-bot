import logging
import re
from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hcode, hbold
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from config.settings import Settings
from db.dal import user_dal, subscription_dal, message_log_dal
from db.models import User
from bot.states.admin_states import AdminStates
from bot.keyboards.inline.admin_keyboards import get_back_to_admin_panel_keyboard
from bot.services.subscription_service import SubscriptionService
from bot.services.panel_api_service import PanelApiService
from bot.middlewares.i18n import JsonI18n
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

router = Router(name="admin_user_management_router")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{5,32}$")


async def user_management_menu_handler(callback: types.CallbackQuery,
                                      state: FSMContext, i18n_data: dict,
                                      settings: Settings, session: AsyncSession):
    """Display user management menu"""
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    if not i18n or not callback.message:
        await callback.answer("Error preparing user management.", show_alert=True)
        return
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)

    prompt_text = _(
        "admin_user_management_prompt",
        default="👤 Управление пользователями\n\nВведите ID пользователя или @username для поиска:"
    )

    try:
        await callback.message.edit_text(
            prompt_text,
            reply_markup=get_back_to_admin_panel_keyboard(current_lang, i18n)
        )
    except Exception as e:
        logging.warning(f"Could not edit message for user management: {e}. Sending new.")
        await callback.message.answer(
            prompt_text,
            reply_markup=get_back_to_admin_panel_keyboard(current_lang, i18n)
        )
    
    await callback.answer()
    await state.set_state(AdminStates.waiting_for_user_search)


def get_user_card_keyboard(user_id: int, i18n_instance, lang: str) -> InlineKeyboardBuilder:
    """Generate keyboard for user management actions"""
    _ = lambda key, **kwargs: i18n_instance.gettext(lang, key, **kwargs)
    builder = InlineKeyboardBuilder()
    
    # Row 1: Trial and Subscription actions
    builder.button(
        text=_(key="admin_user_reset_trial_button", default="🔄 Сбросить триал"),
        callback_data=f"user_action:reset_trial:{user_id}"
    )
    builder.button(
        text=_(key="admin_user_add_subscription_button", default="➕ Добавить дни"),
        callback_data=f"user_action:add_subscription:{user_id}"
    )
    
    # Row 2: Block/Unblock and Message
    builder.button(
        text=_(key="admin_user_toggle_ban_button", default="🚫 Заблокировать/Разблокировать"),
        callback_data=f"user_action:toggle_ban:{user_id}"
    )
    builder.button(
        text=_(key="admin_user_send_message_button", default="✉️ Отправить сообщение"),
        callback_data=f"user_action:send_message:{user_id}"
    )
    
    # Row 3: View actions
    builder.button(
        text=_(key="admin_user_view_logs_button", default="📜 Действия пользователя"),
        callback_data=f"user_action:view_logs:{user_id}"
    )
    builder.button(
        text=_(key="admin_user_refresh_button", default="🔄 Обновить"),
        callback_data=f"user_action:refresh:{user_id}"
    )
    
    # Row 4: Back button
    builder.button(
        text=_(key="admin_user_search_new_button", default="🔍 Найти другого"),
        callback_data="admin_action:users_management"
    )
    builder.button(
        text=_(key="back_to_admin_panel_button"),
        callback_data="admin_action:main"
    )
    
    builder.adjust(2, 2, 2, 2)
    return builder


async def format_user_card(user: User, session: AsyncSession, 
                          subscription_service: SubscriptionService,
                          i18n_instance, lang: str) -> str:
    """Format user information as a detailed card"""
    _ = lambda key, **kwargs: i18n_instance.gettext(lang, key, **kwargs)
    
    # Basic user info
    card_parts = []
    card_parts.append(f"👤 <b>{_('admin_user_card_title', default='Карточка пользователя')}</b>\n")
    
    # User details
    user_name = user.first_name or "N/A"
    username_display = f"@{user.username}" if user.username else "N/A"
    registration_date = user.registration_date.strftime('%Y-%m-%d %H:%M') if user.registration_date else "N/A"
    
    card_parts.append(f"🆔 <b>ID:</b> {hcode(str(user.user_id))}")
    card_parts.append(f"👤 <b>Имя:</b> {hcode(user_name)}")
    card_parts.append(f"📱 <b>Username:</b> {hcode(username_display)}")
    card_parts.append(f"🌍 <b>Язык:</b> {hcode(user.language_code or 'N/A')}")
    card_parts.append(f"📅 <b>Регистрация:</b> {hcode(registration_date)}")
    
    # Ban status
    ban_status = "🚫 Заблокирован" if user.is_banned else "✅ Активен"
    card_parts.append(f"🛡 <b>Статус:</b> {ban_status}")
    
    # Referral info
    if user.referred_by_id:
        card_parts.append(f"🎁 <b>Привлечен по реферальной программе от:</b> {hcode(str(user.referred_by_id))}")
    
    # Panel info
    if user.panel_user_uuid:
        card_parts.append(f"🔗 <b>Panel UUID:</b> {hcode(user.panel_user_uuid[:8] + '...' if len(user.panel_user_uuid) > 8 else user.panel_user_uuid)}")
    
    card_parts.append("")  # Empty line
    
    # Subscription info
    try:
        subscription_details = await subscription_service.get_active_subscription_details(session, user.user_id)
        if subscription_details:
            card_parts.append(f"💳 <b>{_('admin_user_subscription_info', default='Информация о подписке:')}</b>")
            
            end_date = subscription_details.get('end_date')
            if end_date:
                end_date_str = end_date.strftime('%Y-%m-%d %H:%M') if isinstance(end_date, datetime) else str(end_date)
                card_parts.append(f"⏰ <b>Действует до:</b> {hcode(end_date_str)}")
            
            status = subscription_details.get('status_from_panel', 'UNKNOWN')
            card_parts.append(f"📊 <b>Статус на панели:</b> {hcode(status)}")
            
            traffic_limit = subscription_details.get('traffic_limit_bytes')
            traffic_used = subscription_details.get('traffic_used_bytes')
            if traffic_limit and traffic_used is not None:
                traffic_limit_gb = traffic_limit / (1024**3)
                traffic_used_gb = traffic_used / (1024**3)
                card_parts.append(f"📊 <b>Трафик:</b> {hcode(f'{traffic_used_gb:.2f}GB / {traffic_limit_gb:.2f}GB')}")
        else:
            card_parts.append(f"💳 <b>Подписка:</b> {hcode('Отсутствует')}")
    except Exception as e:
        logging.error(f"Error getting subscription details for user {user.user_id}: {e}")
        card_parts.append(f"💳 <b>Подписка:</b> {hcode('Ошибка загрузки')}")
    
    # Statistics
    try:
        # Count user logs
        logs_count = await message_log_dal.count_user_message_logs(session, user.user_id)
        card_parts.append(f"📜 <b>Всего действий:</b> {hcode(str(logs_count))}")
        
        # Check if user had any subscriptions
        had_subscriptions = await subscription_service.has_had_any_subscription(session, user.user_id)
        trial_status = "Использовал" if had_subscriptions else "Не использовал"
        card_parts.append(f"🆓 <b>Триал:</b> {hcode(trial_status)}")
        
    except Exception as e:
        logging.error(f"Error getting user statistics for {user.user_id}: {e}")
    
    return "\n".join(card_parts)


@router.message(AdminStates.waiting_for_user_search, F.text)
async def process_user_search_handler(message: types.Message, state: FSMContext,
                                     settings: Settings, i18n_data: dict,
                                     subscription_service: SubscriptionService,
                                     session: AsyncSession):
    """Process user search input and display user card"""
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    if not i18n:
        await message.reply("Language service error.")
        return
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)

    input_text = message.text.strip() if message.text else ""
    user_model: Optional[User] = None

    # Try to find user by ID or username
    if input_text.isdigit():
        try:
            user_model = await user_dal.get_user_by_id(session, int(input_text))
        except ValueError:
            pass
    elif input_text.startswith("@") and USERNAME_REGEX.match(input_text[1:]):
        user_model = await user_dal.get_user_by_username(session, input_text[1:])
    elif USERNAME_REGEX.match(input_text):
        user_model = await user_dal.get_user_by_username(session, input_text)

    if not user_model:
        await message.answer(_(
            "admin_user_not_found",
            default="❌ Пользователь не найден: {input}",
            input=hcode(input_text)
        ))
        return

    # Store user ID in state for further operations
    await state.update_data(target_user_id=user_model.user_id)
    await state.clear()

    # Format and send user card
    try:
        user_card_text = await format_user_card(user_model, session, subscription_service, i18n, current_lang)
        keyboard = get_user_card_keyboard(user_model.user_id, i18n, current_lang)
        
        await message.answer(
            user_card_text,
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Error displaying user card for {user_model.user_id}: {e}")
        await message.answer(_(
            "admin_user_card_error",
            default="❌ Ошибка отображения карточки пользователя"
        ))


@router.callback_query(F.data.startswith("user_action:"))
async def user_action_handler(callback: types.CallbackQuery, state: FSMContext,
                             settings: Settings, i18n_data: dict, bot: Bot,
                             subscription_service: SubscriptionService,
                             panel_service: PanelApiService,
                             session: AsyncSession):
    """Handle user management actions"""
    try:
        parts = callback.data.split(":")
        action = parts[1]
        user_id = int(parts[2])
    except (IndexError, ValueError):
        await callback.answer("Invalid action format.", show_alert=True)
        return

    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    if not i18n:
        await callback.answer("Language service error.", show_alert=True)
        return
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)

    # Get user from database
    user = await user_dal.get_user_by_id(session, user_id)
    if not user:
        await callback.answer(_(
            "admin_user_not_found_action",
            default="Пользователь не найден"
        ), show_alert=True)
        return

    if action == "reset_trial":
        await handle_reset_trial(callback, user, subscription_service, session, i18n, current_lang)
    elif action == "add_subscription":
        await handle_add_subscription_prompt(callback, state, user, i18n, current_lang)
    elif action == "toggle_ban":
        await handle_toggle_ban(callback, user, panel_service, session, i18n, current_lang)
    elif action == "send_message":
        await handle_send_message_prompt(callback, state, user, i18n, current_lang)
    elif action == "view_logs":
        await handle_view_user_logs(callback, user, session, settings, i18n, current_lang)
    elif action == "refresh":
        await handle_refresh_user_card(callback, user, subscription_service, session, i18n, current_lang)
    else:
        await callback.answer(_("admin_unknown_action"), show_alert=True)


async def handle_reset_trial(callback: types.CallbackQuery, user: User,
                           subscription_service: SubscriptionService,
                           session: AsyncSession, i18n_instance, lang: str):
    """Reset user's trial eligibility"""
    _ = lambda key, **kwargs: i18n_instance.gettext(lang, key, **kwargs)
    
    try:
        # Deactivate all user subscriptions
        await subscription_dal.deactivate_all_user_subscriptions(session, user.user_id)
        await session.commit()
        
        await callback.answer(_(
            "admin_user_trial_reset_success",
            default="✅ Триал сброшен! Пользователь может активировать триал заново."
        ), show_alert=True)
        
        # Refresh user card
        await handle_refresh_user_card(callback, user, subscription_service, session, i18n_instance, lang)
        
    except Exception as e:
        logging.error(f"Error resetting trial for user {user.user_id}: {e}")
        await session.rollback()
        await callback.answer(_(
            "admin_user_trial_reset_error",
            default="❌ Ошибка сброса триала"
        ), show_alert=True)


async def handle_add_subscription_prompt(callback: types.CallbackQuery, state: FSMContext,
                                       user: User, i18n_instance, lang: str):
    """Prompt admin to enter subscription days to add"""
    _ = lambda key, **kwargs: i18n_instance.gettext(lang, key, **kwargs)
    
    await state.update_data(target_user_id=user.user_id)
    await state.set_state(AdminStates.waiting_for_subscription_days_to_add)
    
    prompt_text = _(
        "admin_user_add_subscription_prompt",
        default="➕ Добавление дней подписки для пользователя {user_id}\n\nВведите количество дней для добавления:",
        user_id=user.user_id
    )
    
    try:
        await callback.message.edit_text(prompt_text)
    except Exception:
        await callback.message.answer(prompt_text)
    
    await callback.answer()


async def handle_toggle_ban(callback: types.CallbackQuery, user: User,
                          panel_service: PanelApiService, session: AsyncSession,
                          i18n_instance, lang: str):
    """Toggle user ban status"""
    _ = lambda key, **kwargs: i18n_instance.gettext(lang, key, **kwargs)
    
    try:
        new_ban_status = not user.is_banned
        
        # Update in database
        await user_dal.update_user(session, user.user_id, {"is_banned": new_ban_status})
        
        # Update on panel if user has panel UUID
        if user.panel_user_uuid:
            panel_status = "DISABLED" if new_ban_status else "ACTIVE"
            await panel_service.update_user_status_on_panel(user.panel_user_uuid, not new_ban_status)
        
        await session.commit()
        
        status_text = "заблокирован" if new_ban_status else "разблокирован"
        await callback.answer(_(
            "admin_user_ban_toggle_success",
            default="✅ Пользователь {status}",
            status=status_text
        ), show_alert=True)
        
        # Refresh user card with updated ban status
        user.is_banned = new_ban_status  # Update local object
        await handle_refresh_user_card(callback, user, None, session, i18n_instance, lang)
        
    except Exception as e:
        logging.error(f"Error toggling ban for user {user.user_id}: {e}")
        await session.rollback()
        await callback.answer(_(
            "admin_user_ban_toggle_error",
            default="❌ Ошибка изменения статуса блокировки"
        ), show_alert=True)


async def handle_send_message_prompt(callback: types.CallbackQuery, state: FSMContext,
                                   user: User, i18n_instance, lang: str):
    """Prompt admin to enter message to send to user"""
    _ = lambda key, **kwargs: i18n_instance.gettext(lang, key, **kwargs)
    
    await state.update_data(target_user_id=user.user_id)
    await state.set_state(AdminStates.waiting_for_direct_message_to_user)
    
    prompt_text = _(
        "admin_user_send_message_prompt",
        default="✉️ Отправка сообщения пользователю {user_id}\n\nВведите текст сообщения:",
        user_id=user.user_id
    )
    
    try:
        await callback.message.edit_text(prompt_text)
    except Exception:
        await callback.message.answer(prompt_text)
    
    await callback.answer()


async def handle_view_user_logs(callback: types.CallbackQuery, user: User,
                              session: AsyncSession, settings: Settings,
                              i18n_instance, lang: str):
    """Show recent user logs"""
    _ = lambda key, **kwargs: i18n_instance.gettext(lang, key, **kwargs)
    
    try:
        # Get recent logs for user
        logs = await message_log_dal.get_user_message_logs(session, user.user_id, limit=10, offset=0)
        
        if not logs:
            await callback.answer(_(
                "admin_user_no_logs",
                default="📜 У пользователя нет действий"
            ), show_alert=True)
            return
        
        logs_text_parts = [f"📜 <b>Последние действия пользователя {user.user_id}:</b>\n"]
        
        for log in logs:
            timestamp = log.timestamp.strftime('%Y-%m-%d %H:%M') if log.timestamp else 'N/A'
            event_type = log.event_type or 'N/A'
            content_preview = (log.content or '')[:50] + ('...' if len(log.content or '') > 50 else '')
            
            logs_text_parts.append(
                f"🕐 {hcode(timestamp)} - {hcode(event_type)}\n"
                f"   {content_preview}"
            )
        
        logs_text = "\n\n".join(logs_text_parts)
        
        # Create inline keyboard for full logs
        builder = InlineKeyboardBuilder()
        builder.button(
            text=_(key="admin_user_view_all_logs_button", default="📋 Все действия"),
            callback_data=f"admin_logs:view_user:{user.user_id}:0"
        )
        builder.button(
            text=_(key="admin_user_back_to_card_button", default="🔙 К карточке"),
            callback_data=f"user_action:refresh:{user.user_id}"
        )
        builder.adjust(1)
        
        try:
            await callback.message.edit_text(
                logs_text,
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
        except Exception:
            await callback.message.answer(
                logs_text,
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
        
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Error viewing logs for user {user.user_id}: {e}")
        await callback.answer(_(
            "admin_user_logs_error",
            default="❌ Ошибка загрузки действий пользователя"
        ), show_alert=True)


async def handle_refresh_user_card(callback: types.CallbackQuery, user: User,
                                  subscription_service: SubscriptionService,
                                  session: AsyncSession, i18n_instance, lang: str):
    """Refresh user card with latest information"""
    try:
        # Reload user from database
        fresh_user = await user_dal.get_user_by_id(session, user.user_id)
        if not fresh_user:
            await callback.answer("User not found", show_alert=True)
            return
        
        user_card_text = await format_user_card(fresh_user, session, subscription_service, i18n_instance, lang)
        keyboard = get_user_card_keyboard(fresh_user.user_id, i18n_instance, lang)
        
        try:
            await callback.message.edit_text(
                user_card_text,
                reply_markup=keyboard.as_markup(),
                parse_mode="HTML"
            )
        except Exception:
            await callback.message.answer(
                user_card_text,
                reply_markup=keyboard.as_markup(),
                parse_mode="HTML"
            )
        
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Error refreshing user card for {user.user_id}: {e}")
        await callback.answer("Error refreshing user card", show_alert=True)


# Message handlers for state-based inputs

@router.message(AdminStates.waiting_for_subscription_days_to_add, F.text)
async def process_subscription_days_handler(message: types.Message, state: FSMContext,
                                           settings: Settings, i18n_data: dict,
                                           subscription_service: SubscriptionService,
                                           session: AsyncSession):
    """Process subscription days input"""
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    if not i18n:
        await message.reply("Language service error.")
        return
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)

    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    if not target_user_id:
        await message.answer("Error: target user not found in state")
        await state.clear()
        return

    try:
        days_to_add = int(message.text.strip())
        if days_to_add <= 0 or days_to_add > 3650:  # Max 10 years
            raise ValueError("Invalid days count")
    except ValueError:
        await message.answer(_(
            "admin_user_invalid_days",
            default="❌ Неверное количество дней. Введите число от 1 до 3650."
        ))
        return

    try:
        # Extend subscription
        result = await subscription_service.extend_active_subscription_days(
            session, target_user_id, days_to_add, "admin_manual_extension"
        )
        
        if result:
            await session.commit()
            await message.answer(_(
                "admin_user_subscription_added_success",
                default="✅ Успешно добавлено {days} дней подписки пользователю {user_id}",
                days=days_to_add,
                user_id=target_user_id
            ))
            
            # Show updated user card
            user = await user_dal.get_user_by_id(session, target_user_id)
            if user:
                user_card_text = await format_user_card(user, session, subscription_service, i18n, current_lang)
                keyboard = get_user_card_keyboard(user.user_id, i18n, current_lang)
                
                await message.answer(
                    user_card_text,
                    reply_markup=keyboard.as_markup(),
                    parse_mode="HTML"
                )
        else:
            await session.rollback()
            await message.answer(_(
                "admin_user_subscription_added_error",
                default="❌ Ошибка добавления дней подписки"
            ))
    
    except Exception as e:
        logging.error(f"Error adding subscription days for user {target_user_id}: {e}")
        await session.rollback()
        await message.answer(_(
            "admin_user_subscription_added_error",
            default="❌ Ошибка добавления дней подписки"
        ))
    
    await state.clear()


@router.message(AdminStates.waiting_for_direct_message_to_user, F.text)
async def process_direct_message_handler(message: types.Message, state: FSMContext,
                                       settings: Settings, i18n_data: dict,
                                       bot: Bot, session: AsyncSession):
    """Process direct message to user"""
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    if not i18n:
        await message.reply("Language service error.")
        return
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)

    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    if not target_user_id:
        await message.answer("Error: target user not found in state")
        await state.clear()
        return

    message_text = message.text.strip()
    if len(message_text) > 4000:
        await message.answer(_(
            "admin_user_message_too_long",
            default="❌ Сообщение слишком длинное (максимум 4000 символов)"
        ))
        return

    try:
        # Get target user
        target_user = await user_dal.get_user_by_id(session, target_user_id)
        if not target_user:
            await message.answer("Target user not found")
            await state.clear()
            return

        # Prepare message with admin signature
        admin_signature = _(
            "admin_direct_message_signature",
            default="\n\n---\n💬 Сообщение от администратора"
        )
        full_message = message_text + admin_signature

        # Send message to user
        await bot.send_message(target_user_id, full_message)
        
        # Confirm to admin
        await message.answer(_(
            "admin_user_message_sent_success",
            default="✅ Сообщение отправлено пользователю {user_id}",
            user_id=target_user_id
        ))
        
        # Show user card again
        user_card_text = await format_user_card(target_user, session, None, i18n, current_lang)
        keyboard = get_user_card_keyboard(target_user.user_id, i18n, current_lang)
        
        await message.answer(
            user_card_text,
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logging.error(f"Error sending direct message to user {target_user_id}: {e}")
        await message.answer(_(
            "admin_user_message_sent_error",
            default="❌ Ошибка отправки сообщения"
        ))
    
    await state.clear()