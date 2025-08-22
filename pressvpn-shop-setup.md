# 🚀 Настройка PressVPN Shop Bot

## 📋 Что умеет этот бот:

### Для пользователей:
- 🌐 Мультиязычность (русский/английский)
- 💳 Автоматическая продажа подписок
- 🎁 Пробный период (3 дня бесплатно)
- 🎟️ Промокоды со скидками
- 👥 Реферальная программа с бонусами
- 💰 Оплата через ЮKassa, CryptoBot, Tribute, Telegram Stars
- 📊 Просмотр статуса подписки
- 🔗 Автоматическое получение ссылки для подключения

### Для администраторов:
- 📈 Полная статистика по продажам и пользователям
- 📢 Массовые рассылки
- 🎫 Управление промокодами
- 🚫 Блокировка пользователей
- 🔄 Синхронизация с Remnawave
- 📝 Логирование всех действий

## 🛠️ Пошаговая установка:

### Шаг 1: Получение API ключа от Remnawave

```bash
# Войдите в панель Remnawave
cd /opt/remnawave
docker compose exec remnawave sh

# Внутри контейнера выполните:
npm run cli api-tokens:create -- --name "TelegramShopBot"

# Скопируйте полученный токен
```

### Шаг 2: Создание директории и файлов

```bash
# Создаем директорию для бота
mkdir -p /opt/remnawave-tg-shop
cd /opt/remnawave-tg-shop

# Копируем файлы конфигурации
# Скопируйте содержимое .env из артефакта выше
nano .env

# Скопируйте docker-compose.yml
nano docker-compose.yml
```

### Шаг 3: Настройка .env файла

**Обязательные настройки:**

1. **API ключ Remnawave:**
   ```
   PANEL_API_KEY=ваш_токен_из_шага_1
   ```

2. **ID администратора Telegram:**
   - Узнайте свой ID через @userinfobot
   - Добавьте в `ADMIN_IDS=ваш_id`

3. **Настройка платежей (выберите один или несколько):**

   **Вариант А: ЮKassa (рекомендуется)**
   - Зарегистрируйтесь на https://yookassa.ru
   - Получите Shop ID и Secret Key
   - Заполните:
     ```
     YOOKASSA_ENABLED=true
     YOOKASSA_SHOP_ID=ваш_shop_id
     YOOKASSA_SECRET_KEY=ваш_secret_key
     ```

   **Вариант Б: Ручная проверка платежей**
   - Оставьте `YOOKASSA_ENABLED=false`
   - Бот будет работать с ручным подтверждением

### Шаг 4: Запуск бота

```bash
# Запускаем контейнеры
docker compose up -d

# Проверяем логи
docker compose logs -f remnawave-tg-shop
```

### Шаг 5: Настройка webhook в ЮKassa (если используется)

1. Войдите в личный кабинет ЮKassa
2. Перейдите в Настройки → HTTP-уведомления
3. Добавьте URL: `https://bot.pressvpn.shop/webhook/yookassa`
4. Выберите события: payment.succeeded, payment.canceled

### Шаг 6: Первый запуск

1. Откройте бота в Telegram: @ваш_бот
2. Нажмите /start
3. Перейдите в админ-панель через команду /admin
4. Создайте первый промокод для тестирования

## 🔧 Команды администратора:

- `/admin` - главное меню администратора
- `/stats` - статистика системы
- `/users` - управление пользователями
- `/promo` - управление промокодами
- `/broadcast` - массовая рассылка
- `/sync` - синхронизация с Remnawave

## 📊 Мониторинг:

### Просмотр логов:
```bash
# Логи бота
docker compose logs -f remnawave-tg-shop

# Логи базы данных
docker compose logs -f remnawave-tg-shop-db
```

### Проверка статуса:
```bash
# Статус контейнеров
docker compose ps

# Использование ресурсов
docker stats remnawave-tg-shop remnawave-tg-shop-db
```

## 🆘 Решение проблем:

### Бот не отвечает:
```bash
# Перезапуск бота
docker compose restart remnawave-tg-shop

# Проверка логов на ошибки
docker compose logs --tail=50 remnawave-tg-shop
```

### Ошибка подключения к Remnawave:
- Проверьте `PANEL_API_KEY` в .env
- Убедитесь, что контейнеры в одной сети:
  ```bash
  docker network ls
  docker network inspect remnawave-network
  ```

### Не работают платежи:
- Проверьте настройки ЮKassa в .env
- Убедитесь, что webhook URL доступен извне
- Проверьте логи на наличие ошибок от платежной системы

## 🎯 Тестирование:

1. **Тест создания пользователя:**
   - Напишите боту /start
   - Выберите язык
   - Нажмите "Получить пробный период"

2. **Тест оплаты:**
   - Выберите тариф
   - Оплатите (можно использовать тестовые карты ЮKassa)
   - Проверьте автоматическое создание подписки

3. **Тест реферальной системы:**
   - Получите реферальную ссылку
   - Зарегистрируйте нового пользователя по ней
   - Проверьте начисление бонусов

## 📈 Расширенные возможности:

### Кастомизация сообщений:
Отредактируйте файлы локализации:
```bash
nano locales/ru.json
nano locales/en.json
```

### Добавление новых тарифов:
В .env добавьте новые переменные:
```bash
24_MONTHS_ENABLED=true
RUB_PRICE_24_MONTHS=2999
```

### Интеграция с другими платежными системами:
- CryptoBot для криптовалют
- Tribute для рекуррентных платежей
- Telegram Stars для внутренней валюты

## 📝 Полезные команды:

```bash
# Бэкап базы данных
docker compose exec remnawave-tg-shop-db pg_dump -U postgres pressvpn_shop > backup.sql

# Восстановление из бэкапа
docker compose exec -T remnawave-tg-shop-db psql -U postgres pressvpn_shop < backup.sql

# Обновление бота
docker compose pull
docker compose up -d

# Полный рестарт
docker compose down
docker compose up -d
```

## 🔗 Интеграция с существующей инфраструктурой:

Бот автоматически интегрируется с:
- **Remnawave Panel** - через API для управления пользователями
- **Traefik** - для SSL сертификатов и роутинга
- **PostgreSQL** - отдельная БД для хранения данных бота
- **Docker Network** - общая сеть `remnawave-network`

## ✅ Готово!

После выполнения всех шагов у вас будет полностью автоматизированная система продажи VPN подписок через Telegram!