@echo off
chcp 65001 >nul

REM Переходим в директорию проекта
cd /d "F:\docker\remnawave-tg-bot"

echo === Текущий статус ===
git status

echo.
echo === Текущая ветка ===
git branch --show-current

echo.
echo === Создаем новую ветку для обновлений ===
git checkout -b update-from-upstream-v2

echo.
echo === Добавляем все измененные файлы ===
git add .

echo.
echo === Коммитим изменения ===
git commit -m "feat: Update from upstream - major improvements

- Add support for multiple message types in broadcasts and direct messages
- Implement MessageContent class for unified media handling
- Add date_utils with proper calendar month calculations
- Enhance message queue with support for all Telegram media types
- Update user creation to be race-safe with PostgreSQL upsert
- Switch to webhook-only mode (disable polling)
- Improve subscription service with calendar months support
- Add comprehensive message filtering utilities
- Update localization files with new keys
- Refactor broadcast system for media content
- Enhance user management with media message support
- Update panel webhook service for auto-renewal improvements

Breaking changes:
- main_bot.py now requires webhook mode
- user_dal.create_user() now returns tuple (user, created)
- Subscription duration now uses calendar months instead of 30-day periods"

echo.
echo === Пушим в новую ветку ===
git push -u origin update-from-upstream-v2

echo.
echo === Готово! ===
echo Изменения запушены в ветку 'update-from-upstream-v2'
echo Теперь можно создать Pull Request на GitHub

pause
