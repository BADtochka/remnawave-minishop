# Единый dev stand

Единый dev stand - это локальный Docker Compose стенд для ручной и будущей
автоматизированной full-stack QA. Он поднимает Mini Shop, PostgreSQL, Redis,
локальную Remnawave Panel, Remnawave Subscription Page и сиды для тестовых
пользователей.

Канонический вход - npm-команды из корня репозитория:

```powershell
Copy-Item deploy/dev/remnawave-dev.env.example .env.remnawave-dev
npm run dev:stand:config
npm run dev:stand:up
```

Старые compose-файлы не являются отдельными dev stand:

- `docker-compose-dev.yml` - базовый локальный Mini Shop стек.
- `docker-compose.remnawave-dev.yml` - overlay с Remnawave, Subscription Page и
  dev-сидами. Именно вместе с базовым файлом он образует единый dev stand.
- `docker-compose.test.yml` - изолированный runner для backend test suite.
- `docker-compose.demo.yml` - nginx для статической docs-demo.
- `docker-compose.yml` - production-like запуск приложения, не QA-стенд.

## Версии

Пинованные версии, проверенные 2026-06-25:

- Remnawave Panel `v2.7.4` (`remnawave/backend:2.7.4`)
- Remnawave Subscription Page `7.2.4`
  (`remnawave/subscription-page:7.2.4`)

Чтобы обновить Remnawave, поменяйте в `.env.remnawave-dev`:

```env
REMNAWAVE_DEV_VERSION=2.7.4
REMNAWAVE_SUBSCRIPTION_PAGE_VERSION=7.2.4
```

## Переменные окружения

Файл `deploy/dev/remnawave-dev.env.example` уже содержит локальные безопасные
значения. Скопируйте его в `.env.remnawave-dev` и меняйте только локально:

```powershell
Copy-Item deploy/dev/remnawave-dev.env.example .env.remnawave-dev
```

По умолчанию Mini Shop работает в dry-run режиме записи в панель:

```env
PANEL_WRITE_MODE=dry_run
PANEL_DRY_RUN_VALIDATE_REMOTE=False
PANEL_DRY_RUN_SYNTHETIC_CREATE=True
```

Это удобно для QA: приложение читает живую локальную Remnawave Panel, но
опасные мутации можно прогонять без реального изменения panel-состояния. Если
нужен live-режим против локальной панели, замените токен на токен из Remnawave
Settings -> API Tokens и включите:

```env
PANEL_API_KEY=...
REMNAWAVE_DEV_API_TOKEN=...
PANEL_WRITE_MODE=live
PANEL_DRY_RUN_VALIDATE_REMOTE=True
```

Детерминированный `REMNAWAVE_DEV_API_TOKEN` из example сидируется SQL-файлом
`deploy/dev/seed-remnawave.sql`. Не меняйте
`REMNAWAVE_DEV_JWT_AUTH_SECRET`, если не заменяете этот токен.

## Запуск

```powershell
npm run dev:stand:config
npm run dev:stand:up
npm run dev:stand:ps
```

Логи основных сервисов:

```powershell
npm run dev:stand:logs
```

Остановка без удаления БД:

```powershell
npm run dev:stand:down
```

Чтобы удалить локальные базы и сиды, выполните тот же compose `down -v`
вручную:

```powershell
docker compose --env-file .env.remnawave-dev `
  -f docker-compose-dev.yml `
  -f docker-compose.remnawave-dev.yml `
  --profile seed `
  down -v
```

## URL

- Mini Shop frontend: `http://127.0.0.1:8082`
- Mini Shop backend health: `http://127.0.0.1:8080/healthz`
- Remnawave Panel: `http://127.0.0.1:3000`
- Remnawave metrics health: `http://127.0.0.1:3001/health`
- Remnawave Subscription Page upstream: `http://127.0.0.1:3010`

Subscription Page требует reverse proxy с HTTPS для прямого браузерного
использования. В этом стенде `127.0.0.1:3010` - локальный upstream; plain HTTP
запрос может вернуть empty reply, даже если сервис здоров и подключен к
Remnawave Panel.

## Сиды

Профиль `seed` выполняет два идемпотентных SQL-файла:

- `deploy/dev/seed-minishop.sql` - пользователи, подписки и платежи Mini Shop.
- `deploy/dev/seed-remnawave.sql` - API token, пользователи Remnawave и
  привязка к `Default-Squad`.

Тестовые пользователи:

| Telegram/user ID | Email | Состояние |
| --- | --- | --- |
| `910000001` | `runes_admin@example.test` | активная standard-подписка, admin ID |
| `910000002` | `runes_active@example.test` | активная premium-подписка около лимита трафика |
| `910000003` | `runes_expired@example.test` | истекшая подписка |

Повторный запуск сидов:

```powershell
docker compose --env-file .env.remnawave-dev `
  -f docker-compose-dev.yml `
  -f docker-compose.remnawave-dev.yml `
  --profile seed `
  run --rm dev-seed
```

Overlay использует отдельные volumes
`remnawave-minishop-runes-dev-db-data` и
`remnawave-minishop-runes-dev-redis-data`, чтобы не портить старый локальный
dev-стек с другими кредами.

## Smoke-проверка стенда

```powershell
curl.exe -fsS http://127.0.0.1:8080/healthz
curl.exe -fsS http://127.0.0.1:3001/health
curl.exe -I -fsS http://127.0.0.1:8082/

docker compose --env-file .env.remnawave-dev `
  -f docker-compose-dev.yml `
  -f docker-compose.remnawave-dev.yml `
  --profile seed `
  exec -T postgres psql -U remnawave_minishop -d remnawave_minishop `
  -c "select count(*) from users; select count(*) from subscriptions; select count(*) from payments;"

docker compose --env-file .env.remnawave-dev `
  -f docker-compose-dev.yml `
  -f docker-compose.remnawave-dev.yml `
  --profile seed `
  exec -T remnawave-db psql -U postgres -d postgres `
  -c "select token_name from api_tokens where uuid='30000000-0000-4000-8000-000000000001'; select username from users where username like 'runes_%' order by username;"
```

## Автоматизация реальных QA-сценариев

Автоматизировать auth/payment/admin-save поверх этого стенда можно. Причина,
почему Playwright mock-smoke из runes-плана этого не делал, не технический
запрет, а граница объема: mock-smoke проверяет статическую demo-сборку без
backend, а реальные сценарии требуют управляемого backend-состояния,
платежных webhook, auth-токенов, CSRF, seed/reset и проверки БД.

Рекомендуемый следующий слой QA:

1. **API-level full-stack tests**: pytest поднимает стенд или использует уже
   поднятый, создает платеж через backend API, затем отправляет в локальный
   webhook payload выбранного провайдера. Для позитивного сценария достаточно
   считать, что провайдер прислал успешный webhook.
2. **Browser E2E against real backend**: Playwright открывает
   `http://127.0.0.1:8082`, логинится через тестовый email/code или заранее
   выданную dev-сессию, проходит покупку до pending/success и проверяет UI.
3. **Admin-save E2E**: Playwright входит тестовым admin user и сохраняет
   настройки/тариф/перевод, затем проверяет API или БД после F5.

Чтобы это стало стабильным CI-гейтом, нужно добавить reset фикстур, единый
тестовый payment-provider/webhook fixture и dev-only способ получить email code
или session token без реального Telegram/SMTP. Сам стенд уже содержит основу
для этого: изолированные volumes, сиды, локальную Remnawave и dry-run/live
переключатель панели.
