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

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_TRIAL_ACTIVATION_FAILURE_STATUSES = {
    "trial_activation_failed_panel_link": 502,
    "trial_activation_failed_panel_update": 502,
    "trial_activation_failed_db": 500,
    "user_not_found_for_trial": 404,
}


def _plain_text_message(value: Any) -> str:
    """Strip Telegram-style HTML markup from a localized message for the web app."""
    text = _HTML_TAG_RE.sub("", str(value))
    return html.unescape(text).strip()


def _localized_webapp_message(request: web.Request, lang: str, key: str) -> str:
    i18n = request.app.get("i18n")
    if i18n and hasattr(i18n, "gettext"):
        try:
            message = str(i18n.gettext(lang, key) or "")
        except Exception:
            logger.debug("Failed to localize WebApp message key %s", key, exc_info=True)
        else:
            if message and message != key:
                return _plain_text_message(message)
    return key


def _billing_iso_datetime(value: Optional[Any]) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        normalized = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return normalized.isoformat()
    return str(value)


def _billing_datetime_text(value: Optional[Any]) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        normalized = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return normalized.strftime("%d.%m.%Y %H:%M")
    text = str(value)
    try:
        normalized = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return normalized.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return text


def _parse_positive_int_units(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not number.is_integer():
        return None
    integer = int(number)
    return integer if integer > 0 else None
