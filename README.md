# PressVPN - Telegram Bot для продажи VPN подписок

[![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)](https://github.com/press-vm/remnawave-tg-bot)
[![Docker](https://img.shields.io/badge/docker-ready-green.svg)](https://hub.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> **Упрощенная и безопасная версия** - убран функционал мониторинга серверов для фокуса на одной ноде

## 🚀 Быстрый старт

```bash
git clone https://github.com/press-vm/remnawave-tg-bot.git
cd remnawave-tg-bot
cp .env.example .env
# Отредактируйте .env файл с вашими настройками
docker compose up -d
```

## ✨ Возможности

- 🤖 **Telegram Bot** - автоматизированные продажи через бота
- 💳 **Платежи** - интеграция с YooKassa
- 📊 **Администрирование** - полноценная админ-панель
- 🎁 **Промокоды** - система скидок и промоакций  
- 👥 **Реферальная программа** - бонусы за приглашения
- 🔄 **Синхронизация** - автоматическая синхронизация с панелью Remnawave
- 🌍 **Мультиязычность** - поддержка русского и английского языков
- 📱 **Пробный период** - бесплатные тестовые подписки

## 🏗️ Архитектура

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Telegram Bot  │────│   PostgreSQL     │────│   Remnawave     │
│    (Python)     │    │    Database      │    │     Panel       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                       │
         └────────────────────────┼───────────────────────┘
                                  │
                    ┌─────────────────┐
                    │   Landing Page  │
                    │     (Nginx)     │
                    └─────────────────┘
```

## ⚙️ Установка и настройка

### Требования
- Docker и Docker Compose
- Домен с SSL сертификатом (для webhook)
- Telegram Bot Token
- YooKassa аккаунт для приема платежей

### 1. Клонирование репозитория
```bash
git clone https://github.com/press-vm/remnawave-tg-bot.git
cd remnawave-tg-bot
```

### 2. Настройка окружения
```bash
cp .env.example .env
nano .env
```

**Основные настройки в .env:**
```bash
# Telegram
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=your_telegram_user_id

# База данных
POSTGRES_PASSWORD=secure_password_here

# Webhook
WEBHOOK_BASE_URL=https://your-domain.com

# YooKassa
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key

# Remnawave API
PANEL_API_URL=http://remnawave:3000/api
PANEL_API_KEY=your_jwt_token_here
```

### 3. Запуск проекта
```bash
# Создание сети Docker
docker network create remnawave-network

# Запуск сервисов
docker compose up -d

# Проверка логов
docker compose logs -f
```

### 4. Безопасность и очистка

Запустите скрипт безопасности для удаления лишних файлов и настройки защиты:

```bash
chmod +x security_cleanup.sh
sudo ./security_cleanup.sh
```

Этот скрипт:
- ✅ Создает резервные копии
- ✅ Удаляет временные файлы
- ✅ Настраивает права доступа
- ✅ Проверяет безопасность конфигурации
- ✅ Настраивает мониторинг ресурсов
- ✅ Конфигурирует автоматические бэкапы

## 🔒 Безопасность

### Важные меры безопасности:

1. **Файл .env** должен иметь права доступа 600:
   ```bash
   chmod 600 .env
   ```

2. **Не добавляйте .env в git:**
   ```bash
   echo ".env" >> .gitignore
   ```

3. **Регулярно обновляйте JWT токены** для API

4. **Используйте сильные пароли** для базы данных

5. **Настройте fail2ban** для защиты от брутфорса

6. **Включите UFW firewall:**
   ```bash
   ufw enable
   ufw allow ssh
   ufw allow 80
   ufw allow 443
   ```

## 📊 Мониторинг

После запуска `security_cleanup.sh` автоматически настраивается:

- **Мониторинг ресурсов** каждые 5 минут
- **Ежедневные бэкапы** в 02:00
- **Логирование в** `/var/log/remnawave_monitoring.log`

### Просмотр логов мониторинга:
```bash
tail -f /var/log/remnawave_monitoring.log
```

### Просмотр бэкапов:
```bash
ls -la /opt/backups/
```

## 🛠️ Управление

### Полезные команды Docker:
```bash
# Перезапуск всех сервисов
docker compose restart

# Просмотр логов конкретного сервиса
docker compose logs -f remnawave-tg-shop

# Вход в контейнер бота
docker compose exec remnawave-tg-shop bash

# Обновление до новой версии
docker compose pull
docker compose up -d
```

### Команды администратора в боте:
- `/admin` - главное меню администратора
- `/stats` - статистика системы
- `/broadcast` - массовая рассылка
- `/sync` - принудительная синхронизация с панелью

## 📋 Настройка тарифов

Тарифы настраиваются в .env файле:

```bash
# 1 месяц
1_MONTH_ENABLED=true
RUB_PRICE_1_MONTH=199

# 3 месяца  
3_MONTHS_ENABLED=true
RUB_PRICE_3_MONTHS=499

# 6 месяцев
6_MONTHS_ENABLED=true
RUB_PRICE_6_MONTHS=899

# 12 месяцев
12_MONTHS_ENABLED=true
RUB_PRICE_12_MONTHS=1599
```

## 🎯 Что убрано в этой версии

Для упрощения и фокуса на одной ноде были убраны:

- ❌ **Мониторинг статуса серверов** - больше не нужен для одной ноды
- ❌ **CryptoPay интеграция** - упрощение платежных систем
- ❌ **Tribute платежи** - фокус на YooKassa
- ❌ **Telegram Stars** - пока не активно используется
- ❌ **Множественные админы** - один главный администратор

## 🐛 Устранение неисправностей

### Проблемы с webhook:
```bash
# Проверка webhook статуса
curl -X GET "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# Удаление webhook (для переключения на polling)
curl -X GET "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
```

### Проблемы с базой данных:
```bash
# Подключение к БД
docker compose exec remnawave-tg-shop-db psql -U postgres -d pressvpn_shop

# Проверка таблиц
\dt

# Выход
\q
```

### Проблемы с API панели:
```bash
# Тест подключения к API
docker compose exec remnawave-tg-shop python -c "
import requests
headers = {'Authorization': 'Bearer YOUR_JWT_TOKEN'}
response = requests.get('http://remnawave:3000/api/users', headers=headers)
print(response.status_code, response.text)
"
```

## 📝 Логи

Основные файлы логов:
```bash
# Логи бота
docker compose logs remnawave-tg-shop

# Логи базы данных  
docker compose logs remnawave-tg-shop-db

# Логи мониторинга
tail -f /var/log/remnawave_monitoring.log

# Логи бэкапов
tail -f /var/log/remnawave_backup.log
```

## 📞 Поддержка

- **Telegram:** [@pressvpn_support](https://t.me/pressvpn_support)
- **Email:** support@pressvpn.shop
- **GitHub Issues:** [Создать issue](https://github.com/press-vm/remnawave-tg-bot/issues)

## 📄 Лицензия

MIT License. См. файл [LICENSE](LICENSE) для подробностей.

---

> ⭐ Если проект оказался полезным, поставьте звезду на GitHub!

## 🚀 Что дальше?

После успешного запуска рекомендуется:

1. **Настроить SSL сертификаты** для всех доменов
2. **Протестировать платежи** в тестовом режиме
3. **Создать промокоды** для первых клиентов  
4. **Настроить уведомления** в Telegram канале
5. **Запустить рекламную кампанию** для привлечения пользователей

**Удачного запуска! 🎉**