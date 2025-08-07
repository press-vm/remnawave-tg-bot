import logging
import hmac
import hashlib
import json
from typing import Optional

from aiohttp import web
from aiogram import Bot
from sqlalchemy.orm import sessionmaker

from config.settings import Settings
from bot.middlewares.i18n import JsonI18n
from bot.services.subscription_service import SubscriptionService
from bot.services.panel_api_service import PanelApiService
from bot.services.referral_service import ReferralService
from .notification_service import NotificationService
from bot.keyboards.inline.user_keyboards import get_connect_and_main_keyboard
from db.dal import payment_dal, user_dal, subscription_dal


def convert_period_to_months(period: Optional[str]) -> int:
    """Map Tribute subscription period strings to months."""
    if not period:
        return 1

    mapping = {
        "monthly": 1,
        "quarterly": 3,
        "3-month": 3,
        "3months": 3,
        "3-months": 3,
        "q": 3,
        "halfyearly": 6,
        "yearly": 12,
        "annual": 12,
        "y": 12,
    }
    return mapping.get(period.lower(), 1)


class TributeService:
    def __init__(
        self,
        bot: Bot,
        settings: Settings,
        i18n: JsonI18n,
        async_session_factory: sessionmaker,
        panel_service: PanelApiService,
        subscription_service: SubscriptionService,
        referral_service: ReferralService,
    ):
        self.bot = bot
        self.settings = settings
        self.i18n = i18n
        self.async_session_factory = async_session_factory
        self.panel_service = panel_service
        self.subscription_service = subscription_service
        self.referral_service = referral_service

    async def handle_webhook(self, raw_body: bytes, signature_header: Optional[str]) -> web.Response:
        settings = self.settings
        bot = self.bot
        i18n = self.i18n
        async_session_factory = self.async_session_factory
        subscription_service = self.subscription_service
        referral_service = self.referral_service

        if settings.TRIBUTE_API_KEY:
            if not signature_header:
                return web.Response(status=403, text="no_signature")
            expected_sig = hmac.new(settings.TRIBUTE_API_KEY.encode(), raw_body,
                                    hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected_sig, signature_header):
                return web.Response(status=403, text="invalid_signature")

        try:
            payload = json.loads(raw_body.decode())
        except Exception:
            return web.Response(status=400, text="bad_request")

        logging.info(
            "Tribute webhook data: %s",
            json.dumps(payload, ensure_ascii=False),
        )

        # Tribute webhook spec: only two events are sent
        # name: new_subscription | cancelled_subscription
        event_name = payload.get("name")
        data = payload.get("payload", {})

        # Mandatory routing fields
        user_id = data.get("telegram_user_id")
        if not user_id:
            return web.Response(status=400, text="missing_telegram_user_id")

        period_val = data.get("period")
        months = convert_period_to_months(period_val)

        # Tribute sends amount in minor units (kopecks/cents). Convert to major units before persisting.
        amount_value = data.get("amount") or data.get("price")
        currency = (data.get("currency") or settings.DEFAULT_CURRENCY_SYMBOL or "RUB").upper()
        if amount_value is not None:
            try:
                amount_minor_units = float(amount_value)
            except (TypeError, ValueError):
                amount_minor_units = 0.0
            amount_float = round(amount_minor_units / 100.0, 2)
        else:
            amount_float = 0.0

        async with async_session_factory() as session:
            if event_name == "new_subscription":
                # Build a stable provider payment id from subscription and timestamps
                provider_payment_id = str(data.get("subscription_id"))
                # Idempotent ensure payment
                payment_record = await payment_dal.ensure_payment_with_provider_id(
                    session,
                    user_id=int(user_id),
                    amount=amount_float,
                    currency=currency,
                    months=months,
                    description="Tribute subscription",
                    provider="tribute",
                    provider_payment_id=provider_payment_id,
                )

                activation_details = await subscription_service.activate_subscription(
                    session,
                    int(user_id),
                    months,
                    float(amount_float),
                    payment_record.payment_id,
                    provider="tribute",
                )
                referral_bonus = await referral_service.apply_referral_bonuses_for_payment(
                    session, int(user_id), months)
                await session.commit()

                db_user = await user_dal.get_user_by_id(session, int(user_id))
                lang = db_user.language_code if db_user and db_user.language_code else settings.DEFAULT_LANGUAGE
                _ = lambda k, **kw: i18n.gettext(lang, k, **kw)

                applied_ref_days = referral_bonus.get('referee_bonus_applied_days') if referral_bonus else None
                final_end = (referral_bonus.get('referee_new_end_date')
                             if referral_bonus else None)
                if not final_end:
                    final_end = activation_details.get('end_date')

                if final_end:
                    config_link = activation_details.get("subscription_url") or _(
                        "config_link_not_available"
                    )

                    if applied_ref_days:
                        inviter_name_display = _('friend_placeholder')
                        if db_user and db_user.referred_by_id:
                            inviter = await user_dal.get_user_by_id(session, db_user.referred_by_id)
                            if inviter and inviter.first_name:
                                inviter_name_display = inviter.first_name
                            elif inviter and inviter.username:
                                inviter_name_display = f"@{inviter.username}"
                        success_msg = _(
                            "payment_successful_with_referral_bonus_full",
                            months=months,
                            base_end_date=activation_details["end_date"].strftime('%Y-%m-%d'),
                            bonus_days=applied_ref_days,
                            final_end_date=final_end.strftime('%Y-%m-%d'),
                            inviter_name=inviter_name_display,
                            config_link=config_link,
                        )
                    else:
                        success_msg = _(
                            "payment_successful_full",
                            months=months,
                            end_date=final_end.strftime('%Y-%m-%d'),
                            config_link=config_link,
                        )
                    markup = get_connect_and_main_keyboard(
                        lang, i18n, settings, config_link
                    )

                    try:
                        await bot.send_message(
                            int(user_id),
                            success_msg,
                            reply_markup=markup,
                            parse_mode="HTML",
                            disable_web_page_preview=True,
                        )
                    except Exception as e:
                        logging.error(
                            f"Failed to send Tribute payment success message to user {user_id}: {e}")

                # Send notification about payment
                try:
                    notification_service = NotificationService(bot, settings, i18n)
                    user = await user_dal.get_user_by_id(session, int(user_id))
                    await notification_service.notify_payment_received(
                        user_id=int(user_id),
                        amount=float(amount_float),
                        currency=currency,
                        months=months,
                        payment_provider="tribute",
                        username=user.username if user else None
                    )
                except Exception as e:
                    logging.error(f"Failed to send tribute payment notification: {e}")
            elif event_name == "cancelled_subscription":
                await self._handle_tribute_cancellation(session, int(user_id), bot, i18n)
                
            else:
                await session.commit()
        return web.Response(status=200, text="ok")

    async def _handle_tribute_cancellation(self, session, user_id: int, bot: Bot, i18n: JsonI18n):
        """Handle tribute subscription cancellation - set subscription to 1 day grace period"""
        from datetime import datetime, timezone, timedelta
        from db.dal import subscription_dal, user_dal
        from bot.keyboards.inline.user_keyboards import get_subscribe_only_markup
        
        try:
            # Set all user's subscriptions to expire in 1 day (grace period)
            await subscription_dal.set_user_subscriptions_cancelled_with_grace(session, user_id, grace_days=1)
            await session.commit()
            
            # Send notification about cancellation if enabled
            if not self.settings.TRIBUTE_SKIP_CANCELLATION_NOTIFICATIONS:
                db_user = await user_dal.get_user_by_id(session, user_id)
                lang = db_user.language_code if db_user and db_user.language_code else self.settings.DEFAULT_LANGUAGE
                first_name = db_user.first_name or f"User {user_id}" if db_user else f"User {user_id}"
                
                _ = lambda k, **kw: i18n.gettext(lang, k, **kw) if i18n else k
                markup = get_subscribe_only_markup(lang, i18n)
                
                cancellation_msg = _(
                    "tribute_subscription_cancelled",
                    default="🚨 <b>Подписка отменена</b>\n\n"
                           "Ваша подписка Tribute была отменена. У вас есть 24 часа для восстановления доступа, "
                           "после чего подписка будет заблокирована.\n\n"
                           "Для продления подписки нажмите кнопку ниже.",
                    user_name=first_name
                )
                
                try:
                    await bot.send_message(
                        int(user_id),
                        cancellation_msg,
                        reply_markup=markup,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logging.error(f"Failed to send tribute cancellation notification to user {user_id}: {e}")
                    
            logging.info(f"Tribute subscription cancelled for user {user_id}, grace period set to 1 day")
            
        except Exception as e:
            logging.error(f"Error handling tribute cancellation for user {user_id}: {e}")
            await session.rollback()


async def tribute_webhook_route(request: web.Request):
    """AIOHTTP route handler for Tribute webhook calls."""
    tribute_service: TributeService = request.app['tribute_service']
    raw_body = await request.read()
    signature_header = request.headers.get('trbt-signature')
    return await tribute_service.handle_webhook(raw_body, signature_header)
