"""Apply persisted setting overrides on top of the env-based Settings.

The runtime treats DB overrides as the source of truth: env values are
loaded once via pydantic, then any matching keys from the
``app_setting_overrides`` table replace those attributes in-process.
This way the admin can flip flags, adjust prices or rename labels
without restarting the container.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import sessionmaker

from bot.app.web.admin_settings_manifest import (
    SettingField,
    coerce_value,
    get_field_by_key,
    manifest_keys,
)
from config.settings import Settings
from db.dal import app_settings_dal

logger = logging.getLogger(__name__)


def _resolve_attribute_name(settings: Settings, key: str) -> Optional[str]:
    """Resolve the actual attribute name on the Settings model.

    Some settings expose their env name via ``alias`` (e.g. MONTH_1_ENABLED is
    aliased to "1_MONTH_ENABLED"). Lookups by either alias or attribute name
    should both succeed, with the attribute name returned in either case.
    """

    if hasattr(settings, key):
        return key

    fields = type(settings).model_fields
    for attr_name, field_info in fields.items():
        alias = getattr(field_info, "alias", None)
        if alias and alias == key:
            return attr_name
    return None


def _apply_value(settings: Settings, key: str, value: Any) -> bool:
    attr_name = _resolve_attribute_name(settings, key)
    if not attr_name:
        return False
    try:
        setattr(settings, attr_name, value)
        return True
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to apply override %s=%r: %s", key, value, exc)
        return False


def apply_overrides(settings: Settings, overrides: Dict[str, Any]) -> int:
    applied = 0
    for key, raw_value in overrides.items():
        field = get_field_by_key(key)
        if not field:
            continue
        try:
            coerced = coerce_value(field, raw_value)
        except ValueError as exc:
            logger.warning("Skipping override %s: %s", key, exc)
            continue
        if _apply_value(settings, key, coerced):
            applied += 1
    return applied


async def load_overrides_from_db(settings: Settings, async_session_factory: sessionmaker) -> int:
    """Fetch overrides from the DB and apply them to the in-memory settings."""

    try:
        async with async_session_factory() as session:
            overrides = await app_settings_dal.get_all_overrides(session)
    except Exception as exc:
        logger.warning("Could not load setting overrides from DB: %s", exc)
        return 0

    applied = apply_overrides(settings, overrides)
    if applied:
        logger.info("Applied %s setting overrides from DB", applied)
    return applied


async def update_overrides(
    settings: Settings,
    async_session_factory: sessionmaker,
    *,
    updates: Dict[str, Any],
    deletes: Optional[list] = None,
    actor_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Persist + apply a batch of changes coming from the admin UI."""

    deletes = list(deletes or [])
    coerced_updates: Dict[str, Any] = {}
    errors: Dict[str, str] = {}

    for key, raw in updates.items():
        field: Optional[SettingField] = get_field_by_key(key)
        if not field:
            errors[key] = "unknown_setting"
            continue
        try:
            coerced_updates[key] = coerce_value(field, raw)
        except ValueError as exc:
            errors[key] = str(exc)

    valid_deletes = []
    for key in deletes:
        if get_field_by_key(key) is None:
            errors.setdefault(key, "unknown_setting")
            continue
        valid_deletes.append(key)

    if errors:
        return {"ok": False, "errors": errors}

    async with async_session_factory() as session:  # type: AsyncSession
        async with session.begin():
            for key, value in coerced_updates.items():
                await app_settings_dal.upsert_override(
                    session, key=key, value=value, updated_by=actor_id
                )
            for key in valid_deletes:
                await app_settings_dal.delete_override(session, key)

    # Apply locally; deletes need an env-default fallback. We re-read the env
    # default by instantiating a fresh Settings() (cheap; just a few ms) and
    # copying the matching attributes back over.
    if valid_deletes:
        try:
            env_only = Settings()
            for key in valid_deletes:
                attr_name = _resolve_attribute_name(env_only, key) or key
                if hasattr(env_only, attr_name):
                    setattr(settings, attr_name, getattr(env_only, attr_name))
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to restore env defaults: %s", exc)

    apply_overrides(settings, coerced_updates)

    return {"ok": True, "applied": len(coerced_updates), "reverted": len(valid_deletes)}


def overridable_keys() -> list:
    return list(manifest_keys())


def current_value(settings: Settings, key: str) -> Any:
    attr_name = _resolve_attribute_name(settings, key)
    if not attr_name:
        return None
    return getattr(settings, attr_name, None)
