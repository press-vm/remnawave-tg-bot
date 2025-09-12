# Скрипт обновления .env файла для v2.4.1
# Выполнить в директории проекта

echo "Обновление .env файла для v2.4.1..."

# Создаем резервную копию
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# Добавляем новые переменные для автопродлений
echo "" >> .env
echo "# Автопродление подписок (v2.4.0+)" >> .env
echo "YOOKASSA_AUTOPAYMENTS_ENABLED=False" >> .env
echo "REFERRAL_ONE_BONUS_PER_REFEREE=False" >> .env

echo "Обновление завершено! Проверьте настройки в .env файле."
echo "Важно: установите YOOKASSA_AUTOPAYMENTS_ENABLED=True для включения автопродлений"