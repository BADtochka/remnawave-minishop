from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_telegram_init_data_login_runs_before_manual_logout_gate():
    source = _read("frontend/src/lib/webapp/webappBoot.js")

    init_data_pos = source.index("const initData = getInitDataForBoot();")
    manual_logout_pos = source.index("if (isManuallyLoggedOut())")

    assert init_data_pos < manual_logout_pos


def test_logout_button_is_controlled_by_telegram_context():
    app_source = _read("frontend/src/App.svelte")
    settings_source = _read("frontend/src/webapp/screens/SettingsScreen.svelte")

    assert "$: telegramMiniAppContext = hasTelegramLaunchParams();" in app_source
    assert "showLogout={!telegramMiniAppContext}" in app_source
    assert "export let showLogout = true;" in settings_source
    assert "{#if showLogout}" in settings_source


def test_logout_handler_is_noop_inside_telegram_mini_app():
    source = _read("frontend/src/lib/webapp/stores/accountStore.js")

    guard_pos = source.index("if (telegramSdk.hasLaunchParams()) return;")
    mark_logout_pos = source.index("markManualLogout();")

    assert guard_pos < mark_logout_pos
