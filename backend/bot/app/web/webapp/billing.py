from bot.app.web.webapp.assets import _enforce_webapp_rate_limit, _get_cached_webapp_settings
from bot.app.web.webapp.auth import _require_user_id, _trial_telegram_required_reason
from bot.app.web.webapp.common import (
    _invalidate_webapp_user_caches,
    _json_error,
    _normalize_language,
    _parse_model_payload,
)
from bot.app.web.webapp.payloads import (
    WebAppAutoRenewPayload,
    WebAppPaymentCreatePayload,
    WebAppPromoApplyPayload,
    WebAppTariffChangePayload,
)
from bot.infra import events
from bot.infra.event_payloads import PaymentCanceledPayload
from db.dal import message_log_dal

from ._runtime import (
    Any,
    AsyncSession,
    Dict,
    Optional,
    Payment,
    PromoCodeService,
    Settings,
    SubscriptionService,
    datetime,
    default_currency_key_for_settings,
    default_payment_currency_code_for_settings,
    html,
    logger,
    payment_currency_code,
    payment_dal,
    prepare_config_links,
    re,
    sessionmaker,
    subscription_dal,
    timezone,
    user_dal,
    web,
)
from .common import (
    _coerce_int_or_none,
    _format_webapp_datetime,
    _hwid_devices_payment_description,
    _payment_description,
    _resolve_numeric_option_key,
    _traffic_payment_description,
)
from .serializers import (
    _serialize_tariff_change_target,
    _serialize_topup_packages,
    _traffic_percent,
)

from .billing_common import (
    _HTML_TAG_RE,
    _TRIAL_ACTIVATION_FAILURE_STATUSES,
    _billing_datetime_text,
    _billing_iso_datetime,
    _localized_webapp_message,
    _parse_positive_int_units,
    _plain_text_message,
)
from .billing_options import (
    device_topup_options_route,
    tariff_change_options_route,
    tariff_change_payment_route,
    tariff_change_route,
    tariff_topup_options_route,
)
from .billing_payments import (
    _create_subscription_payment,
    _sale_mode_base,
    _sale_mode_is_hwid_devices,
    _sale_mode_is_traffic,
    _sale_mode_tariff_key,
    create_payment_route,
)
from .billing_status import (
    _payment_status_can_be_refreshed,
    _refresh_wata_payment_status,
    _refresh_yookassa_payment_status,
    _yookassa_payment_payload_for_processing,
    payment_status_route,
)
from .billing_subscription import (
    activate_trial_route,
    apply_promo_route,
    subscription_auto_renew_route,
)
