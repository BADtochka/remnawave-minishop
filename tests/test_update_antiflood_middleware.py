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


if __name__ == "__main__":
    unittest.main()
