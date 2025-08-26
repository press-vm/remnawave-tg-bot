import logging
from typing import Optional
from aiogram import Bot
from config.settings import Settings
from bot.middlewares.i18n import JsonI18n


class NotificationService:
    def __init__(self, bot: Bot, settings: Settings, i18n: JsonI18n):
        self.bot = bot
        self.settings = settings
        self.i18n = i18n

    async def notify_new_user_registration(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        referred_by_id: Optional[int] = None
    ) -> None:
        """Send notification to admins about new user registration"""
        if not self.settings.ADMIN_IDS:
            return

        admin_lang = self.settings.DEFAULT_LANGUAGE
        _ = lambda key, **kwargs: self.i18n.gettext(admin_lang, key, **kwargs)

        # Format user info
        user_info = f"🆔 {user_id}"
        if first_name:
            user_info += f"\n👤 {first_name}"
        if username:
            user_info += f"\n📱 @{username}"
        if referred_by_id:
            user_info += f"\n🎁 Referred by: {referred_by_id}"

        notification_text = _(
            "admin_new_user_notification",
            default="🎉 Новый пользователь зарегистрирован!\n\n{user_info}",
            user_info=user_info
        )

        # Send to all admins
        for admin_id in self.settings.ADMIN_IDS:
            try:
                await self.bot.send_message(admin_id, notification_text)
            except Exception as e:
                logging.error(f"Failed to send new user notification to admin {admin_id}: {e}")

    async def notify_subscription_created(
        self,
        user_id: int,
        subscription_type: str,
        duration_months: int,
        amount: Optional[float] = None
    ) -> None:
        """Send notification to admins about new subscription"""
        if not self.settings.ADMIN_IDS:
            return

        admin_lang = self.settings.DEFAULT_LANGUAGE
        _ = lambda key, **kwargs: self.i18n.gettext(admin_lang, key, **kwargs)

        amount_str = f"💰 {amount}₽" if amount else "🎁 Trial/Promo"
        
        notification_text = _(
            "admin_new_subscription_notification",
            default="💳 Новая подписка!\n\n🆔 Пользователь: {user_id}\n📅 Длительность: {duration} мес.\n💰 Сумма: {amount}\n📦 Тип: {type}",
            user_id=user_id,
            duration=duration_months,
            amount=amount_str,
            type=subscription_type
        )

        # Send to all admins
        for admin_id in self.settings.ADMIN_IDS:
            try:
                await self.bot.send_message(admin_id, notification_text)
            except Exception as e:
                logging.error(f"Failed to send subscription notification to admin {admin_id}: {e}")
