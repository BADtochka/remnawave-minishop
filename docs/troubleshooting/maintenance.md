# Обслуживание

Плановое обслуживание обычно сводится к обновлению образов, проверке миграций, логов и резервных копий PostgreSQL.

## Обновление

```bash
docker compose pull
docker compose up -d
docker compose logs -f migrate backend worker
```

## Резервная копия PostgreSQL

```bash
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > backup.sql
```

## Проверки после работ

- `docker compose ps`
- `docker compose logs -f backend worker frontend`
- `/healthz` на backend-домене
- вход в Mini App и админку
- тестовый платеж или тестовая активация
