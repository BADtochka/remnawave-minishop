# Без reverse proxy

Вариант `deploy/examples/no-proxy` напрямую публикует HTTP-порты backend и frontend. Он удобен для локальной проверки, внутренней сети или ситуации, когда HTTPS завершается внешней платформой.

## Порты

- backend/webhooks: `WEB_SERVER_BIND`, по умолчанию `0.0.0.0:8080`;
- frontend/Mini App: `FRONTEND_BIND`, по умолчанию `0.0.0.0:8082`.

## Запуск

```bash
cd deploy/examples/no-proxy
cp .env.example .env
nano .env
docker compose up -d
```

## Важно про HTTPS

Контейнеры приложения сами не выпускают TLS-сертификаты. Для реального Telegram webhook и Mini App публичные URL должны быть HTTPS.

Используйте этот вариант, если:

- проверяете стек локально;
- публикуете сервисы только во внутренней сети;
- TLS уже завершается внешним reverse proxy, load balancer или платформой.

## Проверка

```bash
curl http://127.0.0.1:8080/healthz
curl http://127.0.0.1:8082/health
docker compose logs -f backend worker frontend
```
