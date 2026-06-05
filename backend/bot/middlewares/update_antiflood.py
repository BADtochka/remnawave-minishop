import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Deque, Dict, Optional

from aiogram import BaseMiddleware
from aiogram.types import Update

from bot.infra.redis import get_redis, redis_key
from config.settings import Settings

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_SECONDS = 60
DEFAULT_MAX_UPDATES_PER_WINDOW = 180


@dataclass(frozen=True)
class RateLimitRule:
    window_seconds: int
    max_events: int


class UpdateAntiFloodMiddleware(BaseMiddleware):
    """Drop extreme update floods before DB-backed middleware runs."""

    def __init__(
        self,
        settings: Settings,
        *,
        default_rule: Optional[RateLimitRule] = None,
    ) -> None:
        super().__init__()
        self.settings = settings
        self.default_rule = default_rule or RateLimitRule(
            window_seconds=int(
                getattr(settings, "TELEGRAM_ANTIFLOOD_WINDOW_SECONDS", DEFAULT_WINDOW_SECONDS)
                or DEFAULT_WINDOW_SECONDS
            ),
            max_events=int(
                getattr(
                    settings,
                    "TELEGRAM_ANTIFLOOD_MAX_UPDATES_PER_WINDOW",
                    DEFAULT_MAX_UPDATES_PER_WINDOW,
                )
                or DEFAULT_MAX_UPDATES_PER_WINDOW
            ),
        )
        self._local_buckets: Dict[str, Deque[float]] = defaultdict(deque)
        self._local_lock = asyncio.Lock()

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        if not bool(getattr(self.settings, "TELEGRAM_ANTIFLOOD_ENABLED", True)):
            return await handler(event, data)

        actor_key = _update_actor_key(event)
        if not actor_key:
            return await handler(event, data)

        if await self._is_limited(actor_key, self.default_rule):
            logger.warning(
                "Telegram update dropped by anti-flood: actor=%s update_type=%s",
                actor_key,
                getattr(event, "event_type", "unknown"),
            )
            data["antiflood_dropped"] = True
            return None

        return await handler(event, data)

    async def _is_limited(self, actor_key: str, rule: RateLimitRule) -> bool:
        if rule.window_seconds <= 0 or rule.max_events <= 0:
            return False

        try:
            redis = await get_redis(self.settings)
            if redis is not None:
                key = redis_key(
                    self.settings,
                    "rate-limit",
                    "telegram",
                    "updates",
                    actor_key,
                )
                current = int(await redis.incr(key))
                if current == 1:
                    await redis.expire(key, rule.window_seconds)
                return current > rule.max_events
        except Exception as exc:
            logger.warning("Redis telegram anti-flood unavailable; using local fallback: %s", exc)

        return await self._is_limited_local(actor_key, rule)

    async def _is_limited_local(self, actor_key: str, rule: RateLimitRule) -> bool:
        now = time.monotonic()
        cutoff = now - rule.window_seconds
        async with self._local_lock:
            bucket = self._local_buckets[actor_key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            bucket.append(now)
            if len(bucket) > rule.max_events:
                return True
            if not bucket:
                self._local_buckets.pop(actor_key, None)
        return False


def _update_actor_key(update: Update) -> Optional[str]:
    user_id = None
    chat_id = None

    if update.message:
        user_id = update.message.from_user.id if update.message.from_user else None
        chat_id = update.message.chat.id if update.message.chat else None
    elif update.callback_query:
        user_id = update.callback_query.from_user.id if update.callback_query.from_user else None
        if update.callback_query.message and update.callback_query.message.chat:
            chat_id = update.callback_query.message.chat.id
    elif update.inline_query:
        user_id = update.inline_query.from_user.id if update.inline_query.from_user else None

    if user_id is not None:
        return f"user:{int(user_id)}"
    if chat_id is not None:
        return f"chat:{int(chat_id)}"
    return None
