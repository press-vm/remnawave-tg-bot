import logging
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from typing import Optional, Dict, Any, Union
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import Settings
from db.dal import payment_dal
from bot.keyboards.inline.user_keyboards import (
    get_subscription_options_keyboard, get_payment_method_keyboard,
    get_payment_url_keyboard, get_back_to_main_menu_markup)
from bot.services.yookassa_service import YooKassaService
from bot.services.stars_service import StarsService
from bot.services.crypto_pay_service import CryptoPayService
from bot.services.subscription_service import SubscriptionService
from bot.services.panel_api_service import PanelApiService
from bot.services.referral_service import ReferralService
from bot.middlewares.i18n import JsonI18n

router = Router(name="user_subscription_router")


async def safe_callback_answer(callback: types.CallbackQuery, text: str = None, show_alert: bool = False):
    """Безопасное выполнение callback.answer() с обработкой ошибок"""
    try:
        await callback.answer(text, show_alert=show_alert)
    except Exception as e:
        logging.error(f"Failed to answer callback from user {callback.from_user.id}: {e}")


async def display_subscription_options(event: Union[types.Message,
                                                    types.CallbackQuery],
                                       i18n_data: dict, settings: Settings,
                                       session: AsyncSession):
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")

    get_text = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs
                                                  ) if i18n else key

    if not i18n:
        err_msg = "Language service error."
        if isinstance(event, types.CallbackQuery):
            await safe_callback_answer(event, err_msg, show_alert=True)
        elif isinstance(event, types.Message):
            await event.answer(err_msg)
        return

    currency_symbol_val = settings.DEFAULT_CURRENCY_SYMBOL
    text_content = get_text("select_subscription_period"
                            ) if settings.subscription_options else get_text(
                                "no_subscription_options_available")

    reply_markup = get_subscription_options_keyboard(
        settings.subscription_options, currency_symbol_val, current_lang, i18n
    ) if settings.subscription_options else get_back_to_main_menu_markup(
        current_lang, i18n)

    target_message_obj = event.message if isinstance(
        event, types.CallbackQuery) else event
    if not target_message_obj:
        if isinstance(event, types.CallbackQuery):
            await safe_callback_answer(event, get_text("error_occurred_try_again"), show_alert=True)
        return

    if isinstance(event, types.CallbackQuery):
        try:
            await target_message_obj.edit_text(text_content,
                                               reply_markup=reply_markup)
        except Exception as e:
            logging.warning(f"Failed to edit subscription options message: {e}")
            try:
                await target_message_obj.answer(text_content,
                                                reply_markup=reply_markup)
            except Exception as e_send:
                logging.error(f"Failed to send new subscription options message: {e_send}")
        
        await safe_callback_answer(event)
    else:
        try:
            await target_message_obj.answer(text_content,
                                            reply_markup=reply_markup)
        except Exception as e:
            logging.error(f"Failed to send subscription options message: {e}")


@router.callback_query(F.data.startswith("subscribe_period:"))
async def select_subscription_period_callback_handler(
        callback: types.CallbackQuery, settings: Settings, i18n_data: dict,
        session: AsyncSession):
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    get_text = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs
                                                  ) if i18n else key

    if not i18n or not callback.message:
        await safe_callback_answer(callback, get_text("error_occurred_try_again"), show_alert=True)
        return

    try:
        months = int(callback.data.split(":")[-1])
    except (ValueError, IndexError):
        logging.error(
            f"Invalid subscription period in callback_data: {callback.data}")
        await safe_callback_answer(callback, get_text("error_try_again"), show_alert=True)
        return

    price_rub = settings.subscription_options.get(months)
    if price_rub is None:
        logging.error(
            f"Price not found for {months} months subscription period in settings.subscription_options."
        )
        await safe_callback_answer(callback, get_text("error_try_again"), show_alert=True)
        return

    currency_symbol_val = settings.DEFAULT_CURRENCY_SYMBOL
    text_content = get_text("choose_payment_method")
    tribute_url = settings.tribute_payment_links.get(months)
    stars_price = settings.stars_subscription_options.get(months)
    reply_markup = get_payment_method_keyboard(
        months,
        price_rub,
        tribute_url,
        stars_price,
        currency_symbol_val,
        current_lang,
        i18n,
        settings,
    )

    try:
        await callback.message.edit_text(text_content,
                                         reply_markup=reply_markup)
    except Exception as e_edit:
        logging.warning(
            f"Edit message for payment method selection failed: {e_edit}. Sending new one."
        )
        try:
            await callback.message.answer(text_content,
                                          reply_markup=reply_markup)
        except Exception as e_send:
            logging.error(f"Failed to send payment method selection message: {e_send}")
    
    await safe_callback_answer(callback)


