"""Request body parsing helpers for typed admin API endpoints."""

from __future__ import annotations

from typing import Optional, Type, TypeVar

from aiohttp import web
from pydantic import BaseModel, ValidationError

BodyModelT = TypeVar("BodyModelT", bound=BaseModel)


def _error(status: int, code: str, message: str = "") -> web.Response:
    return web.json_response(
        {"ok": False, "error": code, "message": message or code},
        status=status,
    )


def _validation_error_summary(exc: ValidationError) -> str:
    messages: list[str] = []
    for error in exc.errors()[:3]:
        location = ".".join(str(part) for part in error.get("loc", ()) if part != "__root__")
        detail = str(error.get("msg") or "Invalid value")
        messages.append(f"{location}: {detail}" if location else detail)
    if len(exc.errors()) > 3:
        messages.append("...")
    return "; ".join(messages) or "Invalid payload"


async def parse_body(
    request: web.Request,
    model_cls: Type[BodyModelT],
) -> tuple[Optional[BodyModelT], Optional[web.Response]]:
    """Parse and validate a JSON object body for a typed endpoint."""
    try:
        raw_payload = await request.json()
    except Exception:
        return None, _error(400, "invalid_payload", "Invalid JSON payload")

    if not isinstance(raw_payload, dict):
        return None, _error(400, "invalid_payload", "Payload must be a JSON object")

    try:
        return model_cls.model_validate(raw_payload), None
    except ValidationError as exc:
        return None, _error(400, "invalid_payload", _validation_error_summary(exc))
