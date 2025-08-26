@echo off
chcp 65001 >nul

REM Переходим в директорию проекта
cd /d "F:\docker\remnawave-tg-bot"

echo === Исправляем NotificationService ===
git add bot/services/notification_service.py locales/ru.json

echo === Коммитим исправление ===
git commit -m "fix: Add missing notification methods to NotificationService

- Add notify_payment_received method for payment notifications
- Add notify_trial_activation method for trial activation notifications  
- Add notify_promo_activation method for promo code activation notifications
- Add corresponding localization keys to ru.json
- Fixes AttributeError: 'NotificationService' object has no attribute errors

These methods were missing and causing errors when:
- Payment webhook received successful payment
- User activated trial subscription
- User activated promo code"

echo === Пушим исправление ===
git push origin update-from-upstream-v2

echo === Готово! ===
echo Исправление NotificationService запушено

pause