@router.callback_query(F.data.startswith("pay_stars:"))
async def pay_stars_callback_handler(
        callback: types.CallbackQuery, settings: Settings, i18n_data: dict,
        session: AsyncSession, bot: Bot, stars_service: StarsService):
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")

    get_text = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs) if i18n else key

    if not i18n or not callback.message:
        await safe_callback_answer(callback, get_text("error_occurred_try_again"), show_alert=True)
        return

    try:
        _, data_payload = callback.data.split(":", 1)
        months_str, price_str = data_payload.split(":")
        months = int(months_str)
        stars_price = int(price_str)
    except (ValueError, IndexError):
        logging.error(f"Invalid pay_stars data in callback: {callback.data}")
        await safe_callback_answer(callback, get_text("error_try_again"), show_alert=True)
        return

    user_id = callback.from_user.id
    payment_description = get_text("payment_description_subscription", months=months)

    try:
        payment_id = await stars_service.create_invoice(
            session, user_id, months, stars_price, payment_description)
        if payment_id is None:
            try:
                await callback.message.edit_text(get_text("error_payment_gateway"))
            except Exception as e:
                logging.error(f"Failed to edit message with payment gateway error: {e}")
            await safe_callback_answer(callback, get_text("error_try_again"), show_alert=True)
            return
    except Exception as e:
        logging.error(f"Error creating Stars invoice for user {user_id}: {e}")
        await safe_callback_answer(callback, get_text("error_payment_gateway"), show_alert=True)
        return

    await safe_callback_answer(callback)


