import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from sqlalchemy.orm import sessionmaker
from typing import Dict, Any

from config.settings import Settings


async def build_and_start_web_app(
    dp: Dispatcher,
    bot: Bot,
    settings: Settings,
    services: Dict[str, Any],
    async_session_factory: sessionmaker,
    i18n_instance,
) -> None:
    """
    Создаёт и запускает веб-приложение с webhook routes
    
    Args:
        dp: Диспетчер
        bot: Экземпляр бота  
        settings: Настройки приложения
        async_session_factory: Фабрика сессий БД
    """
    try:
        logging.info("Building web application...")
        
        app = web.Application()
        
        # Инжектируем зависимости в приложение
        app["bot"] = bot
        app["dp"] = dp
        app["settings"] = settings
        app["async_session_factory"] = async_session_factory
        
        # Добавляем i18n
        app["i18n"] = i18n_instance
        
        # Инжектируем все сервисы
        for key, service in services.items():
            app[key] = service

        # Настраиваем aiogram интеграцию с aiohttp
        setup_application(app, dp, bot=bot)

        # Настраиваем routes
        _setup_webhook_routes(app, settings)
        
        # Создаём и запускаем сервер
        await _start_server(app, settings)
        
    except Exception as e:
        logging.error(f"Error in build_and_start_web_app: {e}", exc_info=True)
        raise


def _setup_webhook_routes(app: web.Application, settings: Settings) -> None:
    """
    Настраивает все webhook routes
    
    Args:
        app: Web приложение
        settings: Настройки приложения
    """
    routes_configured = 0
    
    # Telegram webhook (обязательный если есть WEBHOOK_BASE_URL)
    if settings.WEBHOOK_BASE_URL:
        telegram_webhook_path = f"/{settings.BOT_TOKEN}"
        app.router.add_post(
            telegram_webhook_path, 
            SimpleRequestHandler(
                dispatcher=app["dp"], 
                bot=app["bot"]
            )
        )
        logging.info(f"✓ Telegram webhook configured: [POST] {telegram_webhook_path}")
        routes_configured += 1

    # YooKassa webhook
    if settings.WEBHOOK_BASE_URL and settings.yookassa_webhook_path:
        yk_path = settings.yookassa_webhook_path
        if yk_path.startswith("/"):
            from bot.handlers.user.payment import yookassa_webhook_route
            app.router.add_post(yk_path, yookassa_webhook_route)
            logging.info(f"✓ YooKassa webhook configured: [POST] {yk_path}")
            routes_configured += 1

    # Tribute webhook
    tribute_path = settings.tribute_webhook_path
    if tribute_path and tribute_path.startswith("/"):
        from bot.services.tribute_service import tribute_webhook_route
        app.router.add_post(tribute_path, tribute_webhook_route)
        logging.info(f"✓ Tribute webhook configured: [POST] {tribute_path}")
        routes_configured += 1

    # CryptoPay webhook
    cp_path = settings.cryptopay_webhook_path
    if cp_path and cp_path.startswith("/"):
        from bot.services.crypto_pay_service import cryptopay_webhook_route
        app.router.add_post(cp_path, cryptopay_webhook_route)
        logging.info(f"✓ CryptoPay webhook configured: [POST] {cp_path}")
        routes_configured += 1

    # Panel webhook
    panel_path = settings.panel_webhook_path
    if panel_path and panel_path.startswith("/"):
        from bot.services.panel_webhook_service import panel_webhook_route
        app.router.add_post(panel_path, panel_webhook_route)
        logging.info(f"✓ Panel webhook configured: [POST] {panel_path}")
        routes_configured += 1
    
    logging.info(f"Total webhook routes configured: {routes_configured}")


async def _start_server(app: web.Application, settings: Settings) -> None:
    """
    Запускает веб-сервер
    
    Args:
        app: Web приложение
        settings: Настройки приложения
    """
    try:
        # Создаём AppRunner
        web_app_runner = web.AppRunner(app)
        await web_app_runner.setup()
        
        # Создаём TCP сайт
        site = web.TCPSite(
            web_app_runner,
            host=settings.WEB_SERVER_HOST,
            port=settings.WEB_SERVER_PORT,
        )

        # Запускаем сервер
        await site.start()
        logging.info(
            f"AIOHTTP server started on http://{settings.WEB_SERVER_HOST}:{settings.WEB_SERVER_PORT}"
        )
        logging.info(
            f"🚀 AIOHTTP server started on http://{settings.WEB_SERVER_HOST}:{settings.WEB_SERVER_PORT}"
        )

        # Ждём бесконечно (пока не будет отменено)
        await asyncio.Event().wait()
        
    except asyncio.CancelledError:
        logging.info("Web server task was cancelled")
        raise
    except Exception as e:
        logging.error(f"Error starting web server: {e}", exc_info=True)
        raise


def validate_webhook_config(settings: Settings) -> None:
    """
    Проверяет корректность конфигурации webhook
    
    Args:
        settings: Настройки приложения
        
    Raises:
        ValueError: Если конфигурация некорректна
    """
    if not settings.WEBHOOK_BASE_URL:
        raise ValueError("WEBHOOK_BASE_URL is required for webhook mode")
    
    if not settings.BOT_TOKEN:
        raise ValueError("BOT_TOKEN is required")
    
    # Проверяем что порт валидный
    try:
        port = int(settings.WEB_SERVER_PORT)
        if not (1 <= port <= 65535):
            raise ValueError(f"Invalid port number: {port}")
    except (ValueError, TypeError):
        raise ValueError(f"Invalid WEB_SERVER_PORT: {settings.WEB_SERVER_PORT}")
    
    # Предупреждения о потенциальных проблемах
    warnings = []
    
    if not settings.yookassa_webhook_path:
        warnings.append("YooKassa webhook path not configured")
    
    if not settings.tribute_webhook_path:
        warnings.append("Tribute webhook path not configured")
        
    if not settings.cryptopay_webhook_path:
        warnings.append("CryptoPay webhook path not configured")
        
    if not settings.panel_webhook_path:
        warnings.append("Panel webhook path not configured")
    
    for warning in warnings:
        logging.warning(f"Webhook configuration: {warning}")
    
    logging.info("Webhook configuration validation completed")