# Обзор

Remnawave Minishop состоит из Telegram-бота, backend API, worker-процессов, frontend/Mini App и инфраструктурных сервисов PostgreSQL и Redis. В production эти части запускаются через Docker Compose и общаются с Remnawave Panel по API и вебхукам.

## Основные компоненты

- **Backend** - Telegram webhook, платежные вебхуки, panel webhooks, API для Mini App и админки.
- **Worker** - фоновые задачи, синхронизация подписок, обработка очереди вебхуков и тарифных событий.
- **Frontend** - отдельный nginx-образ с Mini App и админкой.
- **PostgreSQL** - пользователи, платежи, настройки, поддержка, промокоды и служебные данные.
- **Redis** - FSM, кеши, rate limit, очередь вебхуков и distributed locks.

## Сценарии

- пользователь открывает Mini App, видит подписку и оплачивает тариф;
- платежный провайдер отправляет webhook в backend;
- worker применяет фоновые задачи и синхронизацию;
- Remnawave Panel хранит пользователя, подписку и ссылку подключения;
- администратор управляет тарифами, поддержкой, пользователями и настройками через админку.

## Куда идти дальше

- [Установка](setup.md) - базовый запуск через Compose.
- [Deploy examples](../deploy-examples/index.md) - готовые варианты публикации.
- [Архитектура](../architecture.md) - структура каталогов и сервисов.
- [Mini App](../features/web-app.md) - публичный frontend, Telegram OAuth и инструкции установки.