@router.callback_query(F.data.startswith("pay_yk:"))
async def pay_yk_callback_handler(
        callback: types.CallbackQuery, settings: Settings, i18n_data: dict,
        yookassa_service: YooKassaService, session: AsyncSession):
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")

    get_text = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs
                                                  ) if i18n else key

    if not i18n or not callback.message:
        await safe_callback_answer(callback, get_text("error_occurred_try_again"), show_alert=True)
        return

    if not yookassa_service or not yookassa_service.configured:
        logging.error("YooKassa service is not configured or unavailable.")
        try:
            await callback.message.edit_text(get_text("payment_service_unavailable"))
        except Exception as e:
            logging.error(f"Failed to edit message with service unavailable: {e}")
        await safe_callback_answer(callback, get_text("payment_service_unavailable_alert"), show_alert=True)
        return

    try:
        _, data_payload = callback.data.split(":", 1)
        months_str, price_str = data_payload.split(":")
        months = int(months_str)
        price_rub = float(price_str)
    except (ValueError, IndexError):
        logging.error(
            f"Invalid pay_yk data in callback: {callback.data}")
        await safe_callback_answer(callback, get_text("error_try_again"), show_alert=True)
        return

    user_id = callback.from_user.id
    currency_code_for_yk = "RUB"

    payment_record_data = {
        "user_id": user_id,
        "amount": price_rub,
        "currency": currency_code_for_yk,
        "status": "pending_yookassa",
        "description": "Информационно-технологические услуги",  # Безопасное описание для БД
        "subscription_duration_months": months,
    }
    db_payment_record = None
    try:
        db_payment_record = await payment_dal.create_payment_record(
            session, payment_record_data)
        await session.commit()
        logging.info(
            f"Payment record {db_payment_record.payment_id} created for user {user_id} with status 'pending_yookassa'."
        )
    except Exception as e_db_payment:
        await session.rollback()
        logging.error(
            f"Failed to create payment record in DB for user {user_id}: {e_db_payment}",
            exc_info=True)
        try:
            await callback.message.edit_text(
                get_text("error_creating_payment_record"))
        except Exception as e:
            logging.error(f"Failed to edit message with payment record error: {e}")
        await safe_callback_answer(callback, get_text("error_try_again"), show_alert=True)
        return

    if not db_payment_record:
        try:
            await callback.message.edit_text(
                get_text("error_creating_payment_record"))
        except Exception as e:
            logging.error(f"Failed to edit message with payment record error: {e}")
        await safe_callback_answer(callback, get_text("error_try_again"), show_alert=True)
        return

    yookassa_metadata = {
        "user_id": str(user_id),
        "subscription_months": str(months),
        "payment_db_id": str(db_payment_record.payment_id),
    }
    receipt_email_for_yk = settings.YOOKASSA_DEFAULT_RECEIPT_EMAIL

    try:
        payment_response_yk = await yookassa_service.create_payment(
            amount=price_rub,
            currency=currency_code_for_yk,
            # Не передаём description - будет использована случайная безопасная формулировка
            metadata=yookassa_metadata,
            receipt_email=receipt_email_for_yk
        )
    except Exception as e:
        logging.error(f"Error creating YooKassa payment for user {user_id}: {e}")
        try:
            await callback.message.edit_text(get_text("error_payment_gateway"))
        except Exception as e_edit:
            logging.error(f"Failed to edit message with payment gateway error: {e_edit}")
        await safe_callback_answer(callback, get_text("error_try_again"), show_alert=True)
        return

    if payment_response_yk and payment_response_yk.get("confirmation_url"):
        try:
            await payment_dal.update_payment_status_by_db_id(
                session,
                payment_db_id=db_payment_record.payment_id,
                new_status=payment_response_yk.get("status", "pending"),
                yk_payment_id=payment_response_yk.get("id"))
            await session.commit()
        except Exception as e_db_update_ykid:
            await session.rollback()
            logging.error(
                f"Failed to update payment record {db_payment_record.payment_id} with YK ID: {e_db_update_ykid}",
                exc_info=True)
            try:
                await callback.message.edit_text(
                    get_text("error_payment_gateway_link_failed"))
            except Exception as e:
                logging.error(f"Failed to edit message with gateway link error: {e}")
            await safe_callback_answer(callback, get_text("error_try_again"), show_alert=True)
            return

        try:
            await callback.message.edit_text(
                get_text(key="payment_link_message", months=months),
                reply_markup=get_payment_url_keyboard(
                    payment_response_yk["confirmation_url"], current_lang, i18n),
                disable_web_page_preview=False)
        except Exception as e:
            logging.error(f"Failed to edit message with payment link: {e}")
    else:
        try:
            await payment_dal.update_payment_status_by_db_id(
                session, db_payment_record.payment_id, "failed_creation")
            await session.commit()
        except Exception as e_db_fail_create:
            await session.rollback()
            logging.error(
                f"Additionally failed to update payment record to 'failed_creation': {e_db_fail_create}",
                exc_info=True)

        logging.error(
            f"Failed to create payment in YooKassa for user {user_id}, payment_db_id {db_payment_record.payment_id}. Response: {payment_response_yk}"
        )
        try:
            await callback.message.edit_text(get_text("error_payment_gateway"))
        except Exception as e:
            logging.error(f"Failed to edit message with payment gateway error: {e}")

    await safe_callback_answer(callback)


