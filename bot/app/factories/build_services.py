import logging
from typing import Dict, Any
from aiogram import Bot
from sqlalchemy.orm import sessionmaker

from config.settings import Settings
from bot.middlewares.i18n import JsonI18n
from bot.services.yookassa_service import YooKassaService
from bot.services.panel_api_service import PanelApiService
from bot.services.subscription_service import SubscriptionService
from bot.services.referral_service import ReferralService
from bot.services.promo_code_service import PromoCodeService
from bot.services.stars_service import StarsService
from bot.services.tribute_service import TributeService
from bot.services.crypto_pay_service import CryptoPayService
from bot.services.panel_webhook_service import PanelWebhookService


def build_core_services(
    settings: Settings,
    bot: Bot,
    async_session_factory: sessionmaker,
    i18n: JsonI18n,
    bot_username_for_default_return: str,
) -> Dict[str, Any]:
    """
    Создаёт все основные сервисы приложения
    
    Args:
        settings: Настройки приложения
        bot: Экземпляр бота
        async_session_factory: Фабрика сессий БД
        i18n: Экземпляр интернационализации
        bot_username_for_default_return: Username бота для YooKassa URL
        
    Returns:
        Dict: Словарь со всеми сервисами
    """
    try:
        logging.info("Building core services...")
        
        # Базовый сервис для работы с панелью
        panel_service = PanelApiService(settings)
        
        # Основной сервис подписок
        subscription_service = SubscriptionService(
            settings, panel_service, bot, i18n
        )
        
        # Реферальная система
        referral_service = ReferralService(
            settings, subscription_service, bot, i18n
        )
        
        # Промокоды
        promo_code_service = PromoCodeService(
            settings, subscription_service, bot, i18n
        )
        
        # Telegram Stars
        stars_service = StarsService(
            bot, settings, i18n, subscription_service, referral_service
        )
        
        # CryptoPay
        cryptopay_service = CryptoPayService(
            settings.CRYPTOPAY_TOKEN,
            settings.CRYPTOPAY_NETWORK,
            bot,
            settings,
            i18n,
            async_session_factory,
            subscription_service,
            referral_service,
        )
        
        # Tribute
        tribute_service = TributeService(
            bot,
            settings,
            i18n,
            async_session_factory,
            panel_service,
            subscription_service,
            referral_service,
        )
        
        # Panel Webhook Service
        panel_webhook_service = PanelWebhookService(
            bot, settings, i18n, async_session_factory, panel_service
        )
        
        # YooKassa (последний, так как использует bot_username)
        yookassa_service = YooKassaService(
            shop_id=settings.YOOKASSA_SHOP_ID,
            secret_key=settings.YOOKASSA_SECRET_KEY,
            configured_return_url=settings.YOOKASSA_RETURN_URL,
            bot_username_for_default_return=bot_username_for_default_return,
            settings_obj=settings,
        )

        services = {
            "panel_service": panel_service,
            "subscription_service": subscription_service,
            "referral_service": referral_service,
            "promo_code_service": promo_code_service,
            "stars_service": stars_service,
            "cryptopay_service": cryptopay_service,
            "tribute_service": tribute_service,
            "panel_webhook_service": panel_webhook_service,
            "yookassa_service": yookassa_service,
        }
        
        logging.info(f"Successfully built {len(services)} core services")
        return services
        
    except Exception as e:
        logging.error(f"Error building core services: {e}", exc_info=True)
        raise


def validate_services(services: Dict[str, Any], settings: Settings) -> None:
    """
    Проверяет корректность созданных сервисов
    
    Args:
        services: Словарь сервисов
        settings: Настройки приложения
    """
    required_services = [
        "panel_service",
        "subscription_service", 
        "referral_service",
        "promo_code_service",
        "stars_service",
        "cryptopay_service",
        "tribute_service", 
        "panel_webhook_service",
        "yookassa_service"
    ]
    
    missing_services = []
    for service_name in required_services:
        if service_name not in services or services[service_name] is None:
            missing_services.append(service_name)
    
    if missing_services:
        raise ValueError(f"Missing required services: {', '.join(missing_services)}")
    
    # Проверяем настройки критически важных сервисов
    warnings = []
    
    if not settings.PANEL_API_URL:
        warnings.append("PANEL_API_URL not configured - panel operations will fail")
    
    if not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY:
        warnings.append("YooKassa not fully configured - payments may fail")
        
    if not settings.CRYPTOPAY_TOKEN:
        warnings.append("CryptoPay not configured - crypto payments unavailable")
        
    if warnings:
        for warning in warnings:
            logging.warning(f"Service configuration warning: {warning}")
    
    logging.info("Service validation completed successfully")