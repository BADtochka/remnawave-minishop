"""Typed payload contracts for the in-process domain event bus.

Event models are pydantic v2 ``BaseModel`` classes with ``extra="forbid"``:
emit sites construct a model first, then publish ``model.to_payload()`` through
``events.emit``. The bus itself stays deliberately unvalidated so subscriber
failures and validation mistakes cannot change its never-raise contract.

Datetimes should be typed as ``datetime`` on concrete models and serialized via
``model_dump(mode="json")``; this keeps the wire payload as the same flat dict of
primitives and ISO-8601 strings that the existing ``events.iso`` helper emits.
Optional event keys should be declared as ``Optional[...] = None`` when the
current contract allows ``None`` for unknown values.

``model_construct`` is available for trusted internal data only after profiling
shows validation overhead on a hot path. The default is normal validation at the
emit call site, because catching drift there is the point of these contracts.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict


class EventPayload(BaseModel):
    """Base class for validated event payload models."""

    model_config = ConfigDict(extra="forbid")

    EVENT_NAME: ClassVar[str]

    def to_payload(self) -> dict[str, Any]:
        """Return the flat JSON-compatible dict passed to ``events.emit``."""
        return self.model_dump(mode="json")
