"""Discovery and invocation of application plugins.

Plugins are discovered once per process through the ``minishop.plugins``
entry point group and cached. Tests (or embedding code) can also register
plugin instances programmatically with :func:`register`.

A failing plugin never breaks the core: errors are logged and the plugin is
skipped, unless ``PLUGINS_STRICT`` is enabled, in which case the error is
re-raised so a deployment that requires the plugin fails fast.
"""

from __future__ import annotations

import logging
from importlib import metadata
from typing import TYPE_CHECKING, List, Optional

from .spec import ENTRY_POINT_GROUP, Plugin, PluginContext

if TYPE_CHECKING:
    from aiogram import Router
    from aiohttp import web

    from config.settings import Settings

logger = logging.getLogger(__name__)

_discovered_plugins: Optional[List[Plugin]] = None
_registered_plugins: List[Plugin] = []


def register(plugin: Plugin) -> None:
    """Register a plugin instance programmatically (primarily for tests)."""
    _registered_plugins.append(plugin)


def reset_plugins() -> None:
    """Drop the discovery cache and programmatic registrations (for tests)."""
    global _discovered_plugins
    _discovered_plugins = None
    _registered_plugins.clear()


def _coerce_plugin(loaded: object, entry_point_name: str) -> Plugin:
    if isinstance(loaded, type):
        loaded = loaded()
    if not isinstance(loaded, Plugin):
        raise TypeError(
            f"Entry point {entry_point_name!r} in group {ENTRY_POINT_GROUP!r} must provide "
            f"a Plugin subclass or instance, got {type(loaded).__name__}"
        )
    return loaded


def _discover(settings: "Settings") -> List[Plugin]:
    plugins: List[Plugin] = []
    try:
        entry_points = metadata.entry_points(group=ENTRY_POINT_GROUP)
    except Exception:
        logger.exception("Failed to enumerate %s entry points", ENTRY_POINT_GROUP)
        if settings.PLUGINS_STRICT:
            raise
        return plugins
    for entry_point in entry_points:
        try:
            plugins.append(_coerce_plugin(entry_point.load(), entry_point.name))
        except Exception:
            logger.exception("Failed to load plugin from entry point %r", entry_point.name)
            if settings.PLUGINS_STRICT:
                raise
    return plugins


def get_plugins(settings: "Settings") -> List[Plugin]:
    """Return active plugins: discovered via entry points plus registered ones."""
    global _discovered_plugins
    if not settings.PLUGINS_ENABLED:
        return []
    if _discovered_plugins is None:
        _discovered_plugins = _discover(settings)
        if _discovered_plugins or _registered_plugins:
            logger.info(
                "Plugins discovered: %s",
                ", ".join(
                    f"{plugin.name}=={plugin.version}"
                    for plugin in (*_discovered_plugins, *_registered_plugins)
                ),
            )
        else:
            logger.info("Plugins: none")
    return [*_discovered_plugins, *_registered_plugins]


def _run_hook(settings: "Settings", plugin: Plugin, hook_name: str, *args, **kwargs) -> None:
    try:
        getattr(plugin, hook_name)(*args, **kwargs)
    except Exception:
        logger.exception("Plugin %r failed in %s; skipping it", plugin.name, hook_name)
        if settings.PLUGINS_STRICT:
            raise


def run_setup(ctx: PluginContext) -> None:
    """Invoke the general ``setup`` hook of every plugin."""
    for plugin in get_plugins(ctx.settings):
        _run_hook(ctx.settings, plugin, "setup", ctx)


def setup_bot_plugins(ctx: PluginContext, *, user_root: "Router", admin_root: "Router") -> None:
    """Let every plugin register its aiogram routers."""
    for plugin in get_plugins(ctx.settings):
        _run_hook(
            ctx.settings,
            plugin,
            "setup_bot",
            ctx,
            user_root=user_root,
            admin_root=admin_root,
        )


def setup_web_plugins(ctx: PluginContext, app: "web.Application", *, scope: str) -> None:
    """Let every plugin register its aiohttp routes on ``app``."""
    for plugin in get_plugins(ctx.settings):
        _run_hook(ctx.settings, plugin, "setup_web", ctx, app, scope=scope)
