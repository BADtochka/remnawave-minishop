# Deploy examples

В `deploy/examples` лежат самодостаточные Compose-варианты для разных способов публикации Minishop. Каждый пример запускается из своей директории и содержит собственный `docker-compose.yml`, `.env.example` и README.

```bash
cp .env.example .env
nano .env
docker compose up -d
```

После старта проверяйте:

```bash
docker compose ps
docker compose logs -f backend worker frontend
```

## Какой вариант выбрать

| Вариант | Когда использовать | Где лежит |
| --- | --- | --- |
| [Caddy](caddy.md) | Нужен самый простой публичный HTTPS с автоматическими сертификатами Let's Encrypt. | `deploy/examples/caddy` |
| [Nginx](nginx.md) | Уже используете Nginx и готовы положить TLS-сертификаты рядом с примером. | `deploy/examples/nginx` |
| [Pangolin/Newt](newt.md) | Публикуете сервисы через туннель без входящих портов на сервере приложения. | `deploy/examples/newt` |
| [No proxy](no-proxy.md) | Нужно напрямую открыть порты backend/frontend или проверить стек без reverse proxy. | `deploy/examples/no-proxy` |

## Два публичных URL

Для production обычно нужны два домена:

- webhook/backend URL для Telegram, платежных систем и Remnawave webhooks;
- Mini App/frontend URL для Telegram Mini App, Web App и админки.

Пример:

```text
https://webhooks.example.com -> backend:8080
https://app.example.com      -> frontend:80
```
