#!/bin/bash

# Токен вашего бота
BOT_TOKEN="8339838839:AAFjzi7yzQVoFFoBBG2yxxIeyPpHwvxFcFw"

# 1. Удаляем все старые команды
echo "🗑️ Удаляем старые команды..."
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/deleteMyCommands"
echo ""

# 2. Устанавливаем новые команды для shop бота
echo "✨ Устанавливаем новые команды..."
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setMyCommands" \
  -H "Content-Type: application/json" \
  -d '{
    "commands": [
      {
        "command": "start",
        "description": "🛍️ Начать покупки"
      },
      {
        "command": "admin",
        "description": "👨‍💼 Админ панель"
      }
    ]
  }'
echo ""

# 3. Проверяем результат
echo "📋 Текущие команды:"
curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getMyCommands" | python3 -m json.tool