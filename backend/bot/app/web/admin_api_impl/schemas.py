"""Typed HTTP contracts for admin API endpoints.

Request body models use pydantic v2 ``BaseModel`` with ``extra="ignore"`` while
the API is being migrated. That preserves compatibility with clients that send
extra fields today; individual domains can move to ``extra="forbid"`` once their
frontend contracts are fully typed.

Response models describe the inner payload objects only. Handlers still wrap
them with the existing ``{"ok": true, ...}`` envelope via ``_ok`` and must build
objects through explicit classmethods such as ``from_orm_*``. Avoid pydantic
``from_attributes`` for ORM rows: explicit scalar reads prevent accidental lazy
loads after the SQLAlchemy session scope has closed.

Template for migrated domains:
1. Add request models and parse them with ``parse_body``.
2. Add response models with explicit ``from_orm_*`` constructors.
3. Add parity tests proving the serialized JSON matches the legacy dict helper.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class HttpBodyModel(BaseModel):
    """Base class for typed request bodies during the incremental refactor."""

    model_config = ConfigDict(extra="ignore")


class HttpResponseModel(BaseModel):
    """Base class for typed response payload objects."""

    model_config = ConfigDict(extra="ignore")

    @field_serializer("*", when_used="json")
    def _serialize_response_value(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        return value


class PromoCreateBody(HttpBodyModel):
    code: str
    bonus_days: int = Field(gt=0)
    max_activations: int = Field(gt=0)
    valid_days: Any = None

    @field_validator("code", mode="before")
    @classmethod
    def _normalize_code(cls, value: Any) -> str:
        code = str(value or "").strip().upper()
        if not code:
            raise ValueError("empty_code")
        return code


class PromoUpdateBody(HttpBodyModel):
    is_active: Any = None
    bonus_days: int | None = Field(default=None, gt=0)
    max_activations: int | None = Field(default=None, gt=0)


class PromoOut(HttpResponseModel):
    id: int
    code: str
    bonus_days: int
    max_activations: int
    current_activations: int
    is_active: bool
    valid_until: datetime | None = None
    created_at: datetime | None = None
    created_by_admin_id: int | None = None

    @classmethod
    def from_orm_promo(cls, promo: Any) -> "PromoOut":
        return cls(
            id=int(promo.promo_code_id),
            code=promo.code,
            bonus_days=int(promo.bonus_days),
            max_activations=int(promo.max_activations),
            current_activations=int(promo.current_activations or 0),
            is_active=bool(promo.is_active),
            valid_until=promo.valid_until,
            created_at=promo.created_at,
            created_by_admin_id=int(promo.created_by_admin_id)
            if promo.created_by_admin_id
            else None,
        )
