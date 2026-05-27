# Обслуживание

Плановое обслуживание обычно сводится к обновлению образов, проверке миграций, логов и резервных копий. Подробная инструкция по автоматическим ZIP-бэкапам и восстановлению вынесена в [бэкапы и восстановление](../features/backups.md).

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

## Автоматические бэкапы

Worker может собирать ZIP-архивы с дампом PostgreSQL и snapshot compose-папки, отправлять их в Telegram и хранить последние архивы в `data/backups`. Настройка и восстановление описаны в [отдельном разделе](../features/backups.md).

После изменения backup-настроек в `.env` перезапустите backend и worker:

```bash
docker compose up -d --build backend worker
docker compose logs -f backend worker
```

Восстановление из архива доступно в админке **Система -> Бэкапы**. Там же можно загрузить ZIP вручную, выбрать `БД` и/или `compose-папка`, а backend проверит архив перед запуском. Подробности: [бэкапы и восстановление](../features/backups.md#восстановление-из-админки).

## Проверки после работ

- `docker compose ps`
- `docker compose logs -f backend worker frontend`
- `/healthz` на backend-домене
- вход в Mini App и админку
- тестовый платеж или тестовая активация
