import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bot.middlewares.update_antiflood import RateLimitRule, UpdateAntiFloodMiddleware


def _settings(**overrides):
    base = {
        "REDIS_URL": None,
        "REDIS_KEY_PREFIX": "test-shop",
        "TELEGRAM_ANTIFLOOD_ENABLED": True,
        "TELEGRAM_ANTIFLOOD_WINDOW_SECONDS": 60,
        "TELEGRAM_ANTIFLOOD_MAX_UPDATES_PER_WINDOW": 180,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _message_update(*, user_id=42, chat_id=42, chat_type="private", text="hello"):
    return SimpleNamespace(
        event_type="message",
        message=SimpleNamespace(
            from_user=SimpleNamespace(id=user_id),
            chat=SimpleNamespace(id=chat_id, type=chat_type),
            text=text,
        ),
        callback_query=None,
        inline_query=None,
    )


def _callback_update(
    *,
    user_id=42,
    chat_id=42,
    chat_type="private",
    data="main_action:back_to_main",
):
    return SimpleNamespace(
        event_type="callback_query",
        message=None,
        callback_query=SimpleNamespace(
            from_user=SimpleNamespace(id=user_id),
            message=SimpleNamespace(chat=SimpleNamespace(id=chat_id, type=chat_type)),
            data=data,
            answer=AsyncMock(),
        ),
        inline_query=None,
    )


def _inline_update(*, user_id=42, query="ref"):
    return SimpleNamespace(
        event_type="inline_query",
        message=None,
        callback_query=None,
        inline_query=SimpleNamespace(from_user=SimpleNamespace(id=user_id), query=query),
    )


class UpdateAntiFloodMiddlewareTests(unittest.IsolatedAsyncioTestCase):
    async def test_extreme_update_flood_is_dropped_before_handler(self):
        middleware = UpdateAntiFloodMiddleware(
            _settings(),
            default_rule=RateLimitRule(window_seconds=60, max_events=2),
        )
        handler = AsyncMock(return_value="ok")
        event = _message_update()

        with patch("bot.middlewares.update_antiflood.get_redis", AsyncMock(return_value=None)):
            self.assertEqual(await middleware(handler, event, {}), "ok")
            self.assertEqual(await middleware(handler, event, {}), "ok")
            self.assertIsNone(await middleware(handler, event, {}))

        self.assertEqual(handler.await_count, 2)

    async def test_antiflood_can_be_disabled(self):
        middleware = UpdateAntiFloodMiddleware(
            _settings(TELEGRAM_ANTIFLOOD_ENABLED=False),
            default_rule=RateLimitRule(window_seconds=60, max_events=0),
        )
        handler = AsyncMock(return_value="ok")

        with patch("bot.middlewares.update_antiflood.get_redis", AsyncMock(return_value=None)):
            self.assertEqual(await middleware(handler, _message_update(), {}), "ok")

        handler.assert_awaited_once()

    async def test_action_specific_limits_are_counted_separately(self):
        middleware = UpdateAntiFloodMiddleware(
            _settings(),
            default_rule=RateLimitRule(window_seconds=60, max_events=100),
            action_rules={
                "start": RateLimitRule(window_seconds=60, max_events=1),
                "callback": RateLimitRule(window_seconds=60, max_events=2),
                "expensive_callback": RateLimitRule(window_seconds=60, max_events=1),
                "inline": RateLimitRule(window_seconds=60, max_events=1),
            },
        )
        handler = AsyncMock(return_value="ok")

        with patch("bot.middlewares.update_antiflood.get_redis", AsyncMock(return_value=None)):
            self.assertEqual(
                await middleware(handler, _message_update(text="/start"), {}),
                "ok",
            )
            self.assertIsNone(await middleware(handler, _message_update(text="/start abc"), {}))

            self.assertEqual(await middleware(handler, _callback_update(), {}), "ok")
            self.assertEqual(await middleware(handler, _callback_update(), {}), "ok")
            self.assertIsNone(await middleware(handler, _callback_update(), {}))

            self.assertEqual(
                await middleware(handler, _callback_update(data="pay_fk:1:100:subscription"), {}),
                "ok",
            )
            self.assertIsNone(
                await middleware(handler, _callback_update(data="pay_fk:1:100:subscription"), {})
            )

            self.assertEqual(await middleware(handler, _inline_update(), {}), "ok")
            self.assertIsNone(await middleware(handler, _inline_update(), {}))

        self.assertEqual(handler.await_count, 5)


if __name__ == "__main__":
    unittest.main()
