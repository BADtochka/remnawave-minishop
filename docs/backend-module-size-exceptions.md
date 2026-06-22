# Backend Module Size Exceptions

The API refactor F5 cleanup keeps these modules intentionally colocated until their tests
can be migrated away from module-level monkeypatch targets or their provider registration
surfaces can be split without changing import paths:

- `backend/bot/payment_providers/yookassa.py`: webhook, callback, and recurring helpers
  are patched through the legacy module in provider and HWID tests; split into route,
  webhook, success, and payment-method modules together with compatibility shims.
- `backend/bot/payment_providers/wata.py`: webhook tests patch provider module DAL and
  service behavior; split config/core/service after those tests target stable helper
  modules.
- `backend/bot/payment_providers/paykilla.py`: security and payment-method tests import
  private signing/minimum helpers from the provider module; split core/service once those
  helpers have an explicit compatibility module.
- `backend/bot/app/web/admin_api_impl/users.py`: admin API tests patch auth, DAL, and
  serializer helpers through `admin_api_impl.users`; split list/detail/mutation routes
  after those patch targets move to shared dependency modules.
- `backend/bot/handlers/admin/user_management.py`: admin bot actions share one router and
  callback-state flow; split by action group after route-level tests patch handler entry
  points instead of the module namespace.
- `backend/bot/services/subscription_service_impl/lifecycle.py`: tests patch DAL objects
  through `subscription_service_impl.lifecycle`; move lifecycle phases to helper mixins
  only together with patch-target updates.
- `backend/bot/app/web/webapp/auth.py`: account-linking and referral tests patch
  `webapp.auth.user_dal` and related helpers; split OAuth, email auth, and referral
  flows after those tests target a shared dependency module.
- `backend/scripts/import_legacy.py`: one-shot migration CLI keeps parser, legacy schema
  normalization, and write pipeline together so operator dry-runs match production import
  behavior; split after snapshot tests cover each import phase and the CLI exposes stable
  phase helpers.
- `backend/bot/app/web/webapp/assets.py`: asset upload, favicon/logo fallback, and static
  response helpers share filesystem cleanup and cache invalidation state; split storage and
  response helpers after webapp asset tests stop patching module-level paths.
- `backend/bot/handlers/user/subscription/core.py`: user subscription callbacks share
  callback-data grammar and payment/top-up/device flows; split by purchase, device, and
  renewal flows once router tests target exported handler groups instead of this module.
- `backend/bot/handlers/admin/sync_admin.py`: panel sync is a single transactional
  reconciliation workflow with shared counters and identity maps; split into prefetch,
  identity-merge, subscription-sync, and reporting phases after fixture coverage protects
  the reconciliation invariants.
- `backend/db/migrator.py`: ordered migrations intentionally live in one file so fresh
  installs and upgrade tests use the same sequence; split only after migration discovery
  and ordering are covered by dedicated tests.
- `backend/bot/services/tariff_worker.py`: background traffic accounting shares cache
  state, warning thresholds, and panel lookups across regular, premium, and HWID flows;
  split once cache ownership is extracted behind a typed service boundary.
- `backend/config/settings.py`: pydantic settings, computed compatibility aliases, and
  legacy env names are colocated to avoid changing deployment configuration semantics;
  split provider/webapp/backup settings after env alias snapshot tests are in place.
- `backend/db/dal/user_dal.py`: user merge, referral, auth, and subscription lookup helpers
  are still patched through one DAL module; split after SQLAlchemy model assignment typing
  and test patch targets move to narrower repositories.
- `backend/bot/handlers/user/start.py`: `/start`, deep links, referral entry points, promo
  activation, notification opt-in, and required-channel gating share one onboarding state
  machine; split after deep-link routing tests cover each branch.
- `backend/bot/services/panel_api_service.py`: the Remnawave API client keeps endpoint
  wrappers and response normalization together for retry/logging consistency; split
  endpoint groups after a typed HTTP response adapter is introduced.
- `backend/bot/app/web/webapp/billing.py`: billing webapp routes share provider selection,
  recurring metadata, and payment-response shaping; split once provider-specific route
  tests assert the shared response contract.
- `backend/bot/payment_providers/stripe.py`: Stripe checkout, webhook, and recurring helper
  functions share signing and metadata conventions; split after webhook signature and
  recurring tests patch stable helper modules instead of the provider module.
- `backend/bot/services/email_templates.py`: template builders share translation fallback,
  HTML escaping, and branding helpers; split after template snapshot tests cover each mail
  family.
