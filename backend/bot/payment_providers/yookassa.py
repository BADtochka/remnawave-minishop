import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from aiogram import Bot, F, Router, types
from aiohttp import web
from pydantic import Field, field_validator
from pydantic_settings import SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from yookassa import Configuration
from yookassa import Payment as YooKassaPayment
from yookassa.domain.common.confirmation_type import ConfirmationType
from yookassa.domain.notification import WebhookNotification
from yookassa.domain.request.payment_request_builder import PaymentRequestBuilder

from bot.infra import events
from bot.infra.event_payloads import (
    PaymentCanceledPayload,
    PaymentSucceededPayload,
    ReferralBonusGrantedPayload,
    SubscriptionCreatedPayload,
    SubscriptionExtendedPayload,
)
from bot.infra.payment_events import build_payment_succeeded_payload
from bot.infra.webhook_queue import enqueue_webhook_event
from bot.keyboards.inline.user_keyboards import (
    get_back_to_main_menu_markup,
    get_bind_url_keyboard,
    get_payment_method_delete_confirm_keyboard,
    get_payment_method_details_keyboard,
    get_payment_methods_list_keyboard,
    get_payment_url_keyboard,
    get_yk_autopay_choice_keyboard,
    get_yk_saved_cards_keyboard,
    payment_methods_back_callback,
)
from bot.middlewares.i18n import JsonI18n
from bot.services.lknpd_service import LknpdService
from bot.services.panel_api_service import PanelApiService
from bot.services.referral_service import ReferralService
from bot.services.subscription_service import SubscriptionService
from bot.services.user_email_notifications import send_user_notification_email
from bot.utils.callback_answer import callback_message_or_none
from bot.utils.config_link import prepare_config_links
from bot.utils.install_links import ensure_user_install_guide_links
from bot.utils.request_security import ip_in_allowlist, request_client_ip
from config.settings import Settings
from config.tariffs_config import (
    default_currency_key_for_settings,
    default_payment_currency_code_for_settings,
)
from db.dal import payment_dal, user_billing_dal, user_dal
from db.models import Payment

from .base import (
    PaymentProviderSpec,
    ProviderEnvConfig,
    ProviderManifestField,
    ServiceFactoryContext,
    WebAppPaymentContext,
    normalize_payment_currency_code,
    provider_env_file,
    provider_runtime_enabled,
)
from .shared import (
    PaymentCallbackParts,
    RecurringChargeContext,
    RecurringChargeResult,
    SuccessMessage,
    append_hwid_renewal_note,
    build_success_message,
    create_webapp_payment_record,
    format_human_units,
    format_number_for_payload,
    is_traffic_sale_base,
    make_translator,
    mark_payment_failed_creation,
    parse_positive_int_units,
    payment_failed,
    payment_link_response,
    payment_record_amounts,
    payment_unavailable,
    quote_hwid_callback_parts,
    resolve_inviter_name,
    send_success_message_to_user,
)
from .shared import (
    sale_mode_base as _sale_mode_base,
)
from .shared import (
    sale_mode_tariff_key as _sale_mode_tariff_key,
)

from .yookassa_callbacks import (
    _initiate_yk_payment,
    _yookassa_available_to_callback_user,
    pay_yk_callback_handler,
    pay_yk_new_card_handler,
    pay_yk_saved_list_handler,
    pay_yk_use_saved_handler,
)
from .yookassa_common import (
    _format_saved_payment_method_title,
    _format_value,
    _metadata_iso,
    _parse_offer_payload,
    _parse_saved_list_payload,
)
from .yookassa_config import YooKassaConfig, YooKassaPresentation
from .yookassa_payment_methods import (
    payment_method_bind,
    payment_method_delete,
    payment_method_delete_confirm,
    payment_method_history,
    payment_method_view,
    payment_methods_list,
    payment_methods_manage,
)
from .yookassa_payments import create_webapp_payment, reuse_webapp_payment
from .yookassa_router import router
from .yookassa_service import YooKassaService
from .yookassa_success import (
    DEFERRED_EVENTS_KEY,
    DEFERRED_SUCCESS_MESSAGE_KEY,
    HWID_DEVICE_SALE_BASES,
    YOOKASSA_EVENT_PAYMENT_CANCELED,
    YOOKASSA_EVENT_PAYMENT_SUCCEEDED,
    YOOKASSA_EVENT_PAYMENT_WAITING_FOR_CAPTURE,
    YOOKASSA_WEBHOOK_ALLOWED_IPS,
    _is_hwid_device_sale_base,
    _metadata_datetime,
    _metadata_float,
    _metadata_int,
    _metadata_value_present,
    _resolve_yookassa_activation_amounts,
    emit_yookassa_success_events,
    payment_processing_lock,
    process_cancelled_payment,
    process_successful_payment,
)
from .yookassa_webhook import yookassa_webhook_route


logger = logging.getLogger(__name__)


def create_service(ctx: ServiceFactoryContext) -> YooKassaService:
    bundle = ctx.config_for("yookassa_service")
    config = (
        bundle.config if bundle and isinstance(bundle.config, YooKassaConfig) else YooKassaConfig()
    )
    return YooKassaService(
        shop_id=config.SHOP_ID,
        secret_key=config.SECRET_KEY,
        configured_return_url=config.RETURN_URL,
        bot_username_for_default_return=ctx.bot_username_for_default_return,
        settings_obj=ctx.settings,
        config=config,
        subscription_service=ctx.subscription_service,
    )


