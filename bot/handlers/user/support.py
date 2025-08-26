import logging
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.text_decorations import html_decoration as hd
from typing import Optional, Union, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from bot.keyboards.inline.user_keyboards import InlineKeyboardMarkup, InlineKeyboardButton
from bot.states.user_states import UserSupportStates
from config.settings import Settings
from bot.middlewares.i18n import JsonI18n

router = Router(name="support_router")

# Хранилище активных диалогов поддержки
support_dialogs: Dict[int, Dict[str, Any]] = {}

@router.callback_query(F.data == "support:start_dialog")
async def start_support_dialog(callback: types.CallbackQuery, state: FSMContext, 
                              settings: Settings, i18n_data: dict, session: AsyncSession):
    """Активировать режим диалога с поддержкой"""
    user_id = callback.from_user.id
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs) if i18n else key
    
    # Регистрируем активный диалог
    support_dialogs[user_id] = {
        "started_at": datetime.now(),
        "username": callback.from_user.username,
        "first_name": callback.from_user.first_name,
        "last_name": callback.from_user.last_name,
        "language": current_lang
    }
    
    # Устанавливаем состояние FSM
    await state.set_state(UserSupportStates.waiting_for_message)
    
    dialog_text = _(
        "support_dialog_started",
        default="💬 Диалог с технической поддержкой начат!\n\n📝 Теперь все ваши сообщения будут переданы специалистам поддержки. Опишите вашу проблему или задайте вопрос.\n\n⏰ Мы ответим в ближайшее время в рабочие часы (09:00 - 21:00 МСК)."
    )
    
    end_dialog_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=_("support_end_dialog", default="❌ Завершить диалог"),
            callback_data="support:end_dialog"
        )]
    ])
    
    try:
        await callback.message.edit_text(dialog_text, reply_markup=end_dialog_keyboard, parse_mode="HTML")
        await callback.answer(_("support_dialog_started_alert", default="Диалог начат! Напишите ваш вопрос."))
    except Exception:
        await callback.message.answer(dialog_text, reply_markup=end_dialog_keyboard, parse_mode="HTML")
    
    # Уведомляем администраторов о новом диалоге
    user_display = hd.quote(callback.from_user.full_name)
    admin_notification = f"""
🔔 Новый диалог в поддержке

👤 Пользователь: {user_display}
🆔 ID: <code>{user_id}</code>
📱 Username: @{callback.from_user.username or 'отсутствует'}
🌍 Язык: {current_lang}
⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

💬 Ожидаем сообщение от пользователя...
📝 Для ответа используйте: <code>/reply {user_id} текст_ответа</code>
"""
    
    for admin_id in settings.ADMIN_IDS:
        try:
            await callback.bot.send_message(admin_id, admin_notification, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Failed to notify admin {admin_id} about new support dialog: {e}")

@router.callback_query(F.data == "support:end_dialog")
async def end_support_dialog(callback: types.CallbackQuery, state: FSMContext,
                           settings: Settings, i18n_data: dict, 
                           subscription_service, session: AsyncSession):
    """Завершить диалог с поддержкой"""
    user_id = callback.from_user.id
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs) if i18n else key
    
    # Удаляем диалог из активных
    if user_id in support_dialogs:
        dialog_info = support_dialogs[user_id]
        duration = datetime.now() - dialog_info["started_at"]
        del support_dialogs[user_id]
        
        # Уведомляем админов о завершении
        user_display = hd.quote(callback.from_user.full_name)
        admin_end_notification = f"""
❌ Диалог поддержки завершен

👤 Пользователь: {user_display} (ID: {user_id})
⏱ Длительность: {duration.total_seconds() // 60:.0f} мин.
⏰ Завершен: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
"""
        
        for admin_id in settings.ADMIN_IDS:
            try:
                await callback.bot.send_message(admin_id, admin_end_notification, parse_mode="HTML")
            except Exception as e:
                logging.error(f"Failed to notify admin {admin_id} about dialog end: {e}")
    
    # Очищаем состояние
    await state.clear()
    
    end_text = _(
        "support_dialog_ended",
        default="✅ Диалог с поддержкой завершен.\n\nСпасибо за обращение! Если возникнут новые вопросы, нажмите кнопку 'Поддержка' в главном меню."
    )
    
    # Возвращаемся в главное меню
    from bot.handlers.user.start import send_main_menu
    await send_main_menu(callback, settings, i18n_data, subscription_service, session, is_edit=True)
    await callback.answer(_("support_dialog_ended_alert", default="Диалог завершен"))

