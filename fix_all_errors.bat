@echo off
chcp 65001 >nul

REM Переходим в директорию проекта
cd /d "F:\docker\remnawave-tg-bot"

echo === Добавляем все исправления ===
git add .

echo === Коммитим исправления ===
git commit -m "fix: Add missing files and fix import errors

- Fix indentation errors in start.py
- Add missing notification_service.py
- Create bot/app directory structure with __init__.py files
- Add missing localization keys to ru.json
- Create MISSING_LOCALIZATION_KEYS.md for reference
- Add error_occurred_processing_request to localization

These fixes resolve:
- IndentationError in start.py line 170-171
- Missing NotificationService import
- Missing localization keys for new features
- Missing directory structure for imports"

echo === Пушим исправления ===
git push origin update-from-upstream-v2

echo === Готово! ===
echo Все исправления запушены в ветку 'update-from-upstream-v2'

pause
