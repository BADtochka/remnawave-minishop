import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bot.app.web.admin_api_impl import users as admin_users


class FakeSession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False
        self.refreshed = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def refresh(self, obj):
        self.refreshed = obj


class FakeRequest:
    def __init__(self, body, session, subscription_service):
        self.app = {
            "settings": SimpleNamespace(),
            "async_session_factory": lambda: session,
            "subscription_service": subscription_service,
        }
        self.match_info = {"user_id": "42"}
        self._body = body

    async def json(self):
        return self._body


class AdminUserHwidLimitRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_unlimited_payload_stores_zero_and_syncs_panel(self):
        session = FakeSession()
        active = SimpleNamespace(hwid_device_limit=3)
        subscription_service = SimpleNamespace(
            sync_hwid_device_limit_to_panel=AsyncMock(return_value=0)
        )
        request = FakeRequest(
            {"unlimited": True, "hwid_device_limit": 999}, session, subscription_service
        )

        with (
            patch.object(admin_users, "_require_admin_user_id", return_value=100),
            patch.object(
                admin_users.subscription_dal,
                "get_active_subscription_by_user_id",
                AsyncMock(return_value=active),
            ),
            patch.object(admin_users.message_log_dal, "create_message_log", AsyncMock()),
            patch.object(admin_users, "_invalidate_after_admin_user_mutation", AsyncMock()),
            patch.object(
                admin_users,
                "_serialize_subscription",
                return_value={"hwid_device_limit": 0},
            ),
        ):
            response = await admin_users.admin_user_hwid_device_limit_route(request)

        self.assertEqual(response.status, 200)
        self.assertEqual(json.loads(response.text)["subscription"]["hwid_device_limit"], 0)
        self.assertEqual(active.hwid_device_limit, 0)
        subscription_service.sync_hwid_device_limit_to_panel.assert_awaited_once_with(session, 42)
        self.assertTrue(session.committed)
        self.assertEqual(session.refreshed, active)

    async def test_use_default_payload_stores_null_override(self):
        session = FakeSession()
        active = SimpleNamespace(hwid_device_limit=5)
        subscription_service = SimpleNamespace(
            sync_hwid_device_limit_to_panel=AsyncMock(return_value=3)
        )
        request = FakeRequest({"use_default": True}, session, subscription_service)

        with (
            patch.object(admin_users, "_require_admin_user_id", return_value=100),
            patch.object(
                admin_users.subscription_dal,
                "get_active_subscription_by_user_id",
                AsyncMock(return_value=active),
            ),
            patch.object(admin_users.message_log_dal, "create_message_log", AsyncMock()),
            patch.object(admin_users, "_invalidate_after_admin_user_mutation", AsyncMock()),
            patch.object(
                admin_users,
                "_serialize_subscription",
                return_value={"hwid_device_limit": None},
            ),
        ):
            response = await admin_users.admin_user_hwid_device_limit_route(request)

        self.assertEqual(response.status, 200)
        self.assertIsNone(json.loads(response.text)["subscription"]["hwid_device_limit"])
        self.assertIsNone(active.hwid_device_limit)
        subscription_service.sync_hwid_device_limit_to_panel.assert_awaited_once_with(session, 42)

    async def test_negative_limit_is_rejected(self):
        session = FakeSession()
        subscription_service = SimpleNamespace(
            sync_hwid_device_limit_to_panel=AsyncMock(return_value=None)
        )
        request = FakeRequest({"hwid_device_limit": -1}, session, subscription_service)

        with patch.object(admin_users, "_require_admin_user_id", return_value=100):
            response = await admin_users.admin_user_hwid_device_limit_route(request)

        self.assertEqual(response.status, 400)
        self.assertEqual(json.loads(response.text)["error"], "invalid_hwid_device_limit")
        subscription_service.sync_hwid_device_limit_to_panel.assert_not_awaited()

    async def test_over_max_limit_is_rejected(self):
        session = FakeSession()
        subscription_service = SimpleNamespace(
            sync_hwid_device_limit_to_panel=AsyncMock(return_value=None)
        )
        request = FakeRequest({"hwid_device_limit": 1_000_001}, session, subscription_service)

        with patch.object(admin_users, "_require_admin_user_id", return_value=100):
            response = await admin_users.admin_user_hwid_device_limit_route(request)

        self.assertEqual(response.status, 400)
        self.assertEqual(json.loads(response.text)["error"], "invalid_hwid_device_limit")
        subscription_service.sync_hwid_device_limit_to_panel.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
