from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from bot.services.subscription_notification_worker import SubscriptionNotificationWorker


def _worker(**overrides):
    settings = SimpleNamespace(
        SUBSCRIPTION_NOTIFY_DAYS_BEFORE=3,
        SUBSCRIPTION_NOTIFY_HOURS_BEFORE=3,
        SUBSCRIPTION_NOTIFY_ON_EXPIRE=True,
        SUBSCRIPTION_NOTIFY_AFTER_EXPIRE=True,
        SUBSCRIPTION_NOTIFICATION_WORKER_TICK_SECONDS=300,
        **overrides,
    )
    return SubscriptionNotificationWorker(
        settings=settings,
        session_factory=object(),
        bot=object(),
        i18n=object(),
        panel_service=object(),
        subscription_service=object(),
    )


def _sub(end_date):
    return SimpleNamespace(end_date=end_date)


def test_stage_prefers_hour_reminder_over_day_backlog():
    now = datetime(2026, 5, 28, 12, tzinfo=timezone.utc)
    stage = _worker().stage_for_subscription(_sub(now + timedelta(hours=2, minutes=30)), now)

    assert stage.key == "before_3h"
    assert stage.message_key == "subscription_hours_notification"
    assert stage.hours_before == 3


def test_stage_uses_most_imminent_day_reminder():
    now = datetime(2026, 5, 28, 12, tzinfo=timezone.utc)
    stage = _worker().stage_for_subscription(_sub(now + timedelta(hours=23)), now)

    assert stage.key == "before_1d"
    assert stage.message_key == "subscription_24h_notification"


def test_stage_sends_expired_during_first_day_after_end():
    now = datetime(2026, 5, 28, 12, tzinfo=timezone.utc)
    stage = _worker().stage_for_subscription(_sub(now - timedelta(hours=1)), now)

    assert stage.key == "expired"
    assert stage.message_key == "subscription_expired_notification"


def test_stage_sends_yesterday_notice_only_after_first_day():
    now = datetime(2026, 5, 28, 12, tzinfo=timezone.utc)
    stage = _worker().stage_for_subscription(_sub(now - timedelta(hours=25)), now)

    assert stage.key == "expired_24h_after"
    assert stage.message_key == "subscription_expired_yesterday_notification"
