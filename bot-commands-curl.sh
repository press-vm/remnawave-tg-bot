#!/bin/bash

# TOKEN="8339838839:AAFjzi7yzQVoFFoBBG2yxxIeyPpHwvxFcFw"

TOKEN="8339838839:AAFjzi7yzQVoFFoBBG2yxxIeyPpHwvxFcFw"
API="https://api.telegram.org/bot$TOKEN"

# Проверка токена
if [[ -z "$TOKEN" || "$TOKEN" == "ТОКЕН_ТВОЕГО_БОТА" ]]; then
  echo "❌ Ошибка: нужно указать реальный токен бота в переменной TOKEN"
  exit 1
fi

echo "===> Удаляем все команды во всех scope..."

# Удалить default scope
curl -s -X POST "$API/deleteMyCommands"

# Удалить private chats
curl -s -X POST "$API/deleteMyCommands" \
  -H "Content-Type: application/json" \
  -d '{"scope": {"type": "all_private_chats"}}'

# Удалить group chats
curl -s -X POST "$API/deleteMyCommands" \
  -H "Content-Type: application/json" \
  -d '{"scope": {"type": "all_group_chats"}}'

# Удалить admin chats
curl -s -X POST "$API/deleteMyCommands" \
  -H "Content-Type: application/json" \
  -d '{"scope": {"type": "all_chat_administrators"}}'

echo
echo "===> Установка новых команд..."

# Установить default scope (только /start)
curl -s -X POST "$API/setMyCommands" \
  -H "Content-Type: application/json" \
  -d '{
    "commands": [
      {"command": "start", "description": "🛍️ Начать покупки"}
    ]
  }'

# Установить admin scope (/start и /admin)
curl -s -X POST "$API/setMyCommands" \
  -H "Content-Type: application/json" \
  -d '{
    "scope": {"type": "all_chat_administrators"},
    "commands": [
      {"command": "start", "description": "🛍️ Начать покупки"},
      {"command": "admin", "description": "👨‍💼 Админ панель"}
    ]
  }'

echo
echo "===> Проверка итоговых команд..."

echo "--- Default scope ---"
curl -s "$API/getMyCommands" | jq .

echo "--- All Private Chats ---"
curl -s -X POST "$API/getMyCommands" \
  -H "Content-Type: application/json" \
  -d '{"scope": {"type": "all_private_chats"}}' | jq .

echo "--- All Group Chats ---"
curl -s -X POST "$API/getMyCommands" \
  -H "Content-Type: application/json" \
  -d '{"scope": {"type": "all_group_chats"}}' | jq .

echo "--- All Chat Administrators ---"
curl -s -X POST "$API/getMyCommands" \
  -H "Content-Type: application/json" \
  -d '{"scope": {"type": "all_chat_administrators"}}' | jq .

echo "===> Готово!"
