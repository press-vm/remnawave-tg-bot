import logging
from typing import Dict

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.orm import sessionmaker

from config.settings import Settings
from bot.middlewares.db_session import DBSessionMiddleware
from bot.middlewares.i18n import I18nMiddleware, get_i18n_instance, JsonI18n
from bot.middlewares.ban_check_middleware import BanCheckMiddleware
from bot.middlewares.action_logger_middleware import ActionLoggerMiddleware
from bot.middlewares.profile_sync import ProfileSyncMiddleware


def build_dispatcher(settings: Settings, async_session_factory: sessionmaker) -> tuple[Dispatcher, Bot, Dict]:
    """
    Создаёт и настраивает диспетчер с ботом и всеми middleware
    
    Returns:
        tuple: (Dispatcher, Bot, extra_data)
            - Dispatcher: Настроенный диспетчер
            - Bot: Экземпляр бота
            - extra_data: Дополнительные данные (i18n_instance и др.)
    """
    try:
        storage = MemoryStorage()
        default_props = DefaultBotProperties(parse_mode=ParseMode.HTML)
        bot = Bot(token=settings.BOT_TOKEN, default=default_props)

        dp = Dispatcher(storage=storage, settings=settings, bot_instance=bot)

        i18n_instance = get_i18n_instance(path="locales", default=settings.DEFAULT_LANGUAGE)

        dp["i18n_instance"] = i18n_instance
        dp["async_session_factory"] = async_session_factory

        # Порядок middleware важен! Внешние выполняются первыми
        dp.update.outer_middleware(DBSessionMiddleware(async_session_factory))
        dp.update.outer_middleware(I18nMiddleware(i18n=i18n_instance, settings=settings))
        dp.update.outer_middleware(ProfileSyncMiddleware())
        dp.update.outer_middleware(BanCheckMiddleware(settings=settings, i18n_instance=i18n_instance))
        dp.update.outer_middleware(ActionLoggerMiddleware(settings=settings))

        logging.info("Dispatcher and Bot successfully created with all middleware configured")
        
        return dp, bot, {"i18n_instance": i18n_instance}
        
    except Exception as e:
        logging.error(f"Error building dispatcher: {e}", exc_info=True)
        raise