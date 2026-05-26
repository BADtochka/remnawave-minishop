# FreeKassa

FreeKassa подключается как отдельный платежный метод и обрабатывает входящие webhook-события через backend.

## Что настроить

- Включение провайдера: `FREEKASSA_ENABLED`.
- ID магазина, API/secret-ключи и настройки подписи.
- Trusted IP allowlist, если используется.
- Публичный webhook URL на `WEBHOOK_BASE_URL`.

## Где подробнее

- [Переменные FreeKassa](../configuration/env-vars.md#freekassa)
- [Платежи](../features/payments.md)
- [Логи и проверка](../troubleshooting/logs.md)
