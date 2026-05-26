# Платежи

Платежные методы включаются настройками и отображаются пользователю как кнопки оплаты в Mini App и Telegram-сценариях.

## Поддерживаемые провайдеры

- [YooKassa](../payments/yookassa.md)
- [FreeKassa](../payments/freekassa.md)
- [Platega](../payments/platega.md)
- [SeverPay](../payments/severpay.md)
- [Wata](../payments/wata.md)
- [CryptoPay](../payments/cryptopay.md)
- [Heleket](../payments/heleket.md)
- [Telegram Stars](../payments/telegram-stars.md)

## Типовой порядок настройки

1. Включите нужный провайдер в админке или через `.env`.
2. Заполните публичные параметры и секреты.
3. Настройте webhook URL у провайдера, если это требуется.
4. Проверьте порядок и подписи кнопок оплаты.
5. Выполните тестовый платеж и проверьте логи backend.

## Где смотреть параметры

- [Справочник `.env`](../configuration/env-vars.md) содержит все ключи провайдеров.
- [Админ-панель](admin-panel.md) описывает UI-настройки платежей.
- [Тарифы](tariffs.md) описывают цены, Stars и сценарии покупки.