@router.callback_query(F.data.startswith("pay_crypto:"))
async def pay_crypto_callback_handler(
        callback: types.CallbackQuery, settings: Settings, i18n_data: dict,
        cryptopay_service: CryptoPayService, session: AsyncSession):
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    get_text = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs) if i18n else key

    if not i18n or not callback.message:
        await safe_callback_answer(callback, get_text("error_occurred_try_again"), show_alert=True)
        return

    if not cryptopay_service or not cryptopay_service.configured:
        try:
            await callback.message.edit_text(get_text("payment_service_unavailable"))
        except Exception as e:
            logging.error(f"Failed to edit message with service unavailable: {e}")
        await safe_callback_answer(callback, get_text("payment_service_unavailable_alert"), show_alert=True)
        return

    try:
        _, data_payload = callback.data.split(":", 1)
        months_str, amount_str = data_payload.split(":")
        months = int(months_str)
        amount_val = float(amount_str)
    except (ValueError, IndexError):
        logging.error(f"Invalid pay_crypto data in callback: {callback.data}")
        await safe_callback_answer(callback, get_text("error_try_again"), show_alert=True)
        return

    user_id = callback.from_user.id
    description = get_text("payment_description_subscription", months=months)

    try:
        invoice_url = await cryptopay_service.create_invoice(
            session, user_id, months, amount_val, description)
        if invoice_url:
            try:
                await callback.message.edit_text(
                    get_text("payment_link_message", months=months),
                    reply_markup=get_payment_url_keyboard(invoice_url, current_lang, i18n),
                    disable_web_page_preview=False,
                )
            except Exception as e:
                logging.error(f"Failed to edit message with crypto payment link: {e}")
        else:
            try:
                await callback.message.edit_text(get_text("error_payment_gateway"))
            except Exception as e:
                logging.error(f"Failed to edit message with payment gateway error: {e}")
    except Exception as e:
        logging.error(f"Error creating CryptoPay invoice for user {user_id}: {e}")
        await safe_callback_answer(callback, get_text("error_payment_gateway"), show_alert=True)
        return
    
    await safe_callback_answer(callback)


@router.callback_query(F.data == "main_action:subscribe")
async def reshow_subscription_options_callback(callback: types.CallbackQuery,
                                               i18n_data: dict,
                                               settings: Settings,
                                               session: AsyncSession):
    await display_subscription_options(callback, i18n_data, settings, session)


