@echo off
chcp 65001 >nul

echo === Очистка временных и ненужных файлов ===

REM Переходим в директорию проекта
cd /d "F:\docker\remnawave-tg-bot"

echo Удаляем временные bat-файлы...
if exist fix_all_errors.bat del fix_all_errors.bat
if exist fix_broadcast_keyboard.bat del fix_broadcast_keyboard.bat
if exist fix_imports.bat del fix_imports.bat
if exist fix_notification_service.bat del fix_notification_service.bat

echo Удаляем backup файлы...
if exist bot\handlers\admin\update_names.py.bak del bot\handlers\admin\update_names.py.bak

echo Удаляем временную документацию...
if exist MISSING_LOCALIZATION_KEYS.md del MISSING_LOCALIZATION_KEYS.md

echo === Обновляем .gitignore ===
echo.
echo # Временные batch-файлы >> .gitignore
echo *.bat >> .gitignore
echo.
echo # Backup файлы >> .gitignore  
echo *.bak >> .gitignore
echo *.backup >> .gitignore
echo.
echo # Временная документация >> .gitignore
echo MISSING_*.md >> .gitignore
echo TEMP_*.md >> .gitignore
echo DEBUG_*.md >> .gitignore

echo === Показываем статус Git ===
git status

echo.
echo === Готово! ===
echo Файлы очищены. Проверьте статус git и закоммитьте изменения.

pause
