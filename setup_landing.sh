#!/bin/bash

# Скрипт для настройки интеграции с лендингом PressVPN

echo "🚀 Настройка интеграции PressVPN Bot с лендингом..."

# Проверка наличия .env файла
if [ ! -f .env ]; then
    echo "📝 Создание .env файла из примера..."
    cp .env.example .env
    echo "✅ .env файл создан"
else
    echo "✅ .env файл уже существует"
fi

# Функция для обновления переменной в .env
update_env() {
    local key=$1
    local value=$2
    if grep -q "^${key}=" .env; then
        sed -i.bak "s|^${key}=.*|${key}=${value}|" .env
    else
        echo "${key}=${value}" >> .env
    fi
}

# Запрос данных у пользователя
read -p "📞 Введите ссылку на группу/канал поддержки Telegram (например: https://t.me/pressvpn_support): " support_link
read -p "🌐 Введите домен вашего сайта (например: pressvpn.shop): " domain

# Обновление переменных
echo "📝 Обновление настроек..."
update_env "SUPPORT_LINK" "$support_link"
update_env "SERVER_STATUS_URL" "https://${domain}#status"
update_env "TERMS_OF_SERVICE_URL" "https://${domain}#terms"

echo "✅ Настройки обновлены"

# Создание директорий для сайтов
echo ""
echo "📁 Проверка директорий для сайтов..."

# Основной сайт
if [ ! -d "/var/www/pressvpn.shop" ]; then
    echo "📁 Создание директории для основного сайта..."
    sudo mkdir -p /var/www/pressvpn.shop
    sudo mkdir -p /var/www/pressvpn.shop/terms
    echo "✅ Директории созданы"
else
    echo "✅ Директория основного сайта существует"
fi

# Статус сайт (если отдельный домен)
if [[ $use_status_domain == "y" || $use_status_domain == "Y" ]]; then
    if [ ! -d "/var/www/status.pressvpn.shop" ]; then
        echo "📁 Создание директории для сайта статуса..."
        sudo mkdir -p /var/www/status.pressvpn.shop
        echo "✅ Директория статуса создана"
    fi
fi

# Проверка docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "⚠️  docker-compose не установлен. Установите его для продолжения."
    exit 1
fi

echo ""
echo "⚠️  ВАЖНЫЕ НАПОМИНАНИЯ:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. YooKassa находится в ТЕСТОВОМ режиме!"
echo "   Замените ключи на боевые в .env:"
echo "   YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY"
echo ""
echo "2. Разместите HTML файлы:"
echo "   • Основной сайт: /var/www/pressvpn.shop/index.html"
echo "   • Условия: /var/www/pressvpn.shop/terms/index.html"
if [[ $use_status_domain == "y" || $use_status_domain == "Y" ]]; then
    echo "   • Статус: /var/www/status.pressvpn.shop/index.html"
fi
echo ""
echo "3. Настройте nginx для доменов"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Предложение перезапустить контейнеры
echo ""
read -p "🔄 Перезапустить контейнеры для применения настроек? (y/n): " restart
if [[ $restart == "y" || $restart == "Y" ]]; then
    echo "🔄 Перезапуск контейнеров..."
    docker-compose down
    docker-compose up -d
    echo "✅ Контейнеры перезапущены"
    
    echo ""
    echo "📊 Статус контейнеров:"
    docker-compose ps
fi

echo ""
echo "✨ Настройка завершена!"
echo ""
echo "📋 Проверьте следующее:"
echo "1. Основной сайт: https://${domain}"
echo "2. Условия использования: https://${domain}/terms"
if [[ $use_status_domain == "y" || $use_status_domain == "Y" ]]; then
    echo "3. Статус серверов: https://${status_domain}"
else
    echo "3. Статус серверов: https://${domain}#status"
fi
echo "4. Бот: @pressvpnshop_bot"
echo "5. Поддержка: ${support_link}"
echo ""
echo "📚 Подробная инструкция: docs/SETUP_GUIDE.md"
echo "🎨 HTML шаблоны находятся в артефактах выше"
