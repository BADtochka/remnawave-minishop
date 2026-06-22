from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from aiogram import F, Router, types
from aiohttp import ClientError, web
from pydantic import Field, field_validator
from pydantic_settings import SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from bot.middlewares.i18n import JsonI18n
from bot.services.referral_service import ReferralService
from bot.services.subscription_service import SubscriptionService
from config.settings import Settings
from config.tariffs_config import (
    default_currency_key_for_settings,
    default_payment_currency_code_for_settings,
)
from db.dal import payment_dal, user_billing_dal

from .base import (
    PaymentProviderSpec,
    ProviderEnvConfig,
    ProviderManifestField,
    ServiceFactoryContext,
    WebAppPaymentContext,
    normalize_payment_currency_code,
    parse_supported_currency_codes,
    provider_env_file,
    provider_runtime_enabled,
)
from .shared import (
    PAYMENT_STATUS_PENDING_FINALIZATION,
    HttpClientMixin,
    PaymentSuccessRequest,
    RecurringChargeContext,
    RecurringChargeResult,
    build_payment_record_payload,
    create_webapp_payment_record,
    describe_payment,
    finalize_successful_payment,
    finalize_webapp_link_payment,
    first_value,
    lookup_payment_by_order_or_provider_id,
    make_translator,
    notify_callback_parse_error,
    notify_payment_record_failure,
    notify_service_unavailable,
    notify_user_payment_failed,
    parse_payment_callback,
    payment_failed,
    payment_record_amounts,
    payment_unavailable,
    payment_units_for_activation,
    quote_hwid_callback_parts,
    render_link_or_fail,
    render_payment_link,
    safe_callback_answer,
    sale_mode_base,
)

from .stripe_callbacks import pay_stripe_callback_handler
from .stripe_core import (
    StripeConfig,
    StripePresentation,
    _decode_saved_method,
    _encode_saved_method,
    _metadata_pairs,
    _stripe_amount_to_minor_units,
    _stripe_json_success,
)
from .stripe_payments import create_webapp_payment, reuse_webapp_payment
from .stripe_router import router
from .stripe_service import StripeService
from .stripe_webhook import stripe_webhook_route

logger = logging.getLogger(__name__)
_LOG = "stripe"


def create_service(ctx: ServiceFactoryContext) -> StripeService:
    bundle = ctx.config_for("stripe_service")
    config = bundle.config if bundle and isinstance(bundle.config, StripeConfig) else StripeConfig()
    return StripeService(
        bot=ctx.bot,
        settings=ctx.settings,
        config=config,
        i18n=ctx.i18n,
        async_session_factory=ctx.async_session_factory,
        subscription_service=ctx.subscription_service,
        referral_service=ctx.referral_service,
        default_return_url=ctx.bot_username_for_default_return,
    )


def _supported_currencies(config: Any) -> Optional[tuple[str, ...]]:
    values = parse_supported_currency_codes(getattr(config, "SUPPORTED_CURRENCIES", None))
    return values or None


_PRESENTATION_MANIFEST = tuple(
    ProviderManifestField(
        key=key,
        type=type_,
        label=label,
        description=description,
        placeholder=placeholder,
        subsection="Stripe",
        target="presentation",
        attr=attr,
    )
    for key, type_, label, description, placeholder, attr in (
        (
            "PAYMENT_STRIPE_WEBAPP_LABEL_RU",
            "string",
            "WebApp button text (RU)",
            "Custom Russian text shown in the Web App payment method button.",
            "",
            "WEBAPP_LABEL_RU",
        ),
        (
            "PAYMENT_STRIPE_WEBAPP_LABEL_EN",
            "string",
            "WebApp button text (EN)",
            "Custom English text shown in the Web App payment method button.",
            "",
            "WEBAPP_LABEL_EN",
        ),
        (
            "PAYMENT_STRIPE_WEBAPP_ICON",
            "icon",
            "WebApp button icon",
            "Lucide icon name rendered inside the Web App payment method button.",
            "CreditCard",
            "WEBAPP_ICON",
        ),
        (
            "PAYMENT_STRIPE_TELEGRAM_LABEL_RU",
            "string",
            "Telegram button text (RU)",
            "Custom Russian text shown in Telegram bot payment buttons.",
            "",
            "TELEGRAM_LABEL_RU",
        ),
        (
            "PAYMENT_STRIPE_TELEGRAM_LABEL_EN",
            "string",
            "Telegram button text (EN)",
            "Custom English text shown in Telegram bot payment buttons.",
            "",
            "TELEGRAM_LABEL_EN",
        ),
        (
            "PAYMENT_STRIPE_TELEGRAM_EMOJI",
            "string",
            "Telegram button emoji",
            "Emoji prepended to the Telegram bot payment button when customized.",
            "",
            "TELEGRAM_EMOJI",
        ),
    )
)

