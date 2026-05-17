# Project Architecture

The repository is split by runtime responsibility:

```text
backend/              Python application code
  bot/                Telegram bot, aiohttp APIs, webhooks, services
  config/             Pydantic settings and tariff/theme config loaders
  db/                 SQLAlchemy models, DAL, migrations
  main_backend.py     aiohttp backend entrypoint
  main_worker.py      background worker entrypoint
  main_migrate.py     one-shot migration entrypoint
  requirements.txt    Python runtime dependencies

frontend/             Svelte/Vite Mini App and admin UI
  src/                Svelte source code
  scripts/            frontend build helpers
  package.json        Node scripts and dependencies

deploy/
  docker/             Dockerfile, nginx and caddy runtime config
  compose/            legacy/alternate compose examples

data/                 runtime data mounted in containers
locales/              bot and Web App translations
tests/                Python test suite
```

The default `docker-compose.yml` stays in the repository root so `docker compose up` remains the
simple production path. It builds three application images from `deploy/docker/Dockerfile`:

- `backend`: aiohttp APIs and webhooks only.
- `worker`: tariff traffic worker, panel sync, webhook queue consumers.
- `frontend`: static Svelte assets served by nginx.

The `migrate` service is a one-shot container based on the backend image. It is part of the
default Compose dependency graph: Postgres and Redis become healthy, `migrate` applies
`Base.metadata.create_all` and pending `schema_migrations`, then `backend` and `worker` start
only after `migrate` exits successfully. This keeps migrations automatic for `docker compose up`
without running them inside every backend replica.

Python imports intentionally remain `bot.*`, `config.*`, and `db.*`. Runtime containers set
`PYTHONPATH=/app/backend`; local tests use the same layout through `pytest.ini`.

Common commands:

```bash
docker compose up -d --build
docker compose run --rm migrate
docker compose logs -f backend worker frontend
npm run build:webapp
pytest -q
```
