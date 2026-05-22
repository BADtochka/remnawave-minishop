import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bot.app.web.webapp.auth import (
    _link_telegram_to_user,
    _sync_merged_panel_identity_for_user,
)


class AccountLinkingPanelTests(unittest.IsolatedAsyncioTestCase):
    async def test_merged_panel_identity_deletes_source_before_updating_target(self):
        calls = []

        async def delete_source(*args, **kwargs):
            calls.append("delete")
            return True

        async def update_target(*args, **kwargs):
            calls.append("update")
            return {"uuid": "panel-target"}

        panel_service = SimpleNamespace(
            delete_user_from_panel=AsyncMock(side_effect=delete_source),
            update_user_details_on_panel=AsyncMock(side_effect=update_target),
        )
        request = SimpleNamespace(
            app={"subscription_service": SimpleNamespace(panel_service=panel_service)}
        )
        user = SimpleNamespace(
            user_id=42,
            panel_user_uuid="panel-target",
            telegram_id=42,
            email="linked@example.com",
            username="alice",
            first_name="Alice",
            last_name=None,
        )

        result = await _sync_merged_panel_identity_for_user(
            request,
            user,
            source_panel_uuid="panel-source",
            final_panel_uuid="panel-target",
        )

        self.assertTrue(result)
        self.assertEqual(calls, ["delete", "update"])
        panel_service.delete_user_from_panel.assert_awaited_once_with(
            "panel-source",
            log_response=False,
        )
        panel_service.update_user_details_on_panel.assert_awaited_once()
        update_uuid, payload = panel_service.update_user_details_on_panel.await_args.args[:2]
        self.assertEqual(update_uuid, "panel-target")
        self.assertEqual(payload["email"], "linked@example.com")
        self.assertEqual(payload["telegramId"], 42)

    async def test_telegram_merge_defers_panel_sync_until_source_cleanup(self):
        current_user = SimpleNamespace(
            user_id=-100,
            email="linked@example.com",
            email_verified_at=None,
            panel_user_uuid="panel-source",
            telegram_id=None,
            username=None,
            first_name=None,
            last_name=None,
            language_code="ru",
            telegram_photo_url=None,
        )
        existing_telegram_user = SimpleNamespace(
            user_id=42,
            email=None,
            email_verified_at=None,
            panel_user_uuid="panel-target",
            telegram_id=42,
            username="old",
            first_name=None,
            last_name=None,
            language_code="ru",
            telegram_photo_url=None,
        )
        merged_user = SimpleNamespace(
            user_id=42,
            email="linked@example.com",
            email_verified_at=None,
            panel_user_uuid="panel-target",
            telegram_id=42,
            username="old",
            first_name=None,
            last_name=None,
            language_code="ru",
            telegram_photo_url=None,
        )
        panel_service = SimpleNamespace(update_user_details_on_panel=AsyncMock())
        request = SimpleNamespace(
            app={"subscription_service": SimpleNamespace(panel_service=panel_service)}
        )
        session = SimpleNamespace(flush=AsyncMock())
        telegram_user = {
            "id": 42,
            "username": "alice",
            "first_name": "Alice",
            "last_name": "",
            "language_code": "ru",
        }

        with (
            patch(
                "bot.app.web.webapp.auth.user_dal.get_user_by_id",
                AsyncMock(return_value=current_user),
            ),
            patch(
                "bot.app.web.webapp.auth.user_dal.get_user_by_telegram_id",
                AsyncMock(return_value=existing_telegram_user),
            ),
            patch(
                "bot.app.web.webapp.auth.user_dal.merge_users",
                AsyncMock(return_value=merged_user),
            ),
        ):
            result = await _link_telegram_to_user(
                request,
                session,
                current_user_id=-100,
                telegram_user=telegram_user,
                settings=SimpleNamespace(DEFAULT_LANGUAGE="ru"),
            )

        self.assertIs(result, merged_user)
        panel_service.update_user_details_on_panel.assert_not_awaited()
        self.assertEqual(merged_user.username, "alice")
