# Платежи

Платежные методы включаются через `.env` или админ-панель, если параметр добавлен в allowlist настроек. В Mini App и Telegram-сценариях включённые методы отображаются как кнопки оплаты.

## Общий порядок настройки

1. Включите нужный провайдер.
2. Заполните публичные параметры, секреты и URL возврата.
3. Настройте webhook URL у провайдера, если он используется.
4. Проверьте порядок методов в `PAYMENT_METHODS_ORDER`.
5. Проверьте подписи и иконки кнопок оплаты.
6. Выполните тестовый платеж.
7. Проверьте логи `backend`.

> [!TIP]
> URL вебхука отображается вверху раздела каждого провайдера в админ-панели.

## Общие ссылки

- [Справочник `.env`](../configuration/env-vars.md) — все ключи платежных провайдеров.
- [Админ-панель](admin-panel.md) — UI-настройки платежей.
- [Тарифы](tariffs.md) — цены, Telegram Stars и сценарии покупки.
- [Логи](../troubleshooting/logs.md) — проверка webhook и создания платежных ссылок.

## YooKassa

YooKassa используется для рублевых оплат. Провайдер также может участвовать в сценариях автопродления period-подписок.

### Настройка

1. Включите `YOOKASSA_ENABLED`.
2. Заполните `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`, `YOOKASSA_RETURN_URL`.
3. Скопируйте URL вебхука из админ-панели и укажите его в кабинете YooKassa.

### Справочник

- [YooKassa](../configuration/env-vars.md#yookassa)

## FreeKassa

FreeKassa подключается как отдельный платежный метод. Входящие webhook-события обрабатываются через `backend`.

### Настройка

1. Включите `FREEKASSA_ENABLED`.
2. Заполните `FREEKASSA_MERCHANT_ID`, `FREEKASSA_FIRST_SECRET`, `FREEKASSA_SECOND_SECRET`, `FREEKASSA_API_KEY`.
3. Проверьте настройки подписи.
4. Скопируйте URL вебхука из админ-панели и укажите его в кабинете FreeKassa.
5. При необходимости заполните список доверенных IP.

### Справочник

- [FreeKassa](../configuration/env-vars.md#freekassa)

## Platega

Platega подключается как отдельный платежный провайдер. Внутри Minishop он может создавать несколько кнопок: основную legacy-кнопку, СБП/карту и crypto-кнопку.

### Настройка

1. Включите `PLATEGA_ENABLED`.
2. Укажите `PLATEGA_MERCHANT_ID` и `PLATEGA_SECRET`.
3. Скопируйте URL вебхука из админ-панели и укажите его в кабинете Platega.
4. Проверьте `PLATEGA_RETURN_URL` и `PLATEGA_FAILED_URL`.
5. При необходимости укажите `PLATEGA_PAYMENT_METHOD`.

### Справочник

- [Platega](../configuration/env-vars.md#platega)

## SeverPay

SeverPay подключается как отдельный платежный метод с собственным MID, token и сроком жизни платежной ссылки.

### Настройка

1. Включите `SEVERPAY_ENABLED`.
2. Укажите `SEVERPAY_MID`, `SEVERPAY_TOKEN`, `SEVERPAY_BASE_URL`
3. Скопируйте URL вебхука из админ-панели и укажите его в кабинете SeverPay.
4. При необходимости задайте `SEVERPAY_LIFETIME_MINUTES`.

### Справочник

- [SeverPay](../configuration/env-vars.md#severpay)

## Wata

Wata подключается как отдельный провайдер с bearer token, платежными ссылками и опциональной проверкой подписи webhook.

### Настройка

1. Включите `WATA_ENABLED`.
2. Укажите `WATA_BASE_URL` и `WATA_API_TOKEN`.
3. Проверьте `WATA_RETURN_URL` и `WATA_FAILED_URL`.
4. Настройте `WATA_LINK_TTL_MINUTES`.
5. Скопируйте URL вебхука из админ-панели и укажите его в кабинете Wata.
6. При необходимости включите `WATA_WEBHOOK_VERIFY_SIGNATURE`.
7. Если используется проверка подписи, задайте `WATA_PUBLIC_KEY`.
8. Для IP-фильтрации заполните `WATA_TRUSTED_IPS`.

### Ограничения

- `WATA_LINK_TTL_MINUTES` должен быть от `15` до `43200`.

### Справочник

- [Wata](../configuration/env-vars.md#wata)

## CryptoPay

CryptoPay используется для криптовалютных платежей через отдельный токен и сеть Crypto Bot API.

### Настройка

1. Включите `CRYPTOPAY_ENABLED`.
2. Укажите `CRYPTOPAY_TOKEN`.
3. Выберите `CRYPTOPAY_NETWORK`: `mainnet` или `testnet`.
4. Задайте `CRYPTOPAY_CURRENCY_TYPE`: `fiat` или `crypto`.
5. Скопируйте URL вебхука из админ-панели и укажите его в CryptoPay.
6. Проверьте `CRYPTOPAY_ASSET`.

### Проверка

- Testnet-токен должен использоваться только с `testnet`.
- Mainnet-токен должен использоваться только с `mainnet`.
- Если сумма или asset выглядят неверно, проверьте сочетание `CRYPTOPAY_CURRENCY_TYPE` и `CRYPTOPAY_ASSET`.

### Справочник

- [CryptoPay](../configuration/env-vars.md#cryptopay)

## Heleket

Heleket используется для крипто-инвойсов с merchant ID, ключом платежного API, валютой инвойса и настройками проверки webhook.

### Настройка

1. Включите `HELEKET_ENABLED`.
2. Укажите `HELEKET_BASE_URL`, `HELEKET_MERCHANT_ID` и `HELEKET_API_KEY`.
3. Настройте `HELEKET_CURRENCY`.
4. Скопируйте URL вебхука из админ-панели и укажите его в кабинете Heleket.
5. При необходимости задайте `HELEKET_TO_CURRENCY` и `HELEKET_NETWORK`.
7. При необходимости включите `HELEKET_VERIFY_WEBHOOK_SIGNATURE`.
8. Для IP-фильтрации заполните `HELEKET_TRUSTED_IPS`.

### Ограничения

- `HELEKET_LIFETIME_SECONDS` должен быть от `300` до `43200`.

### Справочник

- [Heleket](../configuration/env-vars.md#heleket)

## Telegram Stars

Telegram Stars используются напрямую и поддерживаются в legacy-ценах и JSON-каталоге тарифов.

### Где используются

- Цены period-подписок.
- Пакеты трафика.
- Premium-докупки.
- HWID-докупки, если они включены в каталоге тарифов.

### Настройка

1. Включите `STARS_ENABLED`.
2. Проверьте Stars-цены в legacy-настройках или JSON-каталоге.
3. Убедитесь, что цена округляется до целого количества Stars.
4. Проверьте сценарии смены тарифа.

### Ограничения

- XTR/Stars-докупки не конвертируются без явно заданного курса.

### Справочник

- [Переменные платежей](../configuration/env-vars.md#платежи)
- [Тарифы](tariffs.md)
