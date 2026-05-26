# SeverPay

SeverPay подключается как отдельный платежный метод с собственным MID, token и сроком жизни платежной ссылки.

## Что включить

- `SEVERPAY_ENABLED` - показывает SeverPay среди доступных методов оплаты.
- Presentation-ключи `PAYMENT_SEVERPAY_*` - подписи и иконки кнопки в Mini App и Telegram.

## Что настроить

1. Укажите `SEVERPAY_BASE_URL`.
2. Заполните `SEVERPAY_MID` и `SEVERPAY_TOKEN`.
3. Настройте `SEVERPAY_RETURN_URL`.
4. При необходимости задайте `SEVERPAY_LIFETIME_MINUTES`.
5. Добавьте `severpay` в `PAYMENT_METHODS_ORDER`.

## Проверка

- Создайте тестовый платеж и проверьте, что пользователь получает платежную ссылку.
- Убедитесь, что ссылка живет ожидаемое время, если задан `SEVERPAY_LIFETIME_MINUTES`.
- После оплаты проверьте статус платежа в backend-логах и в админке.

## Где подробнее

- [Переменные SeverPay](../configuration/env-vars.md#severpay)
- [Настройка платежей](../features/payments.md)
- [Логи и диагностика](../troubleshooting/logs.md)
