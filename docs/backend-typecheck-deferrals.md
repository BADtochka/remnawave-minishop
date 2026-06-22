# Backend Typecheck Deferrals

CI now runs the backend mypy ratchet over the actively cleaned layers:

- `backend/db`
- `backend/bot/infra`
- `backend/bot/payment_providers`
- `backend/bot/services`
- `backend/bot/handlers`
- `backend/bot/app/web/admin_api_impl`
- `backend/bot/app/web/webapp`
- `backend/bot/app/web/http_contracts.py`
- `backend/bot/app/web/route_contracts.py`
- `backend/bot/app/web/openapi.py`

The remaining backend-wide `mypy --explicit-package-bases backend` errors are deferred
until the owning surfaces below are migrated. Owner for each item is the backend
maintainer group unless a narrower owner is introduced.

- `backend/config/settings.py`: pydantic computed fields currently trigger mypy
  `prop-decorator` limitations and required-env constructor noise. Exit criteria: move
  compatibility aliases to typed helpers or a pydantic pattern mypy accepts.
- `backend/bot/middlewares/*`: aiogram `BaseMiddleware.__call__` expects
  `TelegramObject`, while local middlewares use narrower event types. Exit criteria:
  widen middleware signatures and perform typed narrowing inside each middleware.
- `backend/bot/main_bot.py`: aiogram command-scope overloads need narrower scope types.
  Exit criteria: construct concrete scope classes where commands are deleted/registered.
- `backend/bot/keyboards/inline/user_keyboards.py`: optional tariff/package dicts need
  explicit shape checks before `.get`. Exit criteria: introduce typed tariff keyboard
  payload helpers.
- `backend/bot/app/web/web_server.py` and `backend/bot/app/controllers/*`: app assembly
  still mixes route metadata and aiohttp app state values. Exit criteria: type route state
  and dispatcher construction helpers.
- `backend/bot/services/panel_dry_run_api_service.py`: dry-run panel responses are
  JSON-like dictionaries with optional values passed through `PanelApiService` signatures.
  Exit criteria: introduce a typed panel response adapter shared with the real client.
- `backend/scripts/import_legacy.py`: legacy import payloads intentionally accept multiple
  historical shapes. Exit criteria: split parsing/normalization/write phases with typed
  intermediate dataclasses.
- `backend/db/dal/support_dal.py`, `backend/db/dal/security_dal.py`, and
  `backend/db/dal/user_dal.py`: SQLAlchemy model assignments are still seen as
  `Column[...]` under the backend package-base run. Exit criteria: finish ORM typing
  migration or add typed repository DTOs around mutable model updates.

Package-level strictness is intentionally limited to modules that pass today:

- `db.*`
- `bot.infra.*`
- `bot.app.web.http_contracts`
- `bot.app.web.route_contracts`
- `web.http_contracts`
- `web.route_contracts`
- `web.openapi`

`handlers`, `services`, `payment_providers`, `admin_api_impl`, and `webapp` are green in
normal CI mypy mode but still have untyped handler signatures or `Any`-return boundaries
under strict flags. Promote them module-by-module after those boundaries are typed.
