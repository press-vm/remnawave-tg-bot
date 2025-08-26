#!/bin/bash

# Переходим в директорию проекта
cd "F:/docker/remnawave-tg-bot"

echo "=== Исправляем main_bot.py ==="
git add bot/main_bot.py

echo "=== Коммитим исправление ==="
git commit -m "fix: Remove missing imports in main_bot.py

- Remove ProfileSyncMiddleware import (module doesn't exist)
- Remove build_dispatcher and build_core_services imports  
- Remove build_and_start_web_app import
- Restore manual service initialization in run_bot function
- Fix web server setup for webhook mode"

echo "=== Пушим исправление ==="
git push origin update-from-upstream-v2

echo "=== Готово! ==="
echo "Исправления запушены в ветку 'update-from-upstream-v2'"
