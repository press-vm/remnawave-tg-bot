import logging
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from typing import Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from config.settings import Settings
from bot.services.panel_api_service import PanelApiService
from bot.services.notification_service import NotificationService

from db.dal import user_dal, subscription_dal, panel_sync_dal

from bot.middlewares.i18n import JsonI18n

router = Router(name="admin_sync_router")


async def perform_sync(panel_service: PanelApiService, session: AsyncSession, 
                      settings: Settings, i18n_instance: JsonI18n) -> dict:
    """
    Perform panel synchronization and return results
    Returns dict with status, details, and sync statistics
    """
    panel_records_checked = 0
    users_found_in_db = 0
    users_updated = 0
    subscriptions_synced_count = 0
    sync_errors = []
    
    # Additional counters for detailed logging
    users_without_telegram_id = 0
    users_not_found_in_db = 0
    users_created = 0
    users_uuid_updated = 0
    subscriptions_created = 0
    subscriptions_updated = 0

    try:
        panel_users_data = await panel_service.get_all_panel_users()

        if panel_users_data is None:
            error_msg = "Failed to fetch users from panel or panel API issue."
            sync_errors.append(error_msg)
            await panel_sync_dal.update_panel_sync_status(session, "failed", error_msg)
            await session.commit()
            return {"status": "failed", "details": error_msg, "errors": sync_errors}

        if not panel_users_data:
            status_msg = "No users found in the panel to sync."
            await panel_sync_dal.update_panel_sync_status(
                session, "success", status_msg, 0, 0
            )
            await session.commit()
            return {"status": "success", "details": status_msg, "users_synced": 0, "subs_synced": 0}

        total_panel_users = len(panel_users_data)
        logging.info(f"Starting sync for {total_panel_users} panel users.")

        for panel_user_dict in panel_users_data:
            try:
                panel_records_checked += 1
                panel_uuid = panel_user_dict.get("uuid")
                panel_subscription_uuid = panel_user_dict.get("subscriptionUuid") or panel_user_dict.get("shortUuid")
                telegram_id_from_panel = panel_user_dict.get("telegramId")

                if not panel_uuid:
                    sync_errors.append(f"Panel user missing UUID: {panel_user_dict}")
                    logging.warning(f"Skipping panel user without UUID: {panel_user_dict}")
                    continue

                # Track users without telegram ID
                if not telegram_id_from_panel:
                    users_without_telegram_id += 1

                # Try to find existing user in local DB
                existing_user = None
                
                # First, try to find by telegram ID if available
                if telegram_id_from_panel:
                    existing_user = await user_dal.get_user_by_id(session, telegram_id_from_panel)
                    if existing_user:
                        logging.debug(f"Found user by telegramId {telegram_id_from_panel}")
                
                # If not found by telegram ID, try to find by panel UUID
                if not existing_user:
                    existing_user = await user_dal.get_user_by_panel_uuid(session, panel_uuid)
                    if existing_user:
                        logging.info(f"Found user by panel UUID {panel_uuid}, telegramId: {existing_user.user_id}")
                        # Update telegram ID if it was missing in panel data but we have local user
                        if telegram_id_from_panel and existing_user.user_id != telegram_id_from_panel:
                            logging.warning(f"TelegramId mismatch: panel={telegram_id_from_panel}, local={existing_user.user_id}")
                
                if not existing_user:
                    users_not_found_in_db += 1
                    if telegram_id_from_panel:
                        logging.debug(f"Panel user with telegramId {telegram_id_from_panel} and UUID {panel_uuid} not found in local DB")
                        # Create new user if they have telegram_id
                        try:
                            user_data = {
                                "user_id": telegram_id_from_panel,
                                "username": None,  # Username will be updated when user interacts with bot
                                "first_name": None,  # Panel doesn't provide this info
                                "last_name": None,   # Panel doesn't provide this info
                                "language_code": "ru",  # Default language
                                "panel_user_uuid": panel_uuid,
                                "is_banned": False,
                                "referred_by_id": None
                            }
                            
                            new_user, was_created = await user_dal.create_user(session, user_data)
                            if was_created:
                                users_created += 1
                                logging.info(f"Created new user {telegram_id_from_panel} from panel sync with UUID {panel_uuid}")
                            
                            existing_user = new_user
                            
                        except Exception as e_create:
                            sync_errors.append(f"Error creating user {telegram_id_from_panel}: {str(e_create)}")
                            logging.error(f"Error creating user {telegram_id_from_panel}: {e_create}")
                            continue
                    else:
                        logging.debug(f"Panel user with UUID {panel_uuid} (no telegramId) not found in local DB - skipping")
                        continue

                # User found in local DB
                users_found_in_db += 1
                user_was_updated = False

                # Get the actual user_id for subscription operations
                actual_user_id = existing_user.user_id

                # Update panel UUID if different
                if existing_user.panel_user_uuid != panel_uuid:
                    existing_user.panel_user_uuid = panel_uuid
                    user_was_updated = True
                    users_uuid_updated += 1
                    logging.info(f"Updated panel UUID for user {actual_user_id}: {panel_uuid}")

                # Sync subscription data
                panel_expire_at_iso = panel_user_dict.get("expireAt")
                panel_status = panel_user_dict.get("status", "UNKNOWN")
                
                if panel_expire_at_iso:
                    try:
                        panel_expire_at = datetime.fromisoformat(
                            panel_expire_at_iso.replace("Z", "+00:00")
                        )
                        
                        # Prefer syncing by concrete subscription UUID (shortUuid/subscriptionUuid)
                        subscription_uuid_from_panel = (
                            panel_user_dict.get("subscriptionUuid")
                            or panel_user_dict.get("shortUuid")
                        )

                        if subscription_uuid_from_panel:
                            # Try to find subscription by its panel_subscription_uuid first
                            existing_sub_by_uuid = (
                                await subscription_dal.get_subscription_by_panel_subscription_uuid(
                                    session, subscription_uuid_from_panel
                                )
                            )

                            if existing_sub_by_uuid:
                                # Update existing subscription
                                await subscription_dal.update_subscription(
                                    session,
                                    existing_sub_by_uuid.subscription_id,
                                    {
                                        "user_id": actual_user_id,
                                        "panel_user_uuid": panel_uuid,
                                        "end_date": panel_expire_at,
                                        "is_active": panel_status == "ACTIVE",
                                        "status_from_panel": panel_status,
                                    },
                                )
                                subscriptions_synced_count += 1
                                subscriptions_updated += 1
                                user_was_updated = True
                                logging.info(
                                    f"Synced existing subscription {existing_sub_by_uuid.subscription_id} for user {actual_user_id}: expires {panel_expire_at}, status {panel_status}"
                                )
                            else:
                                # Create a new subscription
                                sub_payload = {
                                    "user_id": actual_user_id,
                                    "panel_user_uuid": panel_uuid,
                                    "panel_subscription_uuid": subscription_uuid_from_panel,
                                    "start_date": None,
                                    "end_date": panel_expire_at,
                                    "duration_months": None,
                                    "is_active": panel_status == "ACTIVE",
                                    "status_from_panel": panel_status,
                                    "traffic_limit_bytes": settings.user_traffic_limit_bytes,
                                }
                                created_sub = await subscription_dal.upsert_subscription(
                                    session, sub_payload
                                )
                                subscriptions_synced_count += 1
                                subscriptions_created += 1
                                user_was_updated = True
                                logging.info(
                                    f"Created subscription {created_sub.subscription_id} for user {actual_user_id}"
                                )
                        else:
                            # No subscription UUID from panel: only update existing subscription
                            active_sub = await subscription_dal.get_active_subscription_by_user_id(
                                session, actual_user_id, panel_uuid
                            )
                            if active_sub:
                                await subscription_dal.update_subscription(
                                    session,
                                    active_sub.subscription_id,
                                    {
                                        "end_date": panel_expire_at,
                                        "is_active": panel_status == "ACTIVE",
                                        "status_from_panel": panel_status,
                                    },
                                )
                                subscriptions_synced_count += 1
                                subscriptions_updated += 1
                                user_was_updated = True
                                logging.info(
                                    f"Updated active subscription {active_sub.subscription_id} for user {actual_user_id}"
                                )
                            
                    except Exception as e:
                        sync_errors.append(f"Error syncing subscription for user {actual_user_id}: {str(e)}")
                        logging.error(f"Error syncing subscription for user {actual_user_id}: {e}")

                if user_was_updated:
                    users_updated += 1
                            
            except Exception as e_user:
                sync_errors.append(f"Error processing panel user: {str(e_user)}")
                logging.error(f"Error processing panel user: {e_user}")

        # Prepare detailed sync statistics
        sync_stats = {
            "panel_records_checked": panel_records_checked,
            "users_without_telegram_id": users_without_telegram_id,
            "users_not_found_in_db": users_not_found_in_db,
            "users_found_in_db": users_found_in_db,
            "users_created": users_created,
            "users_uuid_updated": users_uuid_updated,
            "users_updated": users_updated,
            "subscriptions_synced_count": subscriptions_synced_count,
            "subscriptions_created": subscriptions_created,
            "subscriptions_updated": subscriptions_updated,
            "sync_errors": len(sync_errors),
        }

        # Create detailed statistics string
        _ = lambda key, **kwargs: i18n_instance.gettext("ru", key, **kwargs) if i18n_instance else key
        
        # Сначала формируем additional_stats
        additional_stats = ""
        if users_without_telegram_id > 0:
            additional_stats += _("admin_sync_no_telegram_id", default="\n⚠️ Записей без telegramId: {count}", count=users_without_telegram_id)
        if users_not_found_in_db > 0:
            additional_stats += _("admin_sync_not_found_in_db", default="\n❌ Не найдено в БД: {count}", count=users_not_found_in_db)
        if sync_errors:
            additional_stats += _("admin_sync_errors", default="\n🚫 Ошибок: {count}", count=len(sync_errors))
        
        # Теперь формируем основную строку с additional_stats
        details_text = _("admin_sync_details", default=(
            "📊 Статистика синхронизации:\n"
            "🔍 Проверено записей панели: {panel_records_checked}\n"
            "👥 Найдено пользователей в БД: {users_found_in_db}\n"
            "✨ Создано новых пользователей: {users_created}\n"
            "🔄 Пользователей обновлено: {users_updated}\n"
            "📋 Подписок синхронизировано: {subscriptions_synced_count}\n"
            "   ├── Создано новых: {subscriptions_created}\n"
            "   └── Обновлено существующих: {subscriptions_updated}{additional_stats}"
        ), **sync_stats, additional_stats=additional_stats)

        # Determine status
        if sync_errors:
            sync_status = "completed_with_errors"
        else:
            sync_status = "completed"

        # Update panel sync status
        await panel_sync_dal.update_panel_sync_status(
            session,
            sync_status,
            details_text,
            users_updated,
            subscriptions_synced_count,
        )
        await session.commit()

        return {
            "status": sync_status,
            "details": details_text,
            "users_synced": users_updated,
            "subs_synced": subscriptions_synced_count,
            "errors": sync_errors,
            **sync_stats,
        }

    except Exception as e:
        error_msg = f"Critical sync error: {str(e)}"
        logging.error(f"Critical sync error: {e}", exc_info=True)
        
        await panel_sync_dal.update_panel_sync_status(session, "failed", error_msg)
        await session.commit()
        
        return {
            "status": "failed",
            "details": error_msg,
            "users_synced": 0,
            "subs_synced": 0,
            "errors": [error_msg],
        }


