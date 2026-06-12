"""Tests for the plugin discovery loader and its core hook points."""

from __future__ import annotations

import pytest
from aiogram import Router
from aiohttp import web

from bot.plugins import (
    WEB_SCOPE_WEBAPP,
    WEB_SCOPE_WEBHOOKS,
    Plugin,
    PluginContext,
    get_plugins,
    register,
    reset_plugins,
    run_setup,
    setup_web_plugins,
)
from bot.plugins import loader as plugins_loader
from bot.routers import build_root_router
from config.settings import Settings


@pytest.fixture(autouse=True)
def _clean_plugin_state():
    reset_plugins()
    yield
    reset_plugins()


@pytest.fixture
def fresh_core_routers(monkeypatch):
    """Replace module-level router aggregates so build_root_router can run
    more than once per process (aiogram forbids re-attaching a router)."""
    import bot.routers as routers_mod

    monkeypatch.setattr(routers_mod, "user_router_aggregate", Router(name="user_agg_stub"))
    monkeypatch.setattr(routers_mod, "admin_router_aggregate", Router(name="admin_agg_stub"))
    monkeypatch.setattr(routers_mod.inline_mode, "router", Router(name="inline_stub"))


def make_settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "BOT_TOKEN": "x",
        "POSTGRES_USER": "u",
        "POSTGRES_PASSWORD": "p",
        "ADMIN_IDS": "1",
    }
    values.update(overrides)
    return Settings(**values)


class RecordingPlugin(Plugin):
    name = "recording"
    version = "1.0.0"

    def __init__(self):
        self.calls = []
        self.user_router = Router(name="recording_user")
        self.admin_router = Router(name="recording_admin")

    def setup(self, ctx):
        self.calls.append(("setup", ctx))

    def setup_bot(self, ctx, *, user_root, admin_root):
        self.calls.append(("setup_bot", user_root, admin_root))
        user_root.include_router(self.user_router)
        admin_root.include_router(self.admin_router)

    def setup_web(self, ctx, app, *, scope):
        self.calls.append(("setup_web", scope))
        app.router.add_get(f"/recording/{scope}", self._handler)

    async def _handler(self, request):
        return web.json_response({"ok": True})


class FailingPlugin(Plugin):
    name = "failing"

    def setup(self, ctx):
        raise RuntimeError("boom")

    def setup_bot(self, ctx, *, user_root, admin_root):
        raise RuntimeError("boom")

    def setup_web(self, ctx, app, *, scope):
        raise RuntimeError("boom")


def test_no_plugins_by_default(caplog):
    settings = make_settings()
    with caplog.at_level("INFO"):
        assert get_plugins(settings) == []
    assert "Plugins: none" in caplog.text


def test_plugins_disabled_via_settings():
    register(RecordingPlugin())
    settings = make_settings(PLUGINS_ENABLED=False)
    assert get_plugins(settings) == []


def test_setup_hook_runs_for_registered_plugins():
    plugin = RecordingPlugin()
    register(plugin)
    ctx = PluginContext(settings=make_settings())
    run_setup(ctx)
    assert plugin.calls == [("setup", ctx)]


def test_build_root_router_invokes_setup_bot_and_includes_routers(fresh_core_routers):
    plugin = RecordingPlugin()
    register(plugin)
    settings = make_settings()
    ctx = PluginContext(settings=settings)

    root = build_root_router(settings, ctx)

    assert plugin.calls and plugin.calls[0][0] == "setup_bot"
    _, user_root, admin_root = plugin.calls[0]
    assert user_root is root
    assert admin_root.name == "admin_main_filtered_router"
    assert plugin.user_router in root.sub_routers
    assert plugin.admin_router in admin_root.sub_routers


def test_build_root_router_without_context_skips_plugins(fresh_core_routers):
    plugin = RecordingPlugin()
    register(plugin)

    root = build_root_router(make_settings())

    assert plugin.calls == []
    assert plugin.user_router not in root.sub_routers


def test_setup_web_registers_routes_per_scope():
    plugin = RecordingPlugin()
    register(plugin)
    ctx = PluginContext(settings=make_settings())

    for scope in (WEB_SCOPE_WEBHOOKS, WEB_SCOPE_WEBAPP):
        app = web.Application()
        setup_web_plugins(ctx, app, scope=scope)
        paths = {resource.canonical for resource in app.router.resources()}
        assert f"/recording/{scope}" in paths

    assert [call for call in plugin.calls if call[0] == "setup_web"] == [
        ("setup_web", WEB_SCOPE_WEBHOOKS),
        ("setup_web", WEB_SCOPE_WEBAPP),
    ]


def test_failing_plugin_is_isolated(caplog):
    failing = FailingPlugin()
    recording = RecordingPlugin()
    register(failing)
    register(recording)
    ctx = PluginContext(settings=make_settings())

    with caplog.at_level("ERROR"):
        run_setup(ctx)

    assert recording.calls == [("setup", ctx)]
    assert "Plugin 'failing' failed in setup" in caplog.text


def test_failing_plugin_is_fatal_in_strict_mode():
    register(FailingPlugin())
    ctx = PluginContext(settings=make_settings(PLUGINS_STRICT=True))

    with pytest.raises(RuntimeError, match="boom"):
        run_setup(ctx)


class _FakeEntryPoint:
    name = "fake"

    def __init__(self, target):
        self._target = target

    def load(self):
        return self._target


def test_entry_point_discovery_accepts_class(monkeypatch):
    monkeypatch.setattr(
        plugins_loader.metadata,
        "entry_points",
        lambda group: [_FakeEntryPoint(RecordingPlugin)],
    )
    plugins = get_plugins(make_settings())
    assert len(plugins) == 1
    assert plugins[0].name == "recording"


def test_entry_point_discovery_rejects_non_plugin(monkeypatch, caplog):
    monkeypatch.setattr(
        plugins_loader.metadata,
        "entry_points",
        lambda group: [_FakeEntryPoint(object())],
    )
    with caplog.at_level("ERROR"):
        assert get_plugins(make_settings()) == []
    assert "Failed to load plugin from entry point" in caplog.text


def test_entry_point_discovery_rejects_non_plugin_strict(monkeypatch):
    monkeypatch.setattr(
        plugins_loader.metadata,
        "entry_points",
        lambda group: [_FakeEntryPoint(object())],
    )
    with pytest.raises(TypeError):
        get_plugins(make_settings(PLUGINS_STRICT=True))
