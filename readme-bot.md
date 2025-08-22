# Remnawave Telegram Shop Bot

Telegram бот для управления подписками VPN-сервиса с интеграцией в панель Remnawave.

## Возможности

### Для пользователей
- **Покупка подписок** - различные тарифные планы на 1, 3, 6, 12 месяцев
- **Пробный период** - бесплатный триал для новых пользователей
- **Реферальная программа** - бонусные дни за приглашение друзей
- **Промокоды** - активация промокодов для получения бонусных дней
- **Множественные платежные системы**:
  - YooKassa (банковские карты)
  - CryptoBot (криптовалюта)
  - Telegram Stars
  - Tribute
- **Мультиязычность** - поддержка русского и английского языков
- **Уведомления** - напоминания об истечении подписки

### Для администраторов
- **Статистика** - детальная информация о пользователях и платежах
- **Управление пользователями** - поиск, просмотр, блокировка
- **Промокоды** - создание и управление промокодами
- **Рассылка** - массовая отправка сообщений пользователям
- **Синхронизация** - автоматическая синхронизация с панелью Remnawave
- **Логирование** - детальные логи всех действий
- **Экспорт данных** - выгрузка платежей и логов в CSV

## Требования

- Docker и Docker Compose
- PostgreSQL 17
- Python 3.11+
- Remnawave панель с API доступом
- Домен с SSL сертификатом (для webhook)

## Быстрый старт

### 1. Клонирование репозитория

```bash
git clone https://github.com/press-vm/remnawave-tg-bot.git
cd remnawave-tg-bot
```

### 2. Настройка переменных окружения

Создайте файл `.env` на основе примера:

```bash
cp .env.example .env
```

Основные переменные:
```env
# Telegram
BOT_TOKEN=your_bot_token
ADMIN_IDS=123456789,987654321
DEFAULT_LANGUAGE=ru

# База данных
POSTGRES_DB=pressvpn_shop
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_password

# Remnawave API
REMNAWAVE_API_URL=https://your-panel.com/api
REMNAWAVE_API_KEY=your_api_key

# Webhook
WEBHOOK_BASE_URL=https://bot.yourdomain.com
WEB_SERVER_HOST=0.0.0.0
WEB_SERVER_PORT=8080

# Платежные системы
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key
```

### 3. Запуск бота

```bash
docker compose up -d
```

### 4. Проверка работы

```bash
docker compose logs -f
```

## Структура проекта

```
.
├── bot/                    # Основной код бота
│   ├── handlers/          # Обработчики команд и событий
│   ├── keyboards/         # Клавиатуры
│   ├── middlewares/       # Middleware компоненты
│   ├── services/          # Сервисы (платежи, API и т.д.)
│   └── utils/            # Утилиты
├── db/                    # База данных
│   ├── dal/              # Data Access Layer
│   └── models.py         # SQLAlchemy модели
├── locales/              # Файлы локализации
├── docker-compose.yml    # Docker конфигурация
└── requirements.txt      # Python зависимости
```

## Настройка webhook

Для работы webhook необходим домен с SSL. Настройте reverse proxy (nginx/traefik):

```nginx
server {
    server_name bot.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    listen 443 ssl;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
}
```

## Команды бота

- `/start` - Главное меню
- `/admin` - Админ панель (только для администраторов)

## Обновление

```bash
git pull
docker compose build --no-cache
docker compose up -d
```

## Лицензия

MIT

## Поддержка

По вопросам обращайтесь в Issues или Telegram: @your_support