@router.message(Command("sync"))
async def sync_command_handler(
    message_event: types.Message,
    bot: Bot,
    settings: Settings,
    i18n_data: dict,
    panel_service: PanelApiService,
    session: AsyncSession,
):
    """
    Handle /sync command - synchronize with panel data and send admin notification
    """
    current_lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    if not i18n:
        await message_event.answer("Language error.")
        return

    _ = lambda key, **kwargs: i18n.gettext(current_lang, key, **kwargs)

    # Send status message to user
    start_msg = await message_event.answer(
        _("sync_started_simple", default="🔄 Начинаю синхронизацию...")
    )

    # Perform sync
    sync_result = await perform_sync(panel_service, session, settings, i18n)

    # Prepare user notification based on result
    if sync_result["status"] == "completed":
        user_msg = _("sync_success_simple", default="✅ Синхронизация успешно завершена")
    elif sync_result["status"] == "completed_with_errors":
        error_count = len(sync_result.get("errors", []))
        user_msg = _(
            "sync_errors_simple",
            default="⚠️ Синхронизация завершена с ошибками ({errors_count} ошибок)",
            errors_count=error_count,
        )
    else:
        user_msg = _("sync_failed_simple", default="❌ Синхронизация завершилась с ошибкой")

    try:
        await start_msg.edit_text(user_msg)
    except Exception:
        await message_event.answer(user_msg)

    # Send detailed admin notification
    notification_service = NotificationService(bot, settings)
    admin_notification_msg = _(
        "log_panel_sync",
        default=(
            "{status_emoji} <b>Синхронизация с панелью</b>\n\n"
            "📊 Статус: <b>{status}</b>\n"
            "👥 Обработано пользователей: <b>{users_processed}</b>\n"
            "📋 Синхронизировано подписок: <b>{subs_synced}</b>\n"
            "🕐 Время: {timestamp}\n\n"
            "📝 Детали:\n{details}"
        ),
        status_emoji="✅" if sync_result["status"] == "completed" else ("⚠️" if sync_result["status"] == "completed_with_errors" else "❌"),
        status=sync_result["status"],
        users_processed=sync_result.get("users_synced", 0),
        subs_synced=sync_result.get("subs_synced", 0),
        timestamp=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        details=sync_result["details"],
    )

    await notification_service.send_admin_notification(
        admin_notification_msg, notify_events=False, parse_mode="HTML"
    )