@router.message(UserSupportStates.waiting_for_message)
async def handle_support_message(message: types.Message, state: FSMContext,
                                settings: Settings, i18n_data: dict):
    """Обработка сообщений в режиме поддержки"""
    user_id = message.from_user.id
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs) if i18n else key
    
    if user_id not in support_dialogs:
        # Диалог не активен
        await message.answer(_(
            "support_dialog_not_active",
            default="❌ Диалог с поддержкой не активен. Нажмите кнопку 'Поддержка' в главном меню для начала."
        ))
        await state.clear()
        return
    
    user_display = hd.quote(message.from_user.full_name)
    
    # Формируем сообщение для администраторов
    if message.content_type == "text":
        admin_message = f"""
📨 Сообщение в поддержку

👤 От: {user_display}
🆔 ID: <code>{user_id}</code>
📱 Username: @{message.from_user.username or 'отсутствует'}
🌍 Язык: {current_lang}
⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

💬 Сообщение:
{hd.quote(message.text)}

📝 Для ответа: <code>/reply {user_id} ваш_ответ</code>
"""
        
        # Отправляем текст администраторам
        for admin_id in settings.ADMIN_IDS:
            try:
                await message.bot.send_message(admin_id, admin_message, parse_mode="HTML")
            except Exception as e:
                logging.error(f"Failed to forward support message to admin {admin_id}: {e}")
    
    else:
        # Обработка медиа-сообщений
        for admin_id in settings.ADMIN_IDS:
            try:
                # Пересылаем медиа
                await message.forward(admin_id)
                
                # Добавляем контекст
                context_text = f"""
📷 Медиа в поддержку от {user_display}

🆔 ID: <code>{user_id}</code>
🌍 Язык: {current_lang}
⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

📝 Для ответа: <code>/reply {user_id} ваш_ответ</code>
"""
                await message.bot.send_message(admin_id, context_text, parse_mode="HTML")
                
            except Exception as e:
                logging.error(f"Failed to forward support media to admin {admin_id}: {e}")
    
    # Подтверждение пользователю
    await message.answer(_(
        "support_message_received",
        default="✅ Ваше сообщение получено! Специалисты поддержки ответят в ближайшее время."
    ))

@router.message(Command("reply"))
async def admin_reply_command(message: types.Message, state: FSMContext, settings: Settings):
    """Команда администратора для ответа пользователю в поддержке"""
    if message.from_user.id not in settings.ADMIN_IDS:
        await message.answer("❌ У вас нет доступа к командам поддержки.")
        return
    
    # Парсим команду: /reply USER_ID текст
    command_args = message.text.split(" ", 2)
    if len(command_args) < 3:
        await message.answer("""
📋 <b>Формат команды поддержки:</b>
<code>/reply USER_ID текст_ответа</code>

📝 <b>Пример:</b>
<code>/reply 123456789 Спасибо за обращение! Проблема решается.</code>

📋 <b>Другие команды:</b>
<code>/support_dialogs</code> - активные диалоги
<code>/support_stats</code> - статистика обращений
""", parse_mode="HTML")
        return
    
    try:
        target_user_id = int(command_args[1])
        reply_text = command_args[2]
    except ValueError:
        await message.answer("❌ Неверный формат ID пользователя.")
        return
    
    # Отправляем ответ пользователю
    try:
        response_text = f"📞 <b>Ответ службы поддержки:</b>\n\n{reply_text}"
        await message.bot.send_message(target_user_id, response_text, parse_mode="HTML")
        
        # Подтверждение администратору
        dialog_info = support_dialogs.get(target_user_id, {})
        user_display = dialog_info.get("first_name", f"User {target_user_id}")
        
        confirmation_text = f"✅ Ответ отправлен пользователю {user_display} (ID: {target_user_id})"
        await message.answer(confirmation_text)
        
        # Логируем ответ для других админов
        log_text = f"""
📤 Ответ отправлен в поддержке

👤 Пользователю: {user_display} (ID: {target_user_id})
👨‍💼 Администратор: {hd.quote(message.from_user.full_name)}
💬 Ответ: {reply_text[:150]}{'...' if len(reply_text) > 150 else ''}
⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
"""
        
        for admin_id in settings.ADMIN_IDS:
            if admin_id != message.from_user.id:  # Не отправляем отправителю
                try:
                    await message.bot.send_message(admin_id, log_text, parse_mode="HTML")
                except Exception as e:
                    logging.error(f"Failed to log reply to admin {admin_id}: {e}")
        
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить ответ: {e}")

@router.message(Command("support_dialogs"))
async def list_support_dialogs(message: types.Message, settings: Settings):
    """Показать активные диалоги поддержки"""
    if message.from_user.id not in settings.ADMIN_IDS:
        return
    
    if not support_dialogs:
        await message.answer("📭 Активных диалогов поддержки нет.")
        return
    
    dialogs_text = "📋 <b>Активные диалоги поддержки:</b>\n\n"
    for user_id, info in support_dialogs.items():
        user_display = info.get("first_name", f"User {user_id}")
        started = info.get("started_at", datetime.now())
        username = info.get("username")
        
        dialogs_text += f"👤 {user_display}\n"
        dialogs_text += f"🆔 <code>{user_id}</code>\n"
        if username:
            dialogs_text += f"📱 @{username}\n"
        dialogs_text += f"⏰ Начат: {started.strftime('%d.%m %H:%M')}\n"
        dialogs_text += f"📝 <code>/reply {user_id} текст</code>\n\n"
    
    await message.answer(dialogs_text, parse_mode="HTML")

@router.message(Command("support_stats"))
async def support_statistics(message: types.Message, settings: Settings):
    """Статистика поддержки"""
    if message.from_user.id not in settings.ADMIN_IDS:
        return
    
    total_dialogs = len(support_dialogs)
    now = datetime.now()
    
    # Подсчитываем диалоги за сегодня
    today_dialogs = sum(1 for info in support_dialogs.values() 
                       if info.get("started_at", now).date() == now.date())
    
    stats_text = f"""
📊 <b>Статистика поддержки</b>

💬 Активных диалогов: <b>{total_dialogs}</b>
📅 Начато сегодня: <b>{today_dialogs}</b>
⏰ Время: {now.strftime('%d.%m.%Y %H:%M:%S')}

📋 Команды:
• <code>/support_dialogs</code> - список диалогов
• <code>/reply USER_ID текст</code> - ответить
• <code>/support_stats</code> - эта статистика
"""
    
    await message.answer(stats_text, parse_mode="HTML")
