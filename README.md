# Remnawave Minishop

Remnawave Minishop - Telegram-бот и Web App (Mini App) для продажи и управления подписками Remnawave. Бот обрабатывает регистрацию, оплату, продление, пробный период, промокоды, рефералов и поддержку в чате. Web App показывает ссылку подключения, срок действия, трафик, оплату, устройства и вход по Telegram Mini Apps `initData`, Telegram OAuth / OpenID Connect и одноразовому email-коду.

Проект является переработанным форком [kavore/remnawave-tg-shop](https://github.com/kavore/remnawave-tg-shop). Для переноса данных из прежнего стека используйте [инструкцию по миграции](docs/migration-to-minishop.md).

## Возможности

Для пользователей:

- регистрация с выбором русского или английского языка;
- просмотр статуса подписки, даты окончания, ссылки подключения и трафика;
- покупка подписок, пакетов трафика, докупка трафика и устройств по настроенному каталогу тарифов;
- Web App / Mini App с входом через Telegram или email;
- пробный период, промокоды и реферальная программа;
- оплата через YooKassa, FreeKassa, Platega, SeverPay, CryptoPay и Telegram Stars;
- раздел "Мои устройства" при включенном `MY_DEVICES_SECTION_ENABLED`.

Для администраторов:

- админ-панель для пользователей из `ADMIN_IDS`;
- статистика пользователей, подписок, платежей и синхронизации с Remnawave;
- блокировка пользователей, рассылки, промокоды и логи действий;
- ручная синхронизация пользователей и подписок с панелью.

## Документация

- [Настройка окружения](docs/configuration.md) - основные переменные `.env`, платежи, Remnawave, пробный период и секреты.
- [Тарифы](docs/tariffs.md) - каталог тарифов, period- и traffic-модели, докупки, смена тарифа, HWID-лимиты и обработка трафика.
- [Web App / Mini App](docs/webapp.md) - отдельный порт, домен, Telegram OAuth, email-вход и реферальные ссылки.
- [Развертывание](docs/deployment.md) - Docker Compose, reverse proxy, Nginx, Caddy, вебхуки и запуск из образа.
- [Миграция с remnawave-tg-shop](docs/migration-to-minishop.md) - перенос данных из прежнего стека.

## Быстрый старт

Требования:

- Docker и Docker Compose;
- рабочая панель Remnawave;
- токен Telegram-бота;
- параметры хотя бы одного платежного провайдера.

```bash
git clone https://github.com/3252a8/remnawave-minishop
cd remnawave-minishop
cp .env.example .env
nano .env
docker compose up -d --build
docker compose logs -f remnawave-minishop
```

Минимально заполните в `.env`:

- `BOT_TOKEN` - токен Telegram-бота;
- `ADMIN_IDS` - Telegram ID администраторов через запятую;
- `WEBHOOK_BASE_URL` - публичный URL вебхуков;
- `PANEL_API_URL`, `PANEL_API_KEY`, `PANEL_WEBHOOK_SECRET` - доступ к Remnawave;
- `USER_SQUAD_UUIDS` - Internal Squads для пользователей;
- настройки платежного провайдера;
- `SUBSCRIPTION_MINI_APP_URL`, если используется Web App.

Для каталога тарифов используется `TARIFFS_CONFIG_PATH` со значением по умолчанию `config/tariffs.json`. Пример формата лежит в [config/tariffs.example.json](config/tariffs.example.json), подробности - в [docs/tariffs.md](docs/tariffs.md).

## Полезные команды

```bash
# Локальная сборка и запуск
docker compose up -d --build

# Логи приложения
docker compose logs -f remnawave-minishop

# Запуск с Caddy
docker compose -f docker-compose-caddy.yml up -d --build

# Запуск из готового образа
IMAGE_TAG=3.1.0 docker compose -f docker-compose-remote-server.yml up -d
```

## Поддержка

- Crypto: `USDT/Other ERC-20 0xeD506D44aae634fEc0E01C8835744fBedb7B2a44 (Ethereum/Polygon/Gnosis)`
