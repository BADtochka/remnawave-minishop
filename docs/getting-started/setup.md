# Установка

Начните с `.env`, затем поднимите Compose-стек и проверьте backend, worker и frontend.

## Минимальный запуск

```bash
cp .env.example .env
nano .env
docker compose up -d --build
docker compose ps
docker compose logs -f backend worker frontend
```

## Что заполнить в первую очередь

- `BOT_TOKEN` и `ADMIN_IDS` для доступа к боту и админке.
- `WEBHOOK_BASE_URL` для Telegram, платежных и panel webhook URL.
- `SUBSCRIPTION_MINI_APP_URL` для Mini App и кнопок в Telegram.
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.
- `WEBAPP_SESSION_SECRET`, `WEBHOOK_SECRET_TOKEN`, `PANEL_API_URL`, `PANEL_API_KEY`, `PANEL_WEBHOOK_SECRET`.

## Как выбрать Compose-вариант

- Для быстрого публичного HTTPS берите [Caddy](../deploy-examples/caddy.md).
- Если у вас уже есть TLS-сертификаты и нужен Nginx в Docker-сети, берите [Nginx](../deploy-examples/nginx.md).
- Если нельзя открывать входящие порты на сервере приложения, берите [Pangolin/Newt](../deploy-examples/newt.md).
- Для локальной проверки или внешнего TLS-терминатора берите [no-proxy](../deploy-examples/no-proxy.md).

## После первого входа

1. Откройте админку через Mini App.
2. Проверьте платежные методы в настройках.
3. Настройте каталог тарифов.
4. Проверьте инструкции подключения.
5. Сделайте тестовую покупку или пробную активацию.

Подробности: [настройка окружения](../configuration.md) и [развертывание](../deployment.md).
