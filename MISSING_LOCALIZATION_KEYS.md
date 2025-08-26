# Дополнительные локализационные ключи

В файлы ru.json и en.json нужно добавить следующие ключи в конец перед закрывающей скобкой:

## Для ru.json:
```json
  "admin_broadcast_invalid_html": "❌ Некорректный HTML в сообщении. Пожалуйста, отправьте корректный HTML (поддерживаются теги Telegram) или уберите теги.\nОшибка: {error}",
  "admin_direct_empty_message": "❌ Пустое сообщение. Отправьте текст или медиа.",
  "admin_new_user_notification": "🎉 Новый пользователь зарегистрирован!\n\n{user_info}",
  "admin_new_subscription_notification": "💳 Новая подписка!\n\n🆔 Пользователь: {user_id}\n📅 Длительность: {duration} мес.\n💰 Сумма: {amount}\n📦 Тип: {type}",
  "config_link_not_available": "Ссылка для подключения недоступна",
  "error_occurred_processing_request": "При обработке вашего запроса произошла ошибка. Попробуйте позже."
```

## Для en.json:
```json
  "admin_broadcast_invalid_html": "❌ Invalid HTML in message. Please send correct HTML (Telegram tags supported) or remove tags.\nError: {error}",
  "admin_direct_empty_message": "❌ Empty message. Send text or media.",
  "admin_new_user_notification": "🎉 New user registered!\n\n{user_info}",
  "admin_new_subscription_notification": "💳 New subscription!\n\n🆔 User: {user_id}\n📅 Duration: {duration} mo.\n💰 Amount: {amount}\n📦 Type: {type}",
  "config_link_not_available": "Connection link unavailable",
  "error_occurred_processing_request": "An error occurred while processing your request. Please try again later."
```

Эти ключи уже добавлены в ru.json, но в en.json могут отсутствовать.
