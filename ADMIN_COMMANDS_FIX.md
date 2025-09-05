# Исправление админских команд

## Проблема
Некоторые команды администратора не работали:
- `/stats` - не работала
- `/check_subs` - не работала
- `/sync_admin` - не работала
- `/update_names` - не работала
- `/revenue_stats` - не работала
- `/users_stats` - не работала

При этом работали:
- `/support_stats` ✅
- `/sync` ✅
- `/support_dialogs` ✅

## Решение

### 1. Добавлены команды в statistics.py
- `@router.message(Command("stats"))` - общая статистика
- `@router.message(Command("users_stats"))` - статистика пользователей
- `@router.message(Command("revenue_stats"))` - финансовая статистика

### 2. Добавлены команды в sync_admin.py
- `@router.message(Command("sync_admin"))` - псевдоним для команды /sync

### 3. Добавлены команды в update_names.py
- `@router.message(Command("update_names"))` - псевдоним для /update_all_names
- `@router.message(Command("check_subs"))` - проверка подписок

### 4. Добавлены недостающие методы в subscription_dal.py
- `get_active_subscriptions_count()` - количество активных подписок
- `get_expired_subscriptions_count()` - количество истекших подписок
- `get_trial_subscriptions_count()` - количество пробных подписок (по provider='trial')

### 5. Подключен роутер update_names к админскому агрегатору
В файле `bot/handlers/admin/__init__.py` добавлена строка:
```python
admin_router_aggregate.include_router(update_names.router)
```

## Результат
Теперь все команды должны работать:
- `/stats` ✅ - показывает полную статистику (использует существующий обработчик)
- `/users_stats` ✅ - показывает только статистику пользователей
- `/revenue_stats` ✅ - показывает только финансовую статистику  
- `/sync_admin` ✅ - псевдоним для `/sync`
- `/update_names` ✅ - псевдоним для `/update_all_names`
- `/check_subs` ✅ - показывает статистику подписок

## Необходимый перезапуск
После внесения изменений необходимо перезапустить бота для применения новых обработчиков команд.