async def my_subscription_command_handler(
    event: Union[types.Message, types.CallbackQuery],
    i18n_data: dict,
    settings: Settings,
    panel_service: PanelApiService,
    subscription_service: SubscriptionService,
    session: AsyncSession,
    bot: Bot
):
    target = event.message if isinstance(event, types.CallbackQuery) else event
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: JsonI18n = i18n_data.get("i18n_instance")
    get_text = lambda key, **kw: i18n.gettext(current_lang, key, **kw)

    if not i18n or not target:
        if isinstance(event, types.Message):
            try:
                await event.answer(get_text("error_occurred_try_again"))
            except Exception as e:
                logging.error(f"Failed to send error message: {e}")
        elif isinstance(event, types.CallbackQuery):
            await safe_callback_answer(event, get_text("error_occurred_try_again"), show_alert=True)
        return

    if not panel_service or not subscription_service:
        error_msg = get_text("error_service_unavailable")
        try:
            if isinstance(event, types.CallbackQuery):
                await event.message.edit_text(error_msg)
            else:
                await target.answer(error_msg)
        except Exception as e:
            logging.error(f"Failed to send service unavailable message: {e}")
        
        if isinstance(event, types.CallbackQuery):
            await safe_callback_answer(event)
        return

    try:
        active = await subscription_service.get_active_subscription_details(session, event.from_user.id)
    except Exception as e:
        logging.error(f"Error getting subscription details for user {event.from_user.id}: {e}")
        error_msg = get_text("error_service_unavailable")
        try:
            if isinstance(event, types.CallbackQuery):
                await event.message.edit_text(error_msg)
            else:
                await target.answer(error_msg)
        except Exception as e_send:
            logging.error(f"Failed to send service error message: {e_send}")
        
        if isinstance(event, types.CallbackQuery):
            await safe_callback_answer(event)
        return

    if not active:
        text = get_text("subscription_not_active")

        buy_button = InlineKeyboardButton(
            text=get_text("menu_subscribe_inline", default="Купить"),
            callback_data="main_action:subscribe"
        )
        back_markup = get_back_to_main_menu_markup(current_lang, i18n)

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [buy_button],
                *back_markup.inline_keyboard
            ]
        )

        if isinstance(event, types.CallbackQuery):
            await safe_callback_answer(event)
            try:
                await event.message.edit_text(text, reply_markup=kb)
            except Exception as e_edit:
                logging.warning(f"Failed to edit subscription message: {e_edit}")
                try:
                    await event.message.answer(text, reply_markup=kb)
                except Exception as e_send:
                    logging.error(f"Failed to send subscription message: {e_send}")
        else:
            try:
                await event.answer(text, reply_markup=kb)
            except Exception as e:
                logging.error(f"Failed to send subscription not active message: {e}")
        return

    end_date = active.get("end_date")
    days_left = (
        (end_date.date() - datetime.now().date()).days
        if end_date else 0
    )
    text = get_text(
        "my_subscription_details",
        end_date=end_date.strftime("%Y-%m-%d") if end_date else "N/A",
        days_left=max(0, days_left),
        status=active.get("status_from_panel", get_text("status_active")).capitalize(),
        config_link=active.get("config_link") or get_text("config_link_not_available"),
        traffic_limit=(
            f"{active['traffic_limit_bytes'] / 2**30:.2f} GB"
            if active.get("traffic_limit_bytes")
            else get_text("traffic_unlimited")
        ),
        traffic_used=(
            f"{active['traffic_used_bytes'] / 2**30:.2f} GB"
            if active.get("traffic_used_bytes") is not None
            else get_text("traffic_na")
        )
    )
    markup = get_back_to_main_menu_markup(current_lang, i18n)

    if isinstance(event, types.CallbackQuery):
        await safe_callback_answer(event)
        try:
            await event.message.edit_text(text, reply_markup=markup, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e_edit:
            logging.warning(f"Failed to edit subscription details message: {e_edit}")
            try:
                await bot.send_message(chat_id=target.chat.id, text=text, reply_markup=markup, parse_mode="HTML", disable_web_page_preview=True)
            except Exception as e_send:
                logging.error(f"Failed to send subscription details message: {e_send}")
    else:
        try:
            await target.answer(text, reply_markup=markup, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            logging.error(f"Failed to send subscription details message: {e}")


@router.pre_checkout_query()
async def stars_pre_checkout_handler(pre_checkout_query: types.PreCheckoutQuery):
    try:
        await pre_checkout_query.answer(ok=True)
    except Exception as e:
        logging.error(f"Failed to answer pre-checkout query: {e}")


@router.message(F.successful_payment)
async def stars_successful_payment_handler(
        message: types.Message, settings: Settings, i18n_data: dict,
        session: AsyncSession, stars_service: StarsService):
    sp = message.successful_payment
    if not sp or sp.currency != "XTR":
        return

    payload = sp.invoice_payload or ""
    try:
        payment_id_str, months_str = payload.split(":")
        payment_db_id = int(payment_id_str)
        months = int(months_str)
    except (ValueError, IndexError):
        logging.error(f"Invalid invoice payload for stars payment: {payload}")
        return

    stars_amount = sp.total_amount
    try:
        await stars_service.process_successful_payment(
            session, message, payment_db_id, months, stars_amount, i18n_data)
    except Exception as e:
        logging.error(f"Error processing successful Stars payment for user {message.from_user.id}: {e}")


@router.message(Command("connect"))
async def connect_command_handler(message: types.Message, i18n_data: dict,
                                  settings: Settings,
                                  panel_service: PanelApiService,
                                  subscription_service: SubscriptionService,
                                  session: AsyncSession, bot: Bot):
    logging.info(f"User {message.from_user.id} used /connect command.")
    try:
        await my_subscription_command_handler(message, i18n_data, settings,
                                              panel_service, subscription_service,
                                              session, bot)
    except Exception as e:
        logging.error(f"Error in connect command handler for user {message.from_user.id}: {e}")