_PRESENTATION_MANIFEST = tuple(
    ProviderManifestField(
        key=key,
        type=type_,
        label=label,
        description=description,
        placeholder=placeholder,
        subsection="YooKassa",
        target="presentation",
        attr=attr,
    )
    for key, type_, label, description, placeholder, attr in (
        (
            "PAYMENT_YOOKASSA_WEBAPP_LABEL_RU",
            "string",
            "WebApp button text (RU)",
            "Custom Russian text shown in the Web App payment method button.",
            "",
            "WEBAPP_LABEL_RU",
        ),
        (
            "PAYMENT_YOOKASSA_WEBAPP_LABEL_EN",
            "string",
            "WebApp button text (EN)",
            "Custom English text shown in the Web App payment method button.",
            "",
            "WEBAPP_LABEL_EN",
        ),
        (
            "PAYMENT_YOOKASSA_WEBAPP_ICON",
            "icon",
            "WebApp button icon",
            "Lucide icon name rendered inside the Web App payment method button.",
            "CreditCard",
            "WEBAPP_ICON",
        ),
        (
            "PAYMENT_YOOKASSA_TELEGRAM_LABEL_RU",
            "string",
            "Telegram button text (RU)",
            "Custom Russian text shown in Telegram bot payment buttons.",
            "",
            "TELEGRAM_LABEL_RU",
        ),
        (
            "PAYMENT_YOOKASSA_TELEGRAM_LABEL_EN",
            "string",
            "Telegram button text (EN)",
            "Custom English text shown in Telegram bot payment buttons.",
            "",
            "TELEGRAM_LABEL_EN",
        ),
        (
            "PAYMENT_YOOKASSA_TELEGRAM_EMOJI",
            "string",
            "Telegram button emoji",
            "Emoji prepended to the Telegram bot payment button when customized.",
            "💳",
            "TELEGRAM_EMOJI",
        ),
    )
)

_CONFIG_MANIFEST = (
    ProviderManifestField(
        "YOOKASSA_ENABLED", "bool", "Включена", subsection="YooKassa", attr="ENABLED"
    ),
    ProviderManifestField(
        "YOOKASSA_SHOP_ID", "string", "Shop ID", subsection="YooKassa", attr="SHOP_ID"
    ),
    ProviderManifestField(
        "YOOKASSA_SECRET_KEY",
        "string",
        "Secret key",
        subsection="YooKassa",
        secret=True,
        attr="SECRET_KEY",
    ),
    ProviderManifestField(
        "YOOKASSA_RETURN_URL", "url", "Return URL", subsection="YooKassa", attr="RETURN_URL"
    ),
    ProviderManifestField(
        "YOOKASSA_DEFAULT_RECEIPT_EMAIL",
        "string",
        "Email для чека по умолчанию",
        subsection="YooKassa",
        attr="DEFAULT_RECEIPT_EMAIL",
    ),
    ProviderManifestField(
        "YOOKASSA_VAT_CODE",
        "int",
        "VAT code",
        description="1..6 в зависимости от системы налогообложения",
        subsection="YooKassa",
        min=1,
        max=6,
        attr="VAT_CODE",
    ),
    ProviderManifestField(
        "YOOKASSA_AUTOPAYMENTS_ENABLED",
        "bool",
        "Автоплатежи (recurring)",
        subsection="YooKassa",
        attr="AUTOPAYMENTS_ENABLED",
    ),
    ProviderManifestField(
        "YOOKASSA_AUTOPAYMENTS_REQUIRE_CARD_BINDING",
        "bool",
        "Принудительная привязка карты",
        subsection="YooKassa",
        attr="AUTOPAYMENTS_REQUIRE_CARD_BINDING",
    ),
)


SPEC = PaymentProviderSpec(
    id="yookassa",
    provider_key="yookassa",
    label="YooKassa",
    webapp_label="ЮKassa",
    webapp_labels={"ru": "ЮKassa", "en": "YooKassa"},
    webapp_icon="CreditCard",
    telegram_labels={"ru": "ЮKassa", "en": "YooKassa"},
    telegram_emoji="💳",
    pending_status="pending_yookassa",
    enabled=lambda config: bool(getattr(config, "ENABLED", False)),
    service_key="yookassa_service",
    callback_prefix="pay_yk",
    router=router,
    create_service=create_service,
    webhook_path=lambda source: "/webhook/yookassa",
    webhook_route=yookassa_webhook_route,
    webhook_requires_base_url=True,
    create_webapp_payment=create_webapp_payment,
    reuse_webapp_payment=reuse_webapp_payment,
    config_class=YooKassaConfig,
    presentation_class=YooKassaPresentation,
    manifest_fields=_CONFIG_MANIFEST + _PRESENTATION_MANIFEST,
    supports_recurring=True,
    supported_currencies=("RUB",),
    currency_support_note=(
        "YooKassa public payment API examples and limits are RUB-based; "
        "treat non-RUB as unsupported unless your YooKassa contract confirms otherwise."
    ),
    currency_support_url="https://yookassa.ru/developers/payment-acceptance/integration-scenarios/smart-payment",
)
