@echo off
chcp 65001 >nul

REM Переходим в директорию проекта
cd /d "F:\docker\remnawave-tg-bot"

echo === Исправляем broadcast keyboard ===
git add bot/handlers/admin/broadcast.py

echo === Коммитим исправление ===
git commit -m "fix: Remove target parameter from get_broadcast_confirmation_keyboard calls

- Remove unsupported 'target' parameter from broadcast confirmation keyboard calls
- This parameter was added in new code but keyboard function doesn't support it yet
- Fixes TypeError: get_broadcast_confirmation_keyboard() got an unexpected keyword argument 'target'"

echo === Пушим исправление ===
git push origin update-from-upstream-v2

echo === Готово! ===
echo Исправление broadcast keyboard запушено

pause
