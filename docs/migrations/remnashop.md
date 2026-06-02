# Миграция из Remnashop

Remnashop импортируется через общий legacy-importer `backend/scripts/import_legacy.py`.
Самый удобный путь - интерактивный install wizard:

```bash
curl -fsSL https://raw.githubusercontent.com/3252a8/remnawave-minishop/main/scripts/install.sh -o install.sh
sh install.sh
```

В меню выберите `Install new stack and run legacy migration` для нового сервера
или `Run legacy migration only`, если compose-папка и `.env` уже готовы.

## Что переносится

- пользователи Telegram, username, email, Remnawave UUID и метаданные профиля;
- старые referral codes и связи рефералов;
- подписки, сроки, лимиты трафика, HWID/device limit и UUID подписок панели;
- платежи и статусы платежей;
- промокоды на дни подписки и их активации, если таблицы есть в source DB;
- служебные mappings, чтобы повторный запуск мог работать в режиме `merge`;
- настройки совместимости Remnashop в админке: старые ref-ссылки и promo codes.

Данные, которые не имеют прямого аналога, сохраняются в legacy mappings или
message logs как заметки, чтобы администратор мог проверить их после переноса.

## Flow wizard

1. Wizard скачивает compose-профиль и `backend/scripts/import_legacy.py` через
   `raw.githubusercontent.com`, без клонирования репозитория.
2. Вы указываете source PostgreSQL DSN Remnashop и schema, обычно `public`.
3. Вы выбираете целевую БД: текущую compose-БД или ручной target DSN.
4. При необходимости указываете JSON map тарифов Remnashop в локальные
   `tariff_key`, например `{"basic": "standard_month"}`.
5. Wizard запускает `dry-run` и показывает JSON-сводку.
6. После подтверждения `y` importer применяет изменения и перезапускает
   `backend`/`worker`, чтобы настройки совместимости перечитались.

Если source DB находится на том же Docker host, помните, что DSN выполняется
из backend-контейнера. Для подключения к сервису вне compose-сети может
понадобиться host name вроде `host.docker.internal`, внешний адрес сервера или
ручное подключение контейнеров к общей Docker network.

## Ручной запуск

Если нужно запустить importer без wizard:

```bash
docker compose run --rm backend \
  python backend/scripts/import_legacy.py \
    --source-type remnashop \
    --source-dsn 'postgresql://old_user:old_password@old_host:5432/remnashop' \
    --source-schema public \
    --dry-run
```

После успешного `dry-run` повторите команду без `--dry-run`. По умолчанию
режим конфликтов `merge`: существующие пользователи и платежи сопоставляются,
а новые записи добавляются. Для узкого импорта используйте `--only`, например
`--only users,referrals,promocodes`.
