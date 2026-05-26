# Platega

Platega подключается как отдельный платежный провайдер, но внутри Minishop может дать несколько кнопок: основную legacy-кнопку, СБП/карту и крипто-кнопку. Общие merchant-параметры задаются один раз, а method ID и подписи кнопок настраиваются отдельно.

## Что включить

- `PLATEGA_ENABLED` - общий флаг провайдера.
- `PLATEGA_SBP_ENABLED` - отдельная кнопка СБП/карта.
- `PLATEGA_CRYPTO_ENABLED` - отдельная crypto-кнопка Platega.
- `PLATEGA_PAYMENT_METHOD` - legacy/fallback method ID для старых callback и старых установок.

## Что настроить

1. Укажите `PLATEGA_BASE_URL`, `PLATEGA_MERCHANT_ID` и `PLATEGA_SECRET`.
2. Заполните `PLATEGA_SBP_METHOD` и/или `PLATEGA_CRYPTO_METHOD`, если используете отдельные кнопки.
3. Проверьте `PLATEGA_RETURN_URL` и `PLATEGA_FAILED_URL`.
4. Настройте тексты и иконки кнопок через `PAYMENT_PLATEGA_SBP_*` и `PAYMENT_PLATEGA_CRYPTO_*`.
5. Добавьте нужные методы в `PAYMENT_METHODS_ORDER`.

## Проверка

- После сохранения настроек откройте Mini App и убедитесь, что видны только включенные Platega-кнопки.
- Выполните тестовую оплату для каждой включенной кнопки: СБП/карта и crypto используют разные method ID.
- При ошибках проверьте backend-логи и ответ провайдера при создании платежной ссылки.

## Где подробнее

- [Переменные Platega](../configuration/env-vars.md#platega)
- [Настройка платежей](../features/payments.md)
- [Логи и диагностика](../troubleshooting/logs.md)
