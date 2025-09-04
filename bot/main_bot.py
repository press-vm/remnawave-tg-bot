import logging
import asyncio
from typing import Dict, Any, Optional

from aiogram import Bot, Dispatcher
from aiogram.types import (MenuButtonDefault, MenuButtonWebApp, WebAppInfo, BotCommand)
from sqlalchemy.orm import sessionmaker

from config.settings import Settings
from db.database_setup import init_db_connection

# Новые модули архитектуры
from bot.app.controllers.dispatcher_controller import build_dispatcher
from bot.app.factories.build_services import build_core_services, validate_services
from bot.app.web.web_server import build_and_start_web_app, validate_webhook_config

from bot.routers import build_root_router
from bot.handlers.admin.sync_admin import perform_sync
from bot.utils.message_queue import init_queue_manager


async def register_all_routers(dp: Dispatcher, settings: Settings) -> None:
    """Регистрирует все роутеры приложения"""
    try:
        dp.include_router(build_root_router(settings))
        logging.info("✓ All application routers registered")
    except Exception as e:
        logging.error(f"❌ Error registering routers: {e}", exc_info=True)
        raise


async def on_startup_configured(dispatcher: Dispatcher) -> None:
    """Обработчик события запуска бота"""
    bot: Bot = dispatcher["bot_instance"]
    settings: Settings = dispatcher["settings"]
    i18n_instance = dispatcher["i18n_instance"]
    panel_service = dispatcher["panel_service"]
    async_session_factory: sessionmaker = dispatcher["async_session_factory"]

    logging.info("🚀 STARTUP: Configuring bot startup sequence...")

    try:
        # Настраиваем Telegram webhook
        await _configure_telegram_webhook(bot, settings, dispatcher)
        
        # Настраиваем меню и команды бота
        await _setup_bot_ui(bot, settings, i18n_instance)
        
        # Инициализируем менеджер очередей сообщений
        await _initialize_message_queue(dispatcher, bot)
        
        # Автоматическая синхронизация при запуске
        await _run_startup_sync(panel_service, async_session_factory, settings, i18n_instance)
        
        logging.info("✅ STARTUP: Bot configuration completed successfully")
        
    except Exception as e:
        logging.error(f"❌ STARTUP: Critical error during startup: {e}", exc_info=True)
        raise

    logging.info("STARTUP: Bot on_startup_configured completed.")


async def _configure_telegram_webhook(bot: Bot, settings: Settings, dispatcher: Dispatcher) -> None:
    """Настраивает Telegram webhook"""
    if not settings.WEBHOOK_BASE_URL:
        raise SystemExit("WEBHOOK_BASE_URL is required. Polling mode is disabled.")
    
    full_webhook_url = f"{str(settings.WEBHOOK_BASE_URL).rstrip('/')}/{settings.BOT_TOKEN}"
    
    if full_webhook_url == "ERROR_URL_TOKEN_DETECTED":
        logging.error("❌ STARTUP: Skipped webhook setup due to security error")
        return
    
    try:
        # Получаем текущую информацию о webhook
        current_info = await bot.get_webhook_info()
        logging.info(f"📡 Current webhook: {current_info.url or 'None'}")
        
        # Устанавливаем новый webhook
        success = await bot.set_webhook(
            url=full_webhook_url,
            drop_pending_updates=True,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
        
        if success:
            logging.info(f"✅ Telegram webhook set successfully")
        else:
            logging.error(f"❌ Failed to set webhook")
            
        # Проверяем результат
        new_info = await bot.get_webhook_info()
        if not new_info.url:
            logging.error("❌ CRITICAL: Webhook URL is empty after setup!")
            
    except Exception as e:
        logging.error(f"❌ Error setting up Telegram webhook: {e}", exc_info=True)
        raise


async def _setup_bot_ui(bot: Bot, settings: Settings, i18n_instance) -> None:
    """Настраивает UI элементы бота (меню, команды)"""
    try:
        # Настраиваем Mini App кнопку
        if settings.SUBSCRIPTION_MINI_APP_URL:
            menu_text = i18n_instance.gettext(
                settings.DEFAULT_LANGUAGE,
                "menu_my_subscription_inline",
            )
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text=menu_text,
                    web_app=WebAppInfo(url=settings.SUBSCRIPTION_MINI_APP_URL),
                )
            )
            await bot.set_chat_menu_button(menu_button=MenuButtonDefault())
            logging.info("✅ Mini app domain registered")

        # Устанавливаем команды
        if settings.START_COMMAND_DESCRIPTION:
            await bot.set_my_commands([
                BotCommand(command="start", description=settings.START_COMMAND_DESCRIPTION)
            ])
            logging.info("✅ Bot commands configured")
            
    except Exception as e:
        logging.error(f"❌ Error setting up bot UI: {e}", exc_info=True)


async def _initialize_message_queue(dispatcher: Dispatcher, bot: Bot) -> None:
    """Инициализирует менеджер очередей сообщений"""
    try:
        queue_manager = init_queue_manager(bot)
        dispatcher["queue_manager"] = queue_manager
        logging.info("✅ Message queue manager initialized")
    except Exception as e:
        logging.error(f"❌ Failed to initialize message queue manager: {e}", exc_info=True)


