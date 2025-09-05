import logging
import asyncio
from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import Settings
from db.dal import user_dal
from bot.services.panel_api_service import PanelApiService

router = Router(name="admin_update_names_router")


@router.message(Command("update_names"))
async def update_names_command(
    message: types.Message,
    settings: Settings,
    panel_service: PanelApiService,
    session: AsyncSession
):
    """Обновить имена всех пользователей в Remnawave (псевдоним для /update_all_names)"""
    await update_all_user_names_command(message, settings, panel_service, session)


@router.message(Command("update_all_names"))
async def update_all_user_names_command(
    message: types.Message,
    settings: Settings,
    panel_service: PanelApiService,
    session: AsyncSession
):
    """Обновить имена всех пользователей в Remnawave"""
    
    status_msg = await message.answer("⏳ Начинаю обновление имен пользователей в Remnawave...")
    
    try:
        # Получаем всех пользователей с panel_user_uuid
        users = await user_dal.get_all_users_with_panel_uuid(session)
        
        if not users:
            await status_msg.edit_text("❌ Не найдено пользователей с panel_user_uuid")
            return
        
        updated_count = 0
        error_count = 0
        
        total_users = len(users)
        await status_msg.edit_text(f"⏳ Обновляю имена для {total_users} пользователей...")
        
        for index, user in enumerate(users, 1):
            try:
                # Формируем описание
                full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
                
                if not full_name:
                    # Если имени нет, используем username или ID
                    if user.username:
                        description = f"@{user.username}"
                    else:
                        description = f"Telegram ID: {user.user_id}"
                else:
                    # Добавляем username если есть
                    if user.username:
                        description = f"{full_name} (@{user.username})"
                    else:
                        description = full_name
                
                # Обновляем в Remnawave
                update_result = await panel_service.update_user_details_on_panel(
                    user.panel_user_uuid,
                    {
                        "uuid": user.panel_user_uuid,
                        "description": description
                    },
                    log_response=False  # Не логировать каждый запрос
                )
                
                if update_result:
                    updated_count += 1
                    logging.info(f"Updated user {user.user_id}: {description}")
                else:
                    error_count += 1
                    logging.error(f"Failed to update user {user.user_id}")
                
                # Обновляем статус каждые 10 пользователей
                if index % 10 == 0:
                    progress = (index / total_users) * 100
                    await status_msg.edit_text(
                        f"⏳ Прогресс: {index}/{total_users} ({progress:.1f}%)\n"
                        f"✅ Обновлено: {updated_count}\n"
                        f"❌ Ошибок: {error_count}"
                    )
                    # Небольшая задержка чтобы не перегружать API
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                logging.error(f"Error updating user {user.user_id}: {e}")
                error_count += 1
                continue
        
        # Финальный отчет
        result_text = "📊 **Обновление завершено!**\n\n"
        result_text += f"👥 Всего пользователей: {total_users}\n"
        result_text += f"✅ Успешно обновлено: {updated_count}\n"
        if error_count > 0:
            result_text += f"❌ Ошибок: {error_count}"
        
        await status_msg.edit_text(result_text, parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"Critical error in update_all_names: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ Критическая ошибка: {str(e)}")


@router.message(Command("check_subs"))
async def check_subs_command(
    message: types.Message,
    settings: Settings,
    session: AsyncSession
):
    """Команда /check_subs - проверка подписок"""
    
    try:
        from db.dal import subscription_dal
        
        # Получаем статистику подписок
        active_subs = await subscription_dal.get_active_subscriptions_count(session)
        expired_subs = await subscription_dal.get_expired_subscriptions_count(session)
        trial_subs = await subscription_dal.get_trial_subscriptions_count(session)
        
        response_text = f"📋 <b>Проверка подписок</b>\n\n"
        response_text += f"✅ Активные: <b>{active_subs}</b>\n"
        response_text += f"❌ Истекшие: <b>{expired_subs}</b>\n"
        response_text += f"🆓 Пробные: <b>{trial_subs}</b>"
        
        await message.answer(response_text, parse_mode="HTML")
        
    except Exception as e:
        logging.error(f"Error in check_subs command: {e}")
        await message.answer(f"❌ Ошибка проверки подписок: {str(e)}")
