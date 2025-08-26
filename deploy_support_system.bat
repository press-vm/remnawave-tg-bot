@echo off
chcp 65001 >nul

echo === Добавляем систему поддержки в основной бот ===

cd /d "F:\docker\remnawave-tg-bot"

echo Добавляем все изменения в git...
git add bot/handlers/user/start.py
git add bot/handlers/user/support.py
git add bot/handlers/user/__init__.py
git add bot/states/user_states.py
git add locales/ru.json

echo Коммитим изменения...
git commit -m "feat: Add integrated support system to main bot

- Add support dialog handler in start.py for 'main_action:support'
- Create support.py with full dialog management system  
- Add UserSupportStates for FSM support dialog states
- Include support router in user router aggregate
- Add support localization keys to ru.json

Features:
- Users can start support dialog from main menu
- Messages forwarded to admins with context
- Admins reply via /reply USER_ID text command
- Dialog state management with start/end tracking
- Media message support (photos, documents, etc.)
- Admin commands: /support_dialogs, /support_stats
- Automatic notifications for dialog start/end

Usage:
- User: Press 'Поддержка' → 'Начать диалог' → write message  
- Admin: Use '/reply USER_ID your_response' to answer
- Admin: Use '/support_dialogs' to see active dialogs"

echo Пушим в main...
git push origin main

echo === Готово! ===
echo Система поддержки добавлена в основной бот.
echo.
echo На сервере выполните:
echo   docker compose down && docker compose up -d
echo   docker compose logs -f

pause
