# Wata

Wata подключается как отдельный провайдер с bearer token, платежными ссылками и опциональной проверкой подписи webhook.

## Что включить

- `WATA_ENABLED` - включает Wata для пользователей.
- `WATA_ADMIN_ONLY_ENABLED` - оставляет метод доступным только для админских сценариев, если используется вместо публичного включения.
- Presentation-ключи `PAYMENT_WATA_*` - подписи и иконки кнопки.

## Что настроить

1. Укажите `WATA_BASE_URL` и `WATA_API_TOKEN`.
2. Проверьте `WATA_RETURN_URL` и `WATA_FAILED_URL`.
3. Настройте `WATA_LINK_TTL_MINUTES`: минимум 15 минут, максимум 43200.
4. Если включаете проверку подписи, задайте `WATA_WEBHOOK_VERIFY_SIGNATURE` и при необходимости `WATA_PUBLIC_KEY`.
5. Для дополнительной защиты заполните `WATA_TRUSTED_IPS`.
6. Добавьте `wata` в `PAYMENT_METHODS_ORDER`.

## Проверка

- Создайте тестовый платеж и убедитесь, что ссылка открывается у пользователя.
- Проверьте входящий webhook: подпись и IP-allowlist должны соответствовать фактическому запросу Wata.
- Если платеж остается в pending, проверьте backend-логи вокруг webhook и статуса ссылки.

## Где подробнее

- [Переменные Wata](../configuration/env-vars.md#wata)
- [Настройка платежей](../features/payments.md)
- [Логи и диагностика](../troubleshooting/logs.md)
