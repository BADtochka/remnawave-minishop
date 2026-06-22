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

from .yookassa_service import YooKassaService
from .yookassa_success import (
    YOOKASSA_EVENT_PAYMENT_CANCELED,
    YOOKASSA_EVENT_PAYMENT_SUCCEEDED,
    YOOKASSA_EVENT_PAYMENT_WAITING_FOR_CAPTURE,
    YOOKASSA_WEBHOOK_ALLOWED_IPS,
    emit_yookassa_success_events,
    payment_processing_lock,
    process_cancelled_payment,
    process_successful_payment,
)

async def yookassa_webhook_route(request: web.Request):

    try:
        bot: Bot = request.app["bot"]
        i18n_instance: JsonI18n = request.app["i18n"]
        settings: Settings = request.app["settings"]
        panel_service: PanelApiService = request.app["panel_service"]
        subscription_service: SubscriptionService = request.app["subscription_service"]
        referral_service: ReferralService = request.app["referral_service"]
        lknpd_service: Optional[LknpdService] = request.app.get("lknpd_service")
        async_session_factory: sessionmaker = request.app["async_session_factory"]
    except KeyError:
        logging.exception("KeyError accessing app context in yookassa_webhook_route.")
        return web.Response(status=500, text="Internal Server Error: Missing app context component")

    client_ip = request_client_ip(request, trusted_proxies=settings.trusted_proxies)
    if not ip_in_allowlist(client_ip, YOOKASSA_WEBHOOK_ALLOWED_IPS):
        logging.warning(
            "YooKassa webhook denied from unauthorized IP source "
            "(client_ip=%s remote=%s x_forwarded_for=%s trusted_ips=%s trusted_proxies=%s).",
            client_ip,
            request.remote,
            request.headers.get("X-Forwarded-For"),
            YOOKASSA_WEBHOOK_ALLOWED_IPS,
            settings.trusted_proxies,
        )
        return web.Response(status=403)

    try:
        event_json = await request.json()

        notification_object = WebhookNotification(event_json)
        payment_data_from_notification = notification_object.object

        logging.info(
            f"YooKassa Webhook Parsed: Event='{notification_object.event}', "
            f"PaymentId='{payment_data_from_notification.id}', Status='{payment_data_from_notification.status}'"  # noqa: E501
        )

        if (
            not payment_data_from_notification
            or not hasattr(payment_data_from_notification, "metadata")
            or payment_data_from_notification.metadata is None
        ):
            logging.error(
                f"YooKassa webhook payment {payment_data_from_notification.id} lacks metadata. Cannot process."  # noqa: E501
            )
            return web.Response(status=200, text="ok_error_no_metadata")

        # Safely extract payment_method details (SDK objects may not have to_dict)
        pm_obj = getattr(payment_data_from_notification, "payment_method", None)
        pm_dict = None
        if pm_obj is not None:
            try:
                card_obj = getattr(pm_obj, "card", None)
                pm_dict = {
                    "id": getattr(pm_obj, "id", None),
                    "type": getattr(pm_obj, "type", None),
                    "saved": bool(getattr(pm_obj, "saved", False)),
                    "title": getattr(pm_obj, "title", None),
                    "account_number": (
                        getattr(pm_obj, "account_number", None)
                        if hasattr(pm_obj, "account_number")
                        else (
                            getattr(pm_obj, "account", None) if hasattr(pm_obj, "account") else None
                        )
                    ),
                    "card": (
                        {
                            "first6": getattr(card_obj, "first6", None),
                            "last4": getattr(card_obj, "last4", None),
                            "expiry_month": getattr(card_obj, "expiry_month", None),
                            "expiry_year": getattr(card_obj, "expiry_year", None),
                            "card_type": getattr(card_obj, "card_type", None),
                        }
                        if card_obj is not None
                        else None
                    ),
                }
            except Exception:
                logging.exception("Failed to serialize YooKassa payment_method from webhook")
                pm_dict = None

        payment_dict_for_processing: Dict[str, Any] = {
            "id": str(payment_data_from_notification.id),
            "status": str(payment_data_from_notification.status),
            "paid": bool(payment_data_from_notification.paid),
            "amount": {
                "value": str(payment_data_from_notification.amount.value),
                "currency": str(payment_data_from_notification.amount.currency),
            }
            if payment_data_from_notification.amount
            else {},
            "metadata": dict(payment_data_from_notification.metadata),
            "description": str(payment_data_from_notification.description)
            if payment_data_from_notification.description
            else None,
            "payment_method": pm_dict,
        }

        if notification_object.event in {
            YOOKASSA_EVENT_PAYMENT_SUCCEEDED,
            YOOKASSA_EVENT_PAYMENT_CANCELED,
        }:
            queued = await enqueue_webhook_event(
                settings,
                "yookassa",
                {
                    "event": notification_object.event,
                    "payment": payment_dict_for_processing,
                },
                event_id=f"{notification_object.event}:{payment_dict_for_processing.get('id')}",
            )
            if queued:
                return web.Response(status=200, text="queued")

        async with payment_processing_lock:
            async with async_session_factory() as session:
                try:
                    if notification_object.event == YOOKASSA_EVENT_PAYMENT_SUCCEEDED:
                        if (
                            payment_dict_for_processing.get("paid")
                            and payment_dict_for_processing.get("status") == "succeeded"
                        ):
                            event_payload = await process_successful_payment(
                                session,
                                bot,
                                payment_dict_for_processing,
                                i18n_instance,
                                settings,
                                panel_service,
                                subscription_service,
                                referral_service,
                                lknpd_service,
                            )
                            await session.commit()
                            if event_payload:
                                await emit_yookassa_success_events(event_payload)
                        else:
                            logging.warning(
                                f"Payment Succeeded event for {payment_dict_for_processing.get('id')} "  # noqa: E501
                                f"but data not as expected: status='{payment_dict_for_processing.get('status')}', "  # noqa: E501
                                f"paid='{payment_dict_for_processing.get('paid')}'"
                            )
                    elif notification_object.event == YOOKASSA_EVENT_PAYMENT_CANCELED:
                        event_payload = await process_cancelled_payment(
                            session, bot, payment_dict_for_processing, i18n_instance, settings
                        )
                        await session.commit()
                        if event_payload:
                            await events.emit_model(
                                PaymentCanceledPayload.model_validate(event_payload),
                                exclude_unset=True,
                            )
                    elif notification_object.event == YOOKASSA_EVENT_PAYMENT_WAITING_FOR_CAPTURE:
                        # Bind-only flow: save method and cancel auth if metadata has bind_only
                        metadata_raw = payment_dict_for_processing.get("metadata")
                        metadata = metadata_raw if isinstance(metadata_raw, dict) else {}
                        if (
                            settings.yookassa_autopayments_active
                            and metadata.get("bind_only") == "1"
                        ):
                            try:
                                user_id_str = metadata.get("user_id")
                                if user_id_str and user_id_str.isdigit():
                                    user_id = int(user_id_str)
                                    payment_method = payment_dict_for_processing.get(
                                        "payment_method"
                                    )
                                    if isinstance(payment_method, dict) and payment_method.get(
                                        "id"
                                    ):
                                        pm_type = payment_method.get("type")
                                        title = payment_method.get("title")
                                        card_raw = payment_method.get("card")
                                        card = card_raw if isinstance(card_raw, dict) else {}
                                        account_number = payment_method.get(
                                            "account_number"
                                        ) or payment_method.get("account")
                                        display_network = None
                                        display_last4 = None
                                        if (pm_type or "").lower() in {
                                            "bank_card",
                                            "bank-card",
                                            "card",
                                        }:
                                            display_network = (
                                                card.get("card_type") or title or "Card"
                                            )
                                            display_last4 = card.get("last4")
                                        elif (pm_type or "").lower() in {
                                            "yoo_money",
                                            "yoomoney",
                                            "yoo-money",
                                            "wallet",
                                        }:
                                            # Normalize wallet display name to avoid leaking full account from title  # noqa: E501
                                            display_network = "YooMoney"
                                            if (
                                                isinstance(account_number, str)
                                                and len(account_number) >= 4
                                            ):
                                                display_last4 = account_number[-4:]
                                            else:
                                                display_last4 = None
                                        else:
                                            display_network = title or (
                                                pm_type.upper() if pm_type else "Payment method"
                                            )
                                            display_last4 = None
                                        await user_billing_dal.upsert_yk_payment_method(
                                            session,
                                            user_id=user_id,
                                            payment_method_id=payment_method.get("id"),
                                            card_last4=display_last4,
                                            card_network=display_network,
                                        )
                                        await session.commit()
                                        # Save multi-card entry and mark default if first
                                        try:
                                            from db.dal import user_billing_dal as ub

                                            await ub.upsert_user_payment_method(
                                                session,
                                                user_id=user_id,
                                                provider_payment_method_id=payment_method.get("id"),
                                                provider="yookassa",
                                                card_last4=display_last4,
                                                card_network=display_network,
                                                set_default=True,
                                            )
                                            await session.commit()
                                        except Exception:
                                            await session.rollback()
                                        # Notify user about successful binding with Back button
                                        try:
                                            # Use user's DB language for bind success notification
                                            i18n_lang = settings.DEFAULT_LANGUAGE
                                            from db.dal import user_dal

                                            db_user = await user_dal.get_user_by_id(
                                                session, user_id
                                            )
                                            if db_user and db_user.language_code:
                                                i18n_lang = db_user.language_code
                                            _ = lambda key, **kwargs: i18n_instance.gettext(
                                                i18n_lang, key, **kwargs
                                            )
                                            from bot.keyboards.inline.user_keyboards import (
                                                get_back_to_payment_methods_keyboard,
                                            )

                                            message_text = _("payment_method_bound_success")
                                            try:
                                                await bot.send_message(
                                                    chat_id=user_id,
                                                    text=message_text,
                                                    reply_markup=get_back_to_payment_methods_keyboard(
                                                        i18n_lang, i18n_instance
                                                    ),
                                                )
                                            except Exception:
                                                logging.exception(
                                                    "Failed to notify user %s "
                                                    "about payment method binding.",
                                                    user_id,
                                                )
                                            if db_user:
                                                await send_user_notification_email(
                                                    settings=settings,
                                                    i18n=i18n_instance,
                                                    user=db_user,
                                                    subject_key="email_payment_method_bound_subject",
                                                    message_text=message_text,
                                                    dashboard_url=(
                                                        settings.SUBSCRIPTION_MINI_APP_URL or None
                                                    ),
                                                )
                                        except Exception:
                                            pass
                                        # Attempt to cancel the authorization to avoid charge hold
                                        try:
                                            yk: YooKassaService = request.app.get(
                                                "yookassa_service"
                                            )
                                            payment_id_to_cancel = str(
                                                payment_dict_for_processing.get("id") or ""
                                            )
                                            if yk and payment_id_to_cancel:
                                                await yk.cancel_payment(payment_id_to_cancel)
                                        except Exception:
                                            logging.exception(
                                                "Failed to cancel bind-only payment auth"
                                            )
                            except Exception:
                                logging.exception(
                                    "Failed to handle bind-only waiting_for_capture webhook"
                                )
                except Exception:
                    await session.rollback()
                    logging.exception(
                        "Error processing YooKassa webhook event '%s' for YK Payment ID %s in DB transaction.",  # noqa: E501
                        notification_object.event,
                        payment_dict_for_processing.get("id"),
                    )
                    return web.Response(status=500, text="internal_processing_error")

        return web.Response(status=200, text="ok")

    except json.JSONDecodeError:
        logging.error("YooKassa Webhook: Invalid JSON received.")
        return web.Response(status=400, text="bad_request_invalid_json")
    except Exception:
        logging.exception("YooKassa Webhook general processing error.")
        return web.Response(status=500, text="internal_error")
