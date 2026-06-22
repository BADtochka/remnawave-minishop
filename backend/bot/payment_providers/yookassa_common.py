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

def _format_value(val: float) -> str:
    return str(int(val)) if float(val).is_integer() else f"{val:g}"


def _parse_offer_payload(payload: str) -> Optional[Tuple[float, float, str]]:
    try:
        parts = payload.split(":")
        value = float(parts[0])
        price = float(parts[1])
        sale_mode = parts[2] if len(parts) > 2 else "subscription"
        return value, price, sale_mode
    except (ValueError, IndexError):
        return None


def _parse_saved_list_payload(payload: str) -> Optional[Tuple[float, float, int, str]]:
    parts = payload.split(":")
    if len(parts) < 2:
        return None
    try:
        months = float(parts[0])
        price = float(parts[1])
    except (ValueError, IndexError):
        return None

    page = 0
    sale_mode = "subscription"
    if len(parts) > 2:
        try:
            page = int(parts[2])
            sale_mode = parts[3] if len(parts) > 3 else "subscription"
        except ValueError:
            sale_mode = parts[2]
    return months, price, page, sale_mode


def _metadata_iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def _format_saved_payment_method_title(
    get_text, network: Optional[str], last4: Optional[str], is_default: bool
) -> str:
    def _is_yoomoney_network(name: Optional[str]) -> bool:
        s = (name or "").lower()
        return "yoomoney" in s or "yoo money" in s or "yoo-money" in s

    def _extract_last4(text: str) -> Optional[str]:
        digits = "".join(ch for ch in text if ch.isdigit())
        return digits[-4:] if len(digits) >= 4 else None

    if _is_yoomoney_network(network):
        inferred_last4 = last4 or (_extract_last4(network or "") or "****")
        title = get_text("payment_method_wallet_title", last4=inferred_last4)
    elif last4:
        network_name = network or get_text("payment_network_card")
        title = get_text("payment_method_card_title", network=network_name, last4=last4)
    else:
        network_name = network or get_text("payment_network_generic")
        title = get_text("payment_method_generic_title", network=network_name)
    return f"⭐ {title}" if is_default else title
