# CryptoPay

CryptoPay используется для криптовалютных платежей через отдельный токен и сеть Crypto Bot API.

## Что включить

- `CRYPTOPAY_ENABLED` - включает CryptoPay среди доступных методов.
- Presentation-ключи `PAYMENT_CRYPTOPAY_*` - подписи и иконки кнопки в Mini App и Telegram.

## Что настроить

1. Укажите `CRYPTOPAY_TOKEN`.
2. Выберите `CRYPTOPAY_NETWORK`: `mainnet` или `testnet`.
3. Задайте `CRYPTOPAY_CURRENCY_TYPE`: `fiat` или `crypto`.
4. Проверьте `CRYPTOPAY_ASSET`, например `RUB`, `USDT` или `BTC`.
5. Добавьте `cryptopay` в `PAYMENT_METHODS_ORDER`.

## Проверка

- Для тестов используйте соответствующую сеть: testnet-токен не должен попадать в mainnet-настройки.
- Выполните тестовый платеж и проверьте, что статус закрывается после callback от провайдера.
- Если сумма или asset выглядят неверно, проверьте сочетание `CRYPTOPAY_CURRENCY_TYPE` и `CRYPTOPAY_ASSET`.

## Где подробнее

- [Переменные CryptoPay](../configuration/env-vars.md#cryptopay)
- [Настройка платежей](../features/payments.md)
- [Логи и диагностика](../troubleshooting/logs.md)