_CONFIG_MANIFEST = (
    ProviderManifestField("STRIPE_ENABLED", "bool", "Enabled", subsection="Stripe", attr="ENABLED"),
    ProviderManifestField(
        "STRIPE_SECRET_KEY",
        "string",
        "Secret key",
        description="Stripe secret API key used for Checkout Sessions and PaymentIntents.",
        subsection="Stripe",
        secret=True,
        attr="SECRET_KEY",
    ),
    ProviderManifestField(
        "STRIPE_WEBHOOK_SECRET",
        "string",
        "Webhook secret",
        description="Stripe endpoint signing secret that starts with whsec_.",
        subsection="Stripe",
        secret=True,
        attr="WEBHOOK_SECRET",
    ),
    ProviderManifestField(
        "STRIPE_BASE_URL",
        "url",
        "Base URL",
        placeholder="https://api.stripe.com",
        subsection="Stripe",
        attr="BASE_URL",
    ),
    ProviderManifestField(
        "STRIPE_RETURN_URL",
        "url",
        "Return URL",
        subsection="Stripe",
        attr="RETURN_URL",
    ),
    ProviderManifestField(
        "STRIPE_CANCEL_URL",
        "url",
        "Cancel URL",
        subsection="Stripe",
        attr="CANCEL_URL",
    ),
    ProviderManifestField(
        "STRIPE_PAYMENT_METHOD_TYPES",
        "string",
        "Payment method types",
        description="Comma-separated Checkout payment method types. Default: card.",
        placeholder="card",
        subsection="Stripe",
        attr="PAYMENT_METHOD_TYPES",
    ),
    ProviderManifestField(
        "STRIPE_SUPPORTED_CURRENCIES",
        "string",
        "Supported currencies",
        description=(
            "Optional comma-separated presentment currencies allowed for this Stripe account. "
            "Empty means no local filter."
        ),
        placeholder="USD,EUR,GBP",
        subsection="Stripe",
        attr="SUPPORTED_CURRENCIES",
    ),
    ProviderManifestField(
        "STRIPE_RECURRING_ENABLED",
        "bool",
        "Recurring payments",
        description="Save Checkout payment methods for off-session PaymentIntent auto-renewal.",
        subsection="Stripe",
        attr="RECURRING_ENABLED",
    ),
    ProviderManifestField(
        "STRIPE_VERIFY_WEBHOOK_SIGNATURE",
        "bool",
        "Verify webhook signature",
        description="Verify the Stripe-Signature header using STRIPE_WEBHOOK_SECRET.",
        subsection="Stripe",
        attr="VERIFY_WEBHOOK_SIGNATURE",
    ),
    ProviderManifestField(
        "STRIPE_WEBHOOK_TOLERANCE_SECONDS",
        "int",
        "Webhook tolerance seconds",
        description="Allowed clock skew for Stripe webhook signatures.",
        subsection="Stripe",
        min=0,
        max=86400,
        attr="WEBHOOK_TOLERANCE_SECONDS",
    ),
)


SPEC = PaymentProviderSpec(
    id="stripe",
    provider_key="stripe",
    label="Stripe",
    webapp_label="Stripe",
    webapp_labels={"ru": "Stripe", "en": "Stripe"},
    webapp_icon="CreditCard",
    telegram_labels={"ru": "Stripe", "en": "Stripe"},
    emoji="",
    telegram_emoji="",
    pending_status="pending_stripe",
    enabled=lambda config: bool(getattr(config, "ENABLED", False)),
    service_key="stripe_service",
    callback_prefix="pay_stripe",
    router=router,
    create_service=create_service,
    webhook_path=lambda source: "/webhook/stripe",
    webhook_route=stripe_webhook_route,
    webhook_requires_base_url=True,
    create_webapp_payment=create_webapp_payment,
    reuse_webapp_payment=reuse_webapp_payment,
    config_class=StripeConfig,
    presentation_class=StripePresentation,
    manifest_fields=_CONFIG_MANIFEST + _PRESENTATION_MANIFEST,
    supports_recurring=True,
    supported_currencies_resolver=_supported_currencies,
    currency_support_note=(
        "Stripe supports many presentment currencies, but availability depends on the account "
        "country and enabled payment methods. Use STRIPE_SUPPORTED_CURRENCIES to restrict UI."
    ),
    currency_support_url="https://docs.stripe.com/currencies",
)
