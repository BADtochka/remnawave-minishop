# ruff: noqa: F401,F403,F405,I001
from ._runtime import *  # noqa: F403,F405

from config.webapp_themes_config import (
    WebappThemesConfig,
    ensure_webapp_core_themes,
    resolved_webapp_themes_catalog,
    write_webapp_theme_dir,
)


async def admin_themes_get_route(request: web.Request) -> web.Response:
    _require_admin_user_id(request)
    settings: Settings = request.app["settings"]
    primary = settings.WEBAPP_PRIMARY_COLOR or "#00fe7a"
    catalog = resolved_webapp_themes_catalog(
        primary_accent=primary,
        env_default_theme=settings.WEBAPP_DEFAULT_THEME,
        theme_dir=settings.WEBAPP_THEMES_DIR,
    )

    return _ok(
        {
            "exists": Path(settings.WEBAPP_THEMES_DIR).expanduser().exists(),
            "themes_dir": str(Path(settings.WEBAPP_THEMES_DIR).expanduser()),
            "catalog": _webapp_themes_catalog_payload(catalog),
        }
    )


async def admin_themes_save_route(request: web.Request) -> web.Response:
    _require_admin_user_id(request)
    settings: Settings = request.app["settings"]
    payload = await _read_json(request)
    catalog = payload.get("catalog") if "catalog" in payload else payload
    if not isinstance(catalog, dict):
        return _error(400, "invalid_payload", "catalog must be an object")

    try:
        config = WebappThemesConfig.model_validate(catalog)
    except (ValidationError, ValueError) as exc:
        return _error(400, "invalid_webapp_themes_config", str(exc))

    config, _changed = ensure_webapp_core_themes(config, settings.WEBAPP_PRIMARY_COLOR or "#00fe7a")

    try:
        write_webapp_theme_dir(settings.WEBAPP_THEMES_DIR, config, delete_missing=True)
    except OSError as exc:
        logger.exception("Failed to write webapp themes to %s", settings.WEBAPP_THEMES_DIR)
        return _error(500, "write_failed", str(exc))

    cache = request.app.get("webapp_settings_cache")
    if isinstance(cache, dict):
        cache["ts"] = 0.0
        cache["data"] = {}

    return _ok(
        {
            "exists": True,
            "themes_dir": str(Path(settings.WEBAPP_THEMES_DIR).expanduser()),
            "catalog": _webapp_themes_catalog_payload(config),
        }
    )
