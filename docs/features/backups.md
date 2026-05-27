# Бэкапы и восстановление

Minishop умеет автоматически собирать ZIP-бэкапы в worker-контейнере, хранить последние архивы на сервере, отправлять их в Telegram и восстанавливать БД/compose-папку из админки.

## Что попадает в архив

Архив создается в `BACKUP_DIR`, по умолчанию `data/backups` внутри volume `shop-data`.

Типовой файл называется так:

```text
remnawave-minishop-backup-20260527-120000+0300.zip
```

Внутри:

- `database/<POSTGRES_DB>.dump` - `pg_dump` в custom format для `pg_restore`;
- `compose/` - snapshot папки с `docker-compose.yml`, `.env` и соседними конфигами;
- `manifest.json` - дата создания, сведения о БД, compose snapshot и предупреждения.

Если compose-папка не смонтирована или недоступна, worker не роняет весь бэкап: архив будет создан с дампом БД и предупреждением в `manifest.json`.

## Настройка

Основные параметры доступны в админке: **Система -> Настройки -> Бэкапы**.

Минимальный `.env`:

```env
BACKUP_ENABLED=True
BACKUP_CHAT_ID=-1001234567890
BACKUP_INTERVAL_SECONDS=3600
BACKUP_LOCAL_RETENTION=100
BACKUP_COMPOSE_ENABLED=True
COMPOSE_BACKUP_SOURCE=.
COMPOSE_RESTORE_MODE=rw
```

`BACKUP_INTERVAL_SECONDS=3600` запускает бэкапы ровно на границе часа: 12:00, 13:00 и т.д. Значение по умолчанию для локального хранения - 100 последних ZIP-архивов.

`BACKUP_CHAT_ID` задает чат Telegram для отправки архивов. Если он пустой, используется `LOG_CHAT_ID`. Для topic/thread можно указать `BACKUP_THREAD_ID`; если он пустой, используется `LOG_THREAD_ID`.

Каждый архив подписывается HMAC-подписью в `manifest.json` и содержит SHA-256 каждого файла. По умолчанию restore принимает только архивы с валидной подписью этого инстанса. Если нужен отдельный стабильный ключ подписи, задайте `BACKUP_ARCHIVE_SIGNATURE_SECRET`; если ключ пустой, используется `BOT_TOKEN`.

## Mount compose-папки

В стандартных compose-файлах есть два mount:

- `worker`: `${COMPOSE_BACKUP_SOURCE:-.}:/app/compose-source:ro` - только читает папку для создания snapshot;
- `backend`: `${COMPOSE_BACKUP_SOURCE:-.}:/app/compose-source:${COMPOSE_RESTORE_MODE:-rw}` - читает список архивов и может восстановить compose-папку из админки.

`COMPOSE_BACKUP_SOURCE=.` означает папку рядом с текущим `docker-compose.yml`. Если compose лежит в другом месте, укажите абсолютный host-путь.

Если нужно запретить восстановление compose-файлов из контейнера, задайте:

```env
COMPOSE_RESTORE_MODE=ro
```

В этом режиме восстановление БД останется доступным, а восстановление compose-папки вернет понятную ошибку о недоступной записи.

## Восстановление из админки

Откройте **Система -> Бэкапы**. В разделе можно:

- выбрать архив, уже лежащий в `data/backups`;
- загрузить ZIP-архив вручную;
- отметить, что восстанавливать: `БД`, `compose-папка` или оба варианта;
- запустить восстановление после подтверждения.

БД восстанавливается через `pg_restore --clean --if-exists --no-owner --no-privileges`. На время восстановления лучше не запускать платежи, рассылки, массовую синхронизацию и ручные изменения подписок.

Compose-файлы восстанавливаются поверх текущей папки. Перед заменой backend создает pre-restore snapshot текущего compose-каталога рядом с остальными архивами:

```text
remnawave-minishop-compose-pre-restore-YYYYMMDD-HHMMSS+ZZZZ.zip
```

