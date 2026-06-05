import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from bot.app.web.admin_api_impl import broadcast as broadcast_module
from bot.app.web.admin_api_impl import common as common_module


class FakeResult:
    def __init__(self, rows=None):
        self._rows = rows or []

    def all(self):
        return self._rows


class AdminPanelActivityTests(unittest.IsolatedAsyncioTestCase):
    def test_panel_activity_detects_connected_and_never_connected_users(self):
        self.assertEqual(
            common_module._panel_user_connection_activity(
                {"onlineAt": "2026-06-05T12:00:00Z"}
            ),
            {
                "status": "connected",
                "last_connected_at": "2026-06-05T12:00:00+00:00",
            },
        )
        self.assertEqual(
            common_module._panel_user_connection_activity(
                {
                    "onlineAt": None,
                    "firstConnectedAt": None,
                    "lastConnectedNode": None,
                    "userTraffic": {"lifetimeUsedTrafficBytes": 0},
                }
            ),
            {"status": "never", "last_connected_at": None},
        )
        self.assertEqual(
            common_module._panel_user_connection_activity(
                {"userTraffic": {"lifetimeUsedTrafficBytes": 1024}}
            ),
            {"status": "connected", "last_connected_at": None},
        )

    async def test_active_never_connected_audience_uses_panel_status(self):
        session = SimpleNamespace(
            execute=AsyncMock(
                return_value=FakeResult(
                    [
                        (1, "never-panel"),
                        (2, "connected-panel"),
                        (3, "missing-panel"),
                        (4, "also-never-panel"),
                        (4, "also-connected-panel"),
                    ]
                )
            )
        )

        async def get_user_by_uuid(panel_uuid):
            return {
                "never-panel": {
                    "onlineAt": None,
                    "firstConnectedAt": None,
                    "lastConnectedNode": None,
                },
                "connected-panel": {"onlineAt": "2026-06-05T12:00:00Z"},
                "also-never-panel": {
                    "onlineAt": None,
                    "firstConnectedAt": None,
                    "lastConnectedNode": None,
                },
                "also-connected-panel": {
                    "userTraffic": {"lifetimeUsedTrafficBytes": 1},
                },
            }.get(panel_uuid)

        panel_service = SimpleNamespace(get_user_by_uuid=AsyncMock(side_effect=get_user_by_uuid))

        result = await broadcast_module._user_ids_with_active_subscription_never_connected(
            session,
            panel_service,
        )

        self.assertEqual(result, [1])
        self.assertEqual(
            [call.args[0] for call in panel_service.get_user_by_uuid.await_args_list],
            [
                "never-panel",
                "connected-panel",
                "missing-panel",
                "also-never-panel",
                "also-connected-panel",
            ],
        )


if __name__ == "__main__":
    unittest.main()
