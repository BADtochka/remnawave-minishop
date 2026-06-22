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

from .yookassa_common import _metadata_iso
from .yookassa_service import YooKassaService

async def create_webapp_payment(ctx: WebAppPaymentContext) -> web.Response:
    service: YooKassaService = ctx.request.app["yookassa_service"]
    if not service or not service.configured:
        return payment_unavailable()
    currency = (ctx.currency or "RUB").upper()

    try:
        amounts = payment_record_amounts(
            months=ctx.months,
            sale_mode=ctx.sale_mode,
            traffic_gb=ctx.traffic_gb,
            hwid_device_count=ctx.hwid_device_count,
        )
        payment = await create_webapp_payment_record(
            ctx,
            amount=ctx.price,
            currency=currency,
            status="pending_yookassa",
            provider="yookassa",
        )
        metadata = {
            "user_id": str(ctx.user_id),
            "subscription_months": str(
                int(float(ctx.months))
                if not amounts.traffic_sale and not amounts.hwid_devices_sale
                else 0
            ),
            "payment_db_id": str(payment.payment_id),
            "sale_mode": ctx.sale_mode,
            "source": "webapp",
        }
        if amounts.traffic_sale:
            metadata["traffic_gb"] = format_number_for_payload(ctx.traffic_gb or ctx.months)
        if amounts.purchased_hwid_devices:
            metadata["hwid_devices"] = str(int(amounts.purchased_hwid_devices))
            hwid_metadata = {
                "hwid_valid_from": _metadata_iso(ctx.hwid_valid_from),
                "hwid_valid_until": _metadata_iso(ctx.hwid_valid_until),
                "hwid_pricing_period_months": ctx.hwid_pricing_period_months,
                "hwid_proration_ratio": ctx.hwid_proration_ratio,
                "hwid_full_price": ctx.hwid_full_price,
            }
            metadata.update(
                {key: str(value) for key, value in hwid_metadata.items() if value is not None}
            )
        if amounts.tariff_key:
            metadata["tariff_key"] = amounts.tariff_key
        response = await service.create_payment(
            amount=ctx.price,
            currency=currency,
            description=ctx.description,
            metadata=metadata,
            receipt_email=service.config.DEFAULT_RECEIPT_EMAIL,
            save_payment_method=False,
        )
        payment_url = response.get("confirmation_url") if response else None
        provider_payment_id = str(response.get("id") or "") if response else ""
        if not payment_url:
            logger.error(
                "YooKassa WebApp payment creation failed for payment %s "
                "(user_id=%s, has_provider_payment_id=%s, response=%s).",
                payment.payment_id,
                ctx.user_id,
                bool(provider_payment_id),
                response,
            )
            await mark_payment_failed_creation(ctx.session, payment.payment_id)
            return payment_failed()

        await payment_dal.update_payment_status_by_db_id(
            ctx.session,
            payment.payment_id,
            "pending_yookassa",
            yk_payment_id=provider_payment_id or None,
        )
        await ctx.session.commit()
        return payment_link_response(payment_url=payment_url, payment_id=payment.payment_id)
    except Exception:
        await ctx.session.rollback()
        logger.exception("YooKassa WebApp payment failed")
        return payment_failed()


async def reuse_webapp_payment(ctx: WebAppPaymentContext, payment: Any) -> Optional[str]:
    service: YooKassaService = ctx.request.app.get("yookassa_service")
    if not service or not service.configured:
        return None

    provider_payment_id = str(
        getattr(payment, "yookassa_payment_id", None)
        or getattr(payment, "provider_payment_id", None)
        or ""
    ).strip()
    if not provider_payment_id:
        return None

    info = await service.get_payment_info(provider_payment_id)
    if not info or str(info.get("status") or "").strip().lower() != "pending":
        return None
    if bool(info.get("paid")):
        return None

    metadata_raw = info.get("metadata")
    metadata = metadata_raw if isinstance(metadata_raw, dict) else {}
    expected_metadata = {
        "user_id": str(ctx.user_id),
        "payment_db_id": str(payment.payment_id),
        "sale_mode": str(ctx.sale_mode),
    }
    if any(str(metadata.get(key) or "") != value for key, value in expected_metadata.items()):
        return None
    return str(info.get("confirmation_url") or "").strip() or None
