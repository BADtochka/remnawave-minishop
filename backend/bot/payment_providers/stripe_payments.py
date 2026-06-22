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

from .stripe_service import StripeService

async def create_webapp_payment(ctx: WebAppPaymentContext) -> web.Response:
    settings: Settings = ctx.request.app["settings"]
    service: StripeService = ctx.request.app["stripe_service"]
    if not service or not service.configured:
        return payment_unavailable()

    currency = ctx.currency or settings.DEFAULT_CURRENCY_SYMBOL or "RUB"
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
            status="pending_stripe",
            provider="stripe",
        )
        success, response_data = await service.create_checkout_session(
            payment_db_id=payment.payment_id,
            user_id=ctx.user_id,
            amount=ctx.price,
            currency=currency,
            description=ctx.description,
            metadata={
                "subscription_months": str(int(float(ctx.months)))
                if sale_mode_base(ctx.sale_mode) == "subscription"
                else "0",
                "traffic_gb": str(ctx.traffic_gb or ctx.months) if amounts.traffic_sale else None,
                "hwid_devices": str(amounts.purchased_hwid_devices)
                if amounts.purchased_hwid_devices
                else None,
                "sale_mode": ctx.sale_mode,
                "source": "webapp",
            },
        )
    except Exception:
        await ctx.session.rollback()
        logging.exception("Stripe WebApp payment failed")
        return payment_failed()

    return await finalize_webapp_link_payment(
        session=ctx.session,
        payment=payment,
        api_success=success,
        payment_url=first_value(response_data, "url") if success else None,
        provider_payment_id=first_value(response_data, "id"),
        provider_response=response_data,
        log_prefix="Stripe",
    )


async def reuse_webapp_payment(ctx: WebAppPaymentContext, payment: Any) -> Optional[str]:
    service: StripeService = ctx.request.app.get("stripe_service")
    if not service or not service.configured:
        return None
    return await service.try_reuse_pending_payment(payment)
