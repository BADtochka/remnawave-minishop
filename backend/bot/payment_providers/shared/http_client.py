from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from aiohttp import ClientError, ClientSession, ClientTimeout, TCPConnector, TraceConfig

SuccessCheck = Callable[[int, Any], bool]
_TRANSPORT_ATTEMPTS = 2
_PAYMENT_REQUEST_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


def http_ok(status: int, _body: Any) -> bool:
    """Default success criterion — HTTP 200 with any body."""
    return status == 200


def _trace_request_ctx(trace_config_ctx: Any) -> Optional[dict]:
    ctx = getattr(trace_config_ctx, "trace_request_ctx", None)
    return ctx if isinstance(ctx, dict) else None


async def _mark_request_headers_sent(session, trace_config_ctx, params) -> None:
    ctx = _trace_request_ctx(trace_config_ctx)
    if ctx is not None:
        ctx["headers_sent"] = True


def _payment_trace_config() -> TraceConfig:
    trace_config = TraceConfig()
    trace_config.on_request_headers_sent.append(_mark_request_headers_sent)
    return trace_config


def _should_retry_transport_error(exc: Exception, trace_ctx: Mapping[str, Any]) -> bool:
    if trace_ctx.get("headers_sent"):
        return False
    return isinstance(exc, (asyncio.TimeoutError, ClientError, OSError))


async def post_json_request(
    session: ClientSession,
    url: str,
    *,
    body: Any,
    headers: Optional[Mapping[str, str]] = None,
    log_prefix: str,
    is_success: SuccessCheck = http_ok,
) -> Tuple[bool, Dict[str, Any]]:
    """Centralized JSON-POST every HTTP-API provider used to inline ~25 lines for.

    On transport failure, JSON decode failure, or rejected ``is_success`` check,
    returns ``(False, {"status": ..., "message": ..., "raw": ...?})`` so callers
    can decide what to do (typically: mark the payment as ``failed_creation``).
    """
    for attempt in range(1, _TRANSPORT_ATTEMPTS + 1):
        trace_ctx: dict[str, Any] = {"headers_sent": False}
        try:
            async with session.post(
                url,
                json=body,
                headers=dict(headers) if headers else None,
                trace_request_ctx=trace_ctx,
            ) as response:
                response_text = await response.text()
                try:
                    response_data = json.loads(response_text) if response_text else {}
                except json.JSONDecodeError:
                    logging.error("%s: invalid JSON response: %s", log_prefix, response_text)
                    return False, {
                        "status": response.status,
                        "message": "invalid_json",
                        "raw": response_text,
                    }
                if not is_success(response.status, response_data):
                    logging.error(
                        "%s: API returned error (status=%s, body=%s)",
                        log_prefix,
                        response.status,
                        response_data,
                    )
                    return False, {"status": response.status, "message": response_data}
                return True, response_data
        except Exception as exc:
            if attempt < _TRANSPORT_ATTEMPTS and _should_retry_transport_error(exc, trace_ctx):
                logging.warning(
                    "%s: transport failed before request headers were sent; retrying (%s/%s): %s",  # noqa: E501
                    log_prefix,
                    attempt + 1,
                    _TRANSPORT_ATTEMPTS,
                    exc,
                )
                continue
            logging.exception("%s: request failed.", log_prefix)
            return False, {"message": str(exc)}
    return False, {"message": "request_failed"}


def first_value(data: Optional[Mapping[str, Any]], *keys: str) -> Optional[str]:
    """Return the first non-empty value among ``keys`` (cast to ``str``)."""
    if not data:
        return None
    for key in keys:
        value = data.get(key)
        if value:
            return str(value)
    return None


class HttpClientMixin:
    """Shared lazy ``aiohttp.ClientSession`` lifecycle for provider services.

    Each subclass calls ``self._init_http_client(total_timeout=...)`` from
    ``__init__`` and inherits ``_get_session`` / ``close``. The session is
    created on first use and recreated transparently if it was closed.

    Payment provider calls are infrequent but user-facing, so the default
    connector does not reuse TCP connections. This avoids intermittent hangs
    on stale keep-alive sockets after long idle periods.
    """

    _timeout: ClientTimeout
    _session: Optional[ClientSession]
    _connector_force_close: bool

    def _init_http_client(self, *, total_timeout: float = 20.0) -> None:
        self._timeout = ClientTimeout(total=total_timeout)
        self._session = None
        self._connector_force_close = True

    async def _get_session(self) -> ClientSession:
        if self._session is None or self._session.closed:
            connector = TCPConnector(force_close=self._connector_force_close)
            self._session = ClientSession(
                timeout=self._timeout,
                connector=connector,
                headers={"User-Agent": _PAYMENT_REQUEST_USER_AGENT},
                trace_configs=[_payment_trace_config()],
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
