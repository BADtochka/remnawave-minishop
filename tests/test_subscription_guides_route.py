import asyncio
import json
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bot.app.web import subscription_webapp as guides
from config.subscription_guides_config import default_subscription_guides_config_text


class _AsyncSessionFactory:
    def __call__(self):
        return self

    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, tb):
        return False


class SubscriptionGuidesRouteTests(unittest.IsolatedAsyncioTestCase):
    def _request(self, settings, panel_service, match_info=None):
        return SimpleNamespace(
            app={
                "settings": settings,
                "async_session_factory": _AsyncSessionFactory(),
                "panel_service": panel_service,
                "subscription_guides_config_cache": {"fingerprint": None, "status": None},
                "subscription_guides_config_lock": asyncio.Lock(),
            },
            match_info=match_info or {},
            headers={"User-Agent": "Mozilla/5.0", "Host": "app.example.test"},
            host="app.example.test",
            scheme="https",
        )

    def _settings(self, **overrides):
        values = {
            "SUBSCRIPTION_GUIDES_ENABLED": True,
            "SUBSCRIPTION_PAGE_CONFIG_PANEL_ENABLED": True,
            "SUBSCRIPTION_PAGE_CONFIG_JSON_OVERRIDE_ENABLED": False,
            "SUBSCRIPTION_PAGE_CONFIG_JSON": "",
            "SUBSCRIPTION_PAGE_CONFIG_PATH": "data/subpage-config/multiapp.json",
            "SUBSCRIPTION_MINI_APP_URL": "https://app.example.test",
            "CRYPT4_ENABLED": False,
            "CRYPT4_REDIRECT_URL": "",
            "CRYPT4_LINK_CACHE_TTL_SECONDS": 3600,
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def _auth_patch(self):
        return patch.dict(
            guides.subscription_guides_route.__globals__,
            {"_require_user_id": lambda _: 42},
        )

    async def test_uses_panel_config_when_admin_json_is_empty(self):
        default_uuid = "00000000-0000-0000-0000-000000000000"
        panel_service = SimpleNamespace(
            get_subscription_page_config_list=AsyncMock(
                return_value={"configs": [{"uuid": default_uuid, "viewPosition": 1}]}
            ),
            get_subscription_page_config_by_uuid=AsyncMock(
                return_value={
                    "uuid": default_uuid,
                    "config": json.loads(default_subscription_guides_config_text()),
                }
            )
        )
        request = self._request(self._settings(), panel_service)

        with self._auth_patch():
            response = await guides.subscription_guides_route(request)

        body = json.loads(response.text)
        self.assertTrue(body["enabled"])
        self.assertEqual(body["source"], "panel")
        self.assertEqual(body["config"]["version"], "1")
        panel_service.get_subscription_page_config_list.assert_awaited_once()
        panel_service.get_subscription_page_config_by_uuid.assert_awaited_once_with(default_uuid)

    async def test_admin_json_override_takes_priority_over_panel(self):
        admin_config = json.loads(default_subscription_guides_config_text())
        panel_service = SimpleNamespace(get_subscription_page_config_by_uuid=AsyncMock())
        request = self._request(
            self._settings(
                SUBSCRIPTION_PAGE_CONFIG_JSON_OVERRIDE_ENABLED=True,
                SUBSCRIPTION_PAGE_CONFIG_JSON=json.dumps(admin_config),
            ),
            panel_service,
        )

        with self._auth_patch():
            response = await guides.subscription_guides_route(request)

        body = json.loads(response.text)
        self.assertTrue(body["enabled"])
        self.assertEqual(body["source"], "admin_json")
        panel_service.get_subscription_page_config_by_uuid.assert_not_called()

    async def test_admin_json_is_ignored_until_override_switch_is_enabled(self):
        default_uuid = "00000000-0000-0000-0000-000000000000"
        admin_config = json.loads(default_subscription_guides_config_text())
        panel_service = SimpleNamespace(
            get_subscription_page_config_list=AsyncMock(
                return_value={"configs": [{"uuid": default_uuid, "viewPosition": 1}]}
            ),
            get_subscription_page_config_by_uuid=AsyncMock(
                return_value={
                    "uuid": default_uuid,
                    "config": json.loads(default_subscription_guides_config_text()),
                }
            )
        )
        request = self._request(
            self._settings(SUBSCRIPTION_PAGE_CONFIG_JSON=json.dumps(admin_config)),
            panel_service,
        )

        with self._auth_patch():
            response = await guides.subscription_guides_route(request)

        body = json.loads(response.text)
        self.assertTrue(body["enabled"])
        self.assertEqual(body["source"], "panel")
        panel_service.get_subscription_page_config_by_uuid.assert_awaited_once_with(default_uuid)

    async def test_panel_config_is_cached_for_multiple_users(self):
        default_uuid = "00000000-0000-0000-0000-000000000000"
        panel_config = json.loads(default_subscription_guides_config_text())
        panel_config["platforms"]["windows"]["apps"][0]["name"] = "Throne"
        panel_service = SimpleNamespace(
            get_subscription_page_config_list=AsyncMock(
                return_value={"configs": [{"uuid": default_uuid, "viewPosition": 1}]}
            ),
            get_subscription_page_config_by_uuid=AsyncMock(
                return_value={"uuid": default_uuid, "config": panel_config}
            ),
        )
        request = self._request(self._settings(), panel_service)

        with self._auth_patch():
            response = await guides.subscription_guides_route(request)
            second_response = await guides.subscription_guides_route(request)

        body = json.loads(response.text)
        second_body = json.loads(second_response.text)
        self.assertTrue(body["enabled"])
        self.assertTrue(second_body["enabled"])
        self.assertEqual(body["source"], "panel")
        self.assertEqual(body["config"]["version"], "1")
        self.assertIn("windows", body["config"]["platforms"])
        windows_apps = [app["name"] for app in body["config"]["platforms"]["windows"]["apps"]]
        self.assertIn("Throne", windows_apps)
        panel_service.get_subscription_page_config_list.assert_awaited_once()
        panel_service.get_subscription_page_config_by_uuid.assert_awaited_once_with(default_uuid)

    async def test_public_route_returns_shared_config_and_subscription_payload(self):
        default_uuid = "00000000-0000-0000-0000-000000000000"
        panel_config = json.loads(default_subscription_guides_config_text())
        panel_service = SimpleNamespace(
            get_subscription_page_config_list=AsyncMock(
                return_value={"configs": [{"uuid": default_uuid, "viewPosition": 1}]}
            ),
            get_subscription_page_config_by_uuid=AsyncMock(
                return_value={"uuid": default_uuid, "config": panel_config}
            ),
            get_user_by_uuid=AsyncMock(
                return_value={
                    "shortUuid": "share-short",
                    "subscriptionUrl": "https://sb.example.test/share-short",
                    "username": "demo",
                }
            ),
        )
        request = self._request(
            self._settings(SUBSCRIPTION_MINI_APP_URL="https://app.example.test/app"),
            panel_service,
            match_info={"short_uuid": "share-short"},
        )
        local_sub = SimpleNamespace(
            panel_user_uuid="panel-user",
            is_active=True,
            end_date=datetime.now(timezone.utc) + timedelta(days=3),
        )

        with patch.object(
            guides.subscription_dal,
            "get_subscription_by_panel_subscription_uuid",
            AsyncMock(return_value=local_sub),
        ):
            response = await guides.public_subscription_guides_route(request)

        body = json.loads(response.text)
        self.assertTrue(body["enabled"])
        self.assertEqual(body["subscription"]["config_link"], "https://sb.example.test/share-short")
        self.assertEqual(
            body["subscription"]["share_url"],
            "https://app.example.test/install/share/share-short",
        )
        panel_service.get_user_by_uuid.assert_awaited_once_with("panel-user")


if __name__ == "__main__":
    unittest.main()
