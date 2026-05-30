import logging
from typing import Any, Optional

from bot.middlewares.i18n import JsonI18n
from bot.services.email_auth_service import EmailAuthService
from bot.services.email_templates import render_user_notification
from config.settings import Settings


def _translate(
    i18n: Optional[JsonI18n],
    language: str,
    key: Optional[str],
    fallback: str = "",
    **kwargs: Any,
) -> str:
    if not key:
        return fallback
    if not i18n:
        return fallback or key
    text = i18n.gettext(language, key, **kwargs)
    return fallback if text == key and fallback else text


async def send_user_notification_email(
    *,
    settings: Settings,
    i18n: Optional[JsonI18n],
    user: Any,
    subject_key: str,
    message_text: str,
    dashboard_url: Optional[str] = None,
    cta_label_key: str = "email_user_notification_cta",
    subject_kwargs: Optional[dict[str, Any]] = None,
    heading_key: Optional[str] = None,
    intro_key: Optional[str] = None,
) -> bool:
    if not getattr(settings, "email_auth_configured", False):
        return False
    recipient = str(getattr(user, "email", "") or "").strip()
    if not recipient:
        return False

    language = (
        str(getattr(user, "language_code", "") or "").strip()
        or getattr(settings, "DEFAULT_LANGUAGE", "ru")
        or "ru"
    )
    kwargs = subject_kwargs or {}
    subject = _translate(i18n, language, subject_key, subject_key, **kwargs)
    heading = _translate(i18n, language, heading_key, subject, **kwargs)
    intro = _translate(
        i18n,
        language,
        intro_key or "email_user_notification_intro",
        "Notification from your account.",
    )
    cta_label = _translate(
        i18n,
        language,
        cta_label_key or "email_user_notification_cta",
        "Open dashboard",
    )

    try:
        content = render_user_notification(
            settings,
            language_code=language,
            subject=subject,
            heading=heading,
            intro=intro,
            message_text=message_text,
            dashboard_url=dashboard_url,
            cta_label=cta_label,
            i18n=i18n,
        )
        await EmailAuthService(settings, i18n).send_rendered_email(
            email=recipient,
            content=content,
        )
        return True
    except Exception:
        logging.exception("Failed to send user notification email to %s.", recipient)
        return False