async def _run_startup_sync(panel_service, async_session_factory: sessionmaker, 
                           settings: Settings, i18n_instance) -> None:
    """Выполняет автоматическую синхронизацию при запуске"""
    try:
        logging.info("🔄 Running automatic panel sync...")
        
        async with async_session_factory() as session:
            sync_result = await perform_sync(
                panel_service=panel_service,
                session=session,
                settings=settings,
                i18n_instance=i18n_instance
            )
            
        if sync_result.get("status") == "completed":
            logging.info(f"✅ Startup sync completed: {sync_result.get('details', 'N/A')}")
        else:
            logging.warning(f"⚠️ Startup sync issues: {sync_result.get('status', 'unknown')}")
            
    except Exception as e:
        logging.error(f"❌ Failed to run startup sync: {e}", exc_info=True)


async def on_shutdown_configured(dispatcher: Dispatcher) -> None:
    """Обработчик события остановки бота"""
    logging.warning("🛑 SHUTDOWN: Starting shutdown sequence...")

    # Закрываем все сервисы
    service_keys = [
        "panel_service", "cryptopay_service", "tribute_service",
        "panel_webhook_service", "yookassa_service", "promo_code_service",
        "stars_service", "subscription_service", "referral_service",
    ]
    
    for service_key in service_keys:
        await _close_service_safely(dispatcher, service_key)

    # Закрываем бота
    bot: Bot = dispatcher["bot_instance"]
    if bot and bot.session:
        try:
            await bot.session.close()
            logging.info("✅ Bot session closed")
        except Exception as e:
            logging.warning(f"⚠️ Failed to close bot session: {e}")

    # Закрываем движок БД
    try:
        from db.database_setup import async_engine as global_async_engine
        if global_async_engine:
            await global_async_engine.dispose()
            logging.info("✅ Database engine disposed")
    except Exception as e:
        logging.warning(f"⚠️ Failed to dispose database engine: {e}")

    logging.info("✅ SHUTDOWN: Cleanup completed")


async def _close_service_safely(dispatcher: Dispatcher, service_key: str) -> None:
    """Безопасно закрывает сервис"""
    service = dispatcher.get(service_key)
    if not service:
        return

    # Пытаемся вызвать close()
    close_method = getattr(service, "close", None)
    if callable(close_method):
        try:
            await close_method()
            logging.info(f"✅ {service_key} closed")
            return
        except Exception as e:
            logging.warning(f"⚠️ Failed to close {service_key}: {e}")

    # Пытаемся вызвать close_session()
    close_session_method = getattr(service, "close_session", None)
    if callable(close_session_method):
        try:
            await close_session_method()
            logging.info(f"✅ {service_key} session closed")
        except Exception as e:
            logging.warning(f"⚠️ Failed to close session for {service_key}: {e}")


async def _get_bot_username(bot: Bot) -> str:
    """Получает username бота"""
    try:
        bot_info = await bot.get_me()
        username = bot_info.username or "unknown_bot"
        logging.info(f"🤖 Bot username resolved: @{username}")
        return username
    except Exception as e:
        logging.error(f"❌ Failed to get bot info: {e}")
        return "fallback_bot_username"


async def run_bot(settings_param: Settings) -> None:
    """
    Основная функция запуска бота с новой архитектурой
    
    Args:
        settings_param: Настройки приложения
    """
    try:
        logging.info("🚀 Starting bot initialization with new architecture...")
        
        # Валидация конфигурации webhook
        validate_webhook_config(settings_param)
        
        # Инициализация БД
        async_session_factory = init_db_connection(settings_param)
        if not async_session_factory:
            logging.critical("❌ Failed to initialize database connection")
            return

        # Создание диспетчера и бота через контроллер
        logging.info("🏗️ Building dispatcher and bot...")
        dp, bot, extras = build_dispatcher(settings_param, async_session_factory)
        i18n_instance = extras["i18n_instance"]

        # Получение username бота для YooKassa
        bot_username = await _get_bot_username(bot)

        # Создание всех сервисов через фабрику
        logging.info("🏭 Building core services...")
        services = build_core_services(
            settings_param,
            bot,
            async_session_factory,
            i18n_instance,
            bot_username,
        )
        
        # Валидация сервисов
        validate_services(services, settings_param)
        logging.info("✅ All services validated successfully")

        # Инжектируем сервисы в диспетчер
        for key, service in services.items():
            dp[key] = service

        # Инжектируем дополнительные зависимости
        dp["async_session_factory"] = async_session_factory

        # Регистрируем обработчики событий
        dp.startup.register(on_startup_configured)
        dp.shutdown.register(on_shutdown_configured)

        # Регистрируем роутеры
        await register_all_routers(dp, settings_param)

        logging.info("🌐 Starting bot in Webhook mode with AIOHTTP server...")
        
        logging.info("Starting bot in Webhook mode with AIOHTTP server...")
        logging.info("Starting bot with main tasks: ['WebServerTask']")
        
        # Запускаем веб-приложение с webhook'ами
        await build_and_start_web_app(
            dp=dp,
            bot=bot,
            settings=settings_param,
            services=services,
            async_session_factory=async_session_factory,
            i18n_instance=i18n_instance,
        )
        
    except Exception as e:
        logging.error(f"❌ Critical error in run_bot: {e}", exc_info=True)
        raise
    finally:
        logging.info("🏁 Bot run_bot function finished")


if __name__ == "__main__":
    # Этот блок не должен выполняться в production, но полезен для отладки
    import sys
    logging.warning("⚠️ main_bot.py executed directly - this should not happen in production")
    sys.exit(1)
