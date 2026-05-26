# Heleket

Heleket используется для crypto-инвойсов с отдельными merchant ID, payment API key, валютой инвойса и настройками webhook-проверки.

## Что включить

- `HELEKET_ENABLED` - включает Heleket среди доступных методов.
- Presentation-ключи `PAYMENT_HELEKET_*` - подписи и иконки кнопки.

## Что настроить

1. Укажите `HELEKET_BASE_URL`, `HELEKET_MERCHANT_ID` и `HELEKET_API_KEY`.
2. Настройте `HELEKET_CURRENCY`.
3. При необходимости задайте `HELEKET_TO_CURRENCY` и `HELEKET_NETWORK`.
4. Проверьте `HELEKET_RETURN_URL` и `HELEKET_SUCCESS_URL`.
5. Настройте `HELEKET_LIFETIME_SECONDS`: допустимый диапазон 300..43200.
6. Если включаете проверку webhook, задайте `HELEKET_VERIFY_WEBHOOK_SIGNATURE`.
7. Для IP-фильтрации заполните `HELEKET_TRUSTED_IPS`.
8. Добавьте `heleket` в `PAYMENT_METHODS_ORDER`.

## Проверка

- Создайте тестовый инвойс и убедитесь, что пользователь получает корректную ссылку.
- Проверьте, что сеть и валюта соответствуют настройкам в кабинете Heleket.
- Если webhook отклоняется, проверьте подпись, allowlist и фактический payload в backend-логах.

## Где подробнее

- [Переменные Heleket](../configuration/env-vars.md#heleket)
- [Настройка платежей](../features/payments.md)
- [Логи и диагностика](../troubleshooting/logs.md)
