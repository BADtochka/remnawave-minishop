# Pangolin / Newt

Вариант `deploy/examples/newt` подходит, если сервер приложения не должен принимать входящие соединения. Newt подключается к Pangolin, а публичные домены настраиваются ресурсами в панели Pangolin.

## Запуск

```bash
cd deploy/examples/newt
cp .env.example .env
nano .env
docker compose up -d
```

В `.env` заполните:

- `WEBHOOK_HOST` и `MINIAPP_HOST` - публичные домены ресурсов в Pangolin;
- `PANGOLIN_ENDPOINT`, `NEWT_ID`, `NEWT_SECRET` - значения из настроек site/client в Pangolin;
- обычные переменные приложения: `BOT_TOKEN`, `ADMIN_IDS`, `POSTGRES_PASSWORD`, секреты и доступ к Remnawave.

## Ресурсы Pangolin

Создайте два HTTP-ресурса для Newt site:

| Публичный домен | Upstream |
| --- | --- |
| `https://webhooks.example.com` | `http://backend:8080` |
| `https://app.example.com` | `http://frontend:80` |

Домены в Pangolin должны совпадать с `WEBHOOK_HOST` и `MINIAPP_HOST`.

Официальная инструкция Pangolin по установке Newt site: <https://docs.pangolin.net/manage/sites/install-site>.

## Проверка

```bash
docker compose ps
docker compose logs -f newt backend worker frontend
```
