# ruff: noqa: F401,F403,F405,I001
from ._runtime import *  # noqa: F403,F405
from .common import _panel_user_connection_activity

import asyncio
from collections import defaultdict


BROADCAST_TARGET_ACTIVE_NEVER_CONNECTED = "active_never_connected"
BROADCAST_TARGETS = {
    "all",
    "active",
    "inactive",
    "expired",
    "never",
    BROADCAST_TARGET_ACTIVE_NEVER_CONNECTED,
}
PANEL_ACTIVITY_LOOKUP_CONCURRENCY = 10


def _resolve_panel_service(request: web.Request) -> Any:
    subscription_service = request.app.get("subscription_service")
    return getattr(subscription_service, "panel_service", None)


async def _active_subscription_panel_uuids_by_user(
    session: AsyncSession,
) -> Dict[int, List[str]]:
    now = datetime.now(timezone.utc)
    stmt = (
        select(Subscription.user_id, Subscription.panel_user_uuid)
        .join(User, Subscription.user_id == User.user_id)
        .where(
            User.is_banned == False,
            Subscription.is_active == True,
            Subscription.end_date > now,
            Subscription.panel_user_uuid.is_not(None),
            Subscription.panel_user_uuid != "",
        )
        .order_by(Subscription.user_id.asc(), Subscription.end_date.desc())
    )
    result = await session.execute(stmt)

    grouped: Dict[int, List[str]] = defaultdict(list)
    seen: Dict[int, set[str]] = defaultdict(set)
    for user_id, panel_uuid in result.all():
        user_id_int = int(user_id)
        panel_uuid_str = str(panel_uuid or "").strip()
        if panel_uuid_str and panel_uuid_str not in seen[user_id_int]:
            grouped[user_id_int].append(panel_uuid_str)
            seen[user_id_int].add(panel_uuid_str)
    return dict(grouped)


async def _panel_connection_status(panel_service: Any, panel_uuid: str) -> str:
    try:
        panel_user = await panel_service.get_user_by_uuid(panel_uuid)
    except Exception as exc:
        logger.warning("Failed to fetch panel user activity uuid=%s: %s", panel_uuid, exc)
        return "unknown"
    activity = _panel_user_connection_activity(panel_user)
    return str(activity.get("status") or "unknown")


async def _user_ids_with_active_subscription_never_connected(
    session: AsyncSession,
    panel_service: Any,
) -> List[int]:
    panel_uuids_by_user = await _active_subscription_panel_uuids_by_user(session)
    semaphore = asyncio.Semaphore(PANEL_ACTIVITY_LOOKUP_CONCURRENCY)

    async def lookup(panel_uuid: str) -> str:
        async with semaphore:
            return await _panel_connection_status(panel_service, panel_uuid)

    user_ids: List[int] = []
    for user_id, panel_uuids in panel_uuids_by_user.items():
        statuses = await asyncio.gather(*(lookup(panel_uuid) for panel_uuid in panel_uuids))
        if statuses and all(status == "never" for status in statuses):
            user_ids.append(user_id)
    return user_ids


async def admin_broadcast_route(request: web.Request) -> web.Response:
    actor_id = _require_admin_user_id(request)
    payload = await _read_json(request)
    text = str(payload.get("text") or "").strip()
    target = str(payload.get("target") or "all").strip().lower()
    if not text:
        return _error(400, "empty_text")
    if target not in BROADCAST_TARGETS:
        target = "all"

    queue_manager = get_queue_manager()
    if not queue_manager:
        return _error(503, "queue_unavailable")

    async_session_factory: sessionmaker = request.app["async_session_factory"]
    async with async_session_factory() as session:
        if target == BROADCAST_TARGET_ACTIVE_NEVER_CONNECTED:
            panel_service = _resolve_panel_service(request)
            if panel_service is None:
                return _error(503, "panel_service_unavailable")
            user_ids = await _user_ids_with_active_subscription_never_connected(
                session,
                panel_service,
            )
        elif target == "active":
            user_ids = await user_dal.get_user_ids_with_active_subscription(session)
        elif target == "inactive":
            user_ids = await user_dal.get_user_ids_without_active_subscription(session)
        elif target == "expired":
            user_ids = await user_dal.get_user_ids_with_expired_subscription(session)
        elif target == "never":
            user_ids = await user_dal.get_user_ids_without_any_subscription(session)
        else:
            user_ids = await user_dal.get_all_active_user_ids_for_broadcast(session)

        sent = 0
        failed = 0
        for uid in user_ids:
            try:
                await send_message_via_queue(
                    queue_manager,
                    int(uid),
                    MessageContent(content_type="text", text=text),
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
                sent += 1
            except Exception as exc:
                failed += 1
                logger.debug("Broadcast queue failed for %s: %s", uid, exc)

        await message_log_dal.create_message_log(
            session,
            {
                "user_id": actor_id,
                "event_type": "admin_broadcast_webapp",
                "content": f"target={target} sent={sent} failed={failed} text={text[:120]}",
                "is_admin_event": True,
            },
        )

    return _ok({"queued": sent, "failed": failed, "target": target})


async def admin_broadcast_audience_counts_route(request: web.Request) -> web.Response:
    """Return how many users each broadcast audience currently resolves to."""
    _require_admin_user_id(request)

    async_session_factory: sessionmaker = request.app["async_session_factory"]
    async with async_session_factory() as session:
        panel_service = _resolve_panel_service(request)
        counts = {
            "all": len(await user_dal.get_all_active_user_ids_for_broadcast(session)),
            "active": len(await user_dal.get_user_ids_with_active_subscription(session)),
            "inactive": len(await user_dal.get_user_ids_without_active_subscription(session)),
            "expired": len(await user_dal.get_user_ids_with_expired_subscription(session)),
            "never": len(await user_dal.get_user_ids_without_any_subscription(session)),
            BROADCAST_TARGET_ACTIVE_NEVER_CONNECTED: None,
        }
        if panel_service is not None:
            counts[BROADCAST_TARGET_ACTIVE_NEVER_CONNECTED] = len(
                await _user_ids_with_active_subscription_never_connected(
                    session,
                    panel_service,
                )
            )

    return _ok({"counts": counts})
