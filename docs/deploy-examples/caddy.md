# Caddy

Вариант `deploy/examples/caddy` подходит, если нужен самый простой публичный HTTPS. Caddy сам выпускает и продлевает сертификаты Let's Encrypt.

## Требования

- На сервере открыты входящие `80/tcp` и `443/tcp`.
- DNS-записи `WEBHOOK_HOST` и `MINIAPP_HOST` смотрят на этот сервер.
- В `.env` заполнены домены, токены, секреты и доступы к Remnawave.

## Запуск

```bash
cd deploy/examples/caddy
cp .env.example .env
nano .env
docker compose up -d
```

Минимально поменяйте:

- `WEBHOOK_HOST` и `MINIAPP_HOST`;
- `BOT_TOKEN`, `ADMIN_IDS`;
- `POSTGRES_PASSWORD`;
- `WEBAPP_SESSION_SECRET`, `WEBHOOK_SECRET_TOKEN`;
- `PANEL_API_URL`, `PANEL_API_KEY`, `PANEL_WEBHOOK_SECRET`.

## Проверка

```bash
docker compose ps
docker compose logs -f caddy backend worker frontend
```

Если нужна нестандартная логика Caddy, правьте `deploy/examples/caddy/Caddyfile` и перезапускайте:

```bash
docker compose up -d --force-recreate caddy
```