После восстановления compose-папки перезапустите нужные сервисы, чтобы изменения `docker-compose.yml`, `.env`, Caddyfile/Nginx-конфигов и других файлов реально применились:

```bash
docker compose up -d --build backend worker
docker compose ps
```

Если менялись proxy-конфиги, перезапустите соответствующий сервис (`caddy`, `nginx`, `newt`).

## Проверка архива перед восстановлением

Backend валидирует архив до восстановления:

- файл должен быть валидным ZIP;
- `manifest.json` должен принадлежать `remnawave-minishop` и иметь поддерживаемую версию формата;
- HMAC-подпись manifest должна быть валидной, если `BACKUP_ARCHIVE_SIGNATURE_REQUIRED=True`;
- SHA-256 и размер каждого файла должны совпадать с manifest;
- выбранный server-side файл должен лежать внутри `BACKUP_DIR`, путь вида `../backup.zip` отклоняется;
- пути внутри ZIP не могут быть абсолютными, содержать `..`, `\`, пустые сегменты или дубли;
- архивы с подозрительно большим числом файлов, размером или zip-bomb compression ratio отклоняются;
- для восстановления БД нужен `database/*.dump` или `database/*.backup`;
- для восстановления compose нужны файлы внутри `compose/`;
- compose restore стартует только если целевая папка существует и доступна на запись;
- backup/restore защищены одним Redis lock, чтобы две операции не выполнялись одновременно.

Это защищает от случайной загрузки мусорного файла, zip-slip-архивов, поврежденных ZIP и структурно похожих архивов, которые не были созданы этим инстансом. Если вы сознательно восстанавливаете старый неподписанный архив, временно выставьте `BACKUP_ARCHIVE_SIGNATURE_REQUIRED=False`, восстановите архив и верните проверку обратно.

## Ручное восстановление БД

Если админка недоступна, можно восстановить дамп вручную:

```bash
unzip remnawave-minishop-backup-YYYYMMDD-HHMMSS+ZZZZ.zip -d restore
docker compose cp restore/database/remnawave_minishop.dump postgres:/tmp/remnawave_minishop.dump
docker compose stop backend worker
docker compose exec postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges /tmp/remnawave_minishop.dump'
docker compose up -d backend worker
```

После ручного восстановления проверьте миграции и healthcheck:

```bash
docker compose run --rm migrate
docker compose ps
docker compose logs -f backend worker
```

## Переменные

Полный справочник лежит в [переменных окружения](../configuration/env-vars.md#кеши-rate-limits-и-worker). Основные ключи:

| Переменная | Назначение |
| --- | --- |
| `BACKUP_ENABLED` | Включает периодические бэкапы. |
| `BACKUP_CHAT_ID` / `BACKUP_THREAD_ID` | Куда отправлять архивы в Telegram. |
| `BACKUP_INTERVAL_SECONDS` | Периодичность, по умолчанию `3600`. |
| `BACKUP_LOCAL_RETENTION` | Сколько последних архивов хранить на сервере. |
| `BACKUP_DIR` | Каталог ZIP-архивов. |
| `BACKUP_ARCHIVE_SIGNATURE_REQUIRED` | Требовать валидную HMAC-подпись manifest при upload/restore. |
| `BACKUP_ARCHIVE_SIGNATURE_SECRET` | Отдельный секрет подписи архивов; если пустой, используется `BOT_TOKEN`. |
| `BACKUP_COMPOSE_ENABLED` | Добавлять compose snapshot. |
| `COMPOSE_BACKUP_SOURCE` | Host-путь compose-папки для mount в контейнеры. |
| `COMPOSE_RESTORE_MODE` | `rw` для восстановления compose из админки, `ro` для запрета записи. |
| `BACKUP_PG_DUMP_PATH` / `BACKUP_PG_RESTORE_PATH` | Пути к `pg_dump` и `pg_restore` внутри контейнеров. |
