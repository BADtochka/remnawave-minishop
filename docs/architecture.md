# Архитектура проекта

Репозиторий разделен по зонам ответственности рантайма:

```text
backend/              Python-код приложения
  bot/                Telegram-бот, aiohttp API, вебхуки, сервисы
  config/             Pydantic-настройки и загрузчики тарифов/тем
  db/                 SQLAlchemy-модели, DAL, миграции
  main_backend.py     точка входа aiohttp backend
  main_worker.py      точка входа фонового worker
  main_migrate.py     одноразовый запуск миграций
  requirements.txt    Python-зависимости рантайма

frontend/             Svelte/Vite Mini App и админка
  src/                исходный код Svelte
  scripts/            вспомогательные скрипты сборки frontend
  package.json        Node-скрипты и зависимости

deploy/
  docker/             Dockerfile, nginx- и caddy-конфиги рантайма
  examples/           готовые Docker Compose примеры запуска

data/                 данные рантайма, монтируемые в контейнеры
locales/              переводы бота и Web App
tests/                Python-тесты
```

Основной `docker-compose.yml` находится в корне репозитория, чтобы `docker compose up` оставался простым продакшен-путем. Он собирает три прикладных образа из `deploy/docker/Dockerfile`:

- `backend`: aiohttp API и вебхуки.
- `worker`: worker тарифов, синхронизация с панелью, обработчики очередей вебхуков.
- `frontend`: статические Svelte-ассеты, которые отдает nginx.

Сервис `migrate` - одноразовый контейнер на базе backend-образа. Он входит в стандартный Compose-граф: Postgres и Redis переходят в healthy-состояние, `migrate` применяет `Base.metadata.create_all` и ожидающие `schema_migrations`, а затем `backend` и `worker` стартуют только после успешного завершения `migrate`. Так миграции остаются автоматическими для `docker compose up`, но не запускаются внутри каждой backend-реплики.

Python-импорты намеренно остаются в пространствах `bot.*`, `config.*` и `db.*`. Контейнеры рантайма выставляют `PYTHONPATH=/app/backend`; локальные тесты используют такую же раскладку через `pytest.ini`.

Основные команды:

```bash
docker compose up -d --build
docker compose run --rm migrate
docker compose logs -f backend worker frontend
npm run build:webapp
pytest -q
```
