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
DEFAULT_MESSAGE_MAX_PER_WINDOW = 120
DEFAULT_CALLBACK_MAX_PER_WINDOW = 240
DEFAULT_INLINE_MAX_PER_WINDOW = 60
DEFAULT_START_MAX_PER_WINDOW = 30
DEFAULT_EXPENSIVE_CALLBACK_MAX_PER_WINDOW = 60

EXPENSIVE_CALLBACK_PREFIXES = (
    "pay_",
    "trial_action:confirm_activate",
    "main_action:request_trial",
    "main_action:apply_promo",
    "main_action:bot_apply_promo",
    "tariff_change:apply:",
    "tariff_change:confirm_pay:",
    "tariff_change:pay:",
    "autorenew:confirm:",
    "disconnect_device:",
)


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
        action_rules: Optional[Dict[str, RateLimitRule]] = None,
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
        self.action_rules = action_rules or _default_action_rules(settings)
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

        action_key = _update_action_key(event)
        if await self._is_limited("updates", actor_key, self.default_rule) or (
            action_key
            and action_key in self.action_rules
            and await self._is_limited(action_key, actor_key, self.action_rules[action_key])
        ):
            logger.warning(
                "Telegram update dropped by anti-flood: actor=%s update_type=%s",
                actor_key,
                action_key or getattr(event, "event_type", "unknown"),
            )
            data["antiflood_dropped"] = True
            return None

        return await handler(event, data)

    async def _is_limited(self, bucket_name: str, actor_key: str, rule: RateLimitRule) -> bool:
        if rule.window_seconds <= 0 or rule.max_events <= 0:
            return False

        try:
            redis = await get_redis(self.settings)
            if redis is not None:
                key = redis_key(
                    self.settings,
                    "rate-limit",
                    "telegram",
                    bucket_name,
                    actor_key,
                )
                current = int(await redis.incr(key))
                if current == 1:
                    await redis.expire(key, rule.window_seconds)
                return current > rule.max_events
        except Exception as exc:
            logger.warning("Redis telegram anti-flood unavailable; using local fallback: %s", exc)

        return await self._is_limited_local(f"{bucket_name}:{actor_key}", rule)

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


def _update_action_key(update: Update) -> str:
    if update.message:
        text = update.message.text or ""
        if text.startswith("/start"):
            return "start"
        return "message"
    if update.callback_query:
        data = update.callback_query.data or ""
        if data.startswith(EXPENSIVE_CALLBACK_PREFIXES):
            return "expensive_callback"
        return "callback"
    if update.inline_query:
        return "inline"
    return "updates"


def _default_action_rules(settings: Settings) -> Dict[str, RateLimitRule]:
    window_seconds = int(
        getattr(settings, "TELEGRAM_ANTIFLOOD_WINDOW_SECONDS", DEFAULT_WINDOW_SECONDS)
        or DEFAULT_WINDOW_SECONDS
    )
    return {
        "message": RateLimitRule(
            window_seconds,
            int(
                getattr(
                    settings,
                    "TELEGRAM_ANTIFLOOD_MESSAGE_MAX_PER_WINDOW",
                    DEFAULT_MESSAGE_MAX_PER_WINDOW,
                )
                or DEFAULT_MESSAGE_MAX_PER_WINDOW
            ),
        ),
        "callback": RateLimitRule(
            window_seconds,
            int(
                getattr(
                    settings,
                    "TELEGRAM_ANTIFLOOD_CALLBACK_MAX_PER_WINDOW",
                    DEFAULT_CALLBACK_MAX_PER_WINDOW,
                )
                or DEFAULT_CALLBACK_MAX_PER_WINDOW
            ),
        ),
        "inline": RateLimitRule(
            window_seconds,
            int(
                getattr(
                    settings,
                    "TELEGRAM_ANTIFLOOD_INLINE_MAX_PER_WINDOW",
                    DEFAULT_INLINE_MAX_PER_WINDOW,
                )
                or DEFAULT_INLINE_MAX_PER_WINDOW
            ),
        ),
        "start": RateLimitRule(
            window_seconds,
            int(
                getattr(
                    settings,
                    "TELEGRAM_ANTIFLOOD_START_MAX_PER_WINDOW",
                    DEFAULT_START_MAX_PER_WINDOW,
                )
                or DEFAULT_START_MAX_PER_WINDOW
            ),
        ),
        "expensive_callback": RateLimitRule(
            window_seconds,
            int(
                getattr(
                    settings,
                    "TELEGRAM_ANTIFLOOD_EXPENSIVE_CALLBACK_MAX_PER_WINDOW",
                    DEFAULT_EXPENSIVE_CALLBACK_MAX_PER_WINDOW,
                )
                or DEFAULT_EXPENSIVE_CALLBACK_MAX_PER_WINDOW
            ),
        ),
    }
