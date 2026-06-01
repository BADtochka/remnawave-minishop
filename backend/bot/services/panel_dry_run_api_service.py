import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from config.settings import Settings

from .panel_api_service import PanelApiService

logger = logging.getLogger(__name__)

_USER_ACTION_RE = re.compile(
    r"^/users/(?P<user_uuid>[^/]+)/actions/(?P<action>enable|disable|reset-traffic)$"
)
_INTERNAL_SQUAD_BULK_RE = re.compile(
    r"^/internal-squads/(?P<squad_uuid>[^/]+)/bulk-actions/"
    r"(?P<action>add-users|remove-users)$"
)
_LIVE_POST_ENDPOINTS = frozenset({"/system/tools/happ/encrypt"})
_KNOWN_TRAFFIC_STRATEGIES = frozenset({"NO_RESET", "DAY", "WEEK", "MONTH"})

# Panel payloads can carry proxy credentials (e.g. trojanPassword, ssPassword,
# vless/vmess uuids) and PII (email, telegramId). Redact such values before they
# reach the dry-run log so secrets are never written in clear text.
_SENSITIVE_KEY_RE = re.compile(
    r"pass|pwd|secret|token|key|credential|auth|cookie|session|"
    r"email|mail|phone|telegram|mnemonic",
    re.IGNORECASE,
)
# Mask opaque id-like path segments (UUIDs, long tokens) in logged endpoints.
_ENDPOINT_ID_RE = re.compile(r"(?<=/)(?:[0-9a-fA-F]{8}-[0-9a-fA-F-]{8,}|[A-Za-z0-9_-]{24,})")
_REDACTED = "***"


@dataclass
class _DryRunValidation:
    errors: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add(self, message: str) -> None:
        self.errors.append(message)


class PanelDryRunApiService(PanelApiService):
    """Panel API client that reads live data but never mutates Remnawave users."""

    def __init__(self, settings: Settings):
        super().__init__(settings)
        self._synthetic_users: Dict[str, Dict[str, Any]] = {}

    async def _request(
        self, method: str, endpoint: str, log_full_response: bool = False, **kwargs
    ) -> Optional[Dict[str, Any]]:
        method_upper = method.upper()
        normalized_endpoint = self._normalize_endpoint(endpoint)
        if not self._should_intercept(method_upper, normalized_endpoint):
            return await super()._request(
                method_upper,
                endpoint,
                log_full_response=log_full_response,
                **kwargs,
            )

        validation = await self._validate_dry_run_request(
            method_upper,
            normalized_endpoint,
            kwargs.get("json"),
        )
        if not validation.ok:
            self._log_dry_run(
                "BLOCKED",
                method_upper,
                normalized_endpoint,
                kwargs.get("json"),
                errors=validation.errors,
            )
            return {
                "error": True,
                "status_code": 400,
                "errorCode": "DRY_RUN_VALIDATION_FAILED",
                "message": "Panel dry-run validation failed.",
                "details": {"errors": validation.errors},
            }

        response = await self._dry_run_response(
            method_upper,
            normalized_endpoint,
            kwargs.get("json"),
        )
        self._log_dry_run("OK", method_upper, normalized_endpoint, kwargs.get("json"))
        return {"response": response, "dryRun": True}

    @staticmethod
    def _normalize_endpoint(endpoint: str) -> str:
        return f"/{str(endpoint or '').lstrip('/')}"

    @staticmethod
    def _safe_endpoint(endpoint: str) -> str:
        """Mask opaque id-like segments so logged paths carry no private ids."""
        return _ENDPOINT_ID_RE.sub("<id>", str(endpoint or ""))

    @classmethod
    def _redact(cls, value: Any, _depth: int = 0) -> Any:
        """Recursively replace values under sensitive keys with a placeholder."""
        if _depth > 6:
            return "..."
        if isinstance(value, dict):
            return {
                k: (
                    _REDACTED
                    if isinstance(k, str) and _SENSITIVE_KEY_RE.search(k)
                    else cls._redact(v, _depth + 1)
                )
                for k, v in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [cls._redact(item, _depth + 1) for item in value]
        return value

    @classmethod
    def _payload_preview(cls, payload: Any) -> str:
        redacted = cls._redact(payload)
        try:
            text = json.dumps(redacted, ensure_ascii=False, default=str, sort_keys=True)
        except Exception:
            text = str(redacted)
        if len(text) > 1200:
            return f"{text[:1200]}..."
        return text

    def _log_dry_run(
        self,
        status: str,
        method: str,
        endpoint: str,
        payload: Any,
        *,
        errors: Optional[List[str]] = None,
    ) -> None:
        logger.info(
            "[PANEL DRY-RUN %s] would %s %s payload=%s%s",
            status,
            method,
            self._safe_endpoint(endpoint),
            self._payload_preview(payload),
            f" errors={errors}" if errors else "",
        )

    @staticmethod
    def _should_intercept(method: str, endpoint: str) -> bool:
        if method in PanelApiService._SAFE_METHODS:
            return False
        if method == "POST" and endpoint in _LIVE_POST_ENDPOINTS:
            return False
        return True

    async def _validate_dry_run_request(
        self,
        method: str,
        endpoint: str,
        payload: Any,
    ) -> _DryRunValidation:
        validation = _DryRunValidation()
        data = payload if isinstance(payload, dict) else {}
        if payload is not None and not isinstance(payload, dict):
            validation.add("JSON payload must be an object.")
            return validation

        if method == "POST" and endpoint == "/users":
            await self._validate_create_user_payload(data, validation)
            return validation
        if method == "PATCH" and endpoint == "/users":
            await self._validate_update_user_payload(data, validation)
            return validation
        if method == "POST" and (match := _USER_ACTION_RE.match(endpoint)):
            user_uuid = match.group("user_uuid")
            self._validate_non_empty_string(user_uuid, "user uuid", validation)
            await self._validate_remote_user(user_uuid, validation)
            return validation
        if method == "DELETE" and endpoint.startswith("/users/"):
            user_uuid = endpoint.removeprefix("/users/").strip()
            self._validate_non_empty_string(user_uuid, "user uuid", validation)
            await self._validate_remote_user(user_uuid, validation)
            return validation
        if method == "POST" and endpoint == "/hwid/devices/delete":
            user_uuid = self._validate_non_empty_string(
                data.get("userUuid"),
                "userUuid",
                validation,
            )
            self._validate_non_empty_string(data.get("hwid"), "hwid", validation)
            await self._validate_remote_user(user_uuid, validation)
            return validation
        if match := _INTERNAL_SQUAD_BULK_RE.match(endpoint):
            squad_uuid = match.group("squad_uuid")
            self._validate_non_empty_string(squad_uuid, "squad uuid", validation)
            user_uuids = self._validate_string_list(data.get("userUuids"), "userUuids", validation)
            if not user_uuids:
                user_uuids = self._validate_string_list(data.get("users"), "users", validation)
            await self._validate_remote_squads([squad_uuid], validation)
            for user_uuid in user_uuids:
                await self._validate_remote_user(user_uuid, validation)
            return validation

        if payload is None:
            return validation
        self._validate_json_serializable(payload, validation)
        return validation

    async def _validate_create_user_payload(
        self,
        payload: Dict[str, Any],
        validation: _DryRunValidation,
    ) -> None:
        username = self._validate_non_empty_string(payload.get("username"), "username", validation)
        if username and (
            not (3 <= len(username) <= 36) or not re.match(r"^[A-Za-z0-9_-]+$", username)
        ):
            validation.add("username must be 3-36 chars and contain only A-Z, 0-9, _ or -.")
        self._validate_user_mutation_payload(payload, validation, require_uuid=False)
        await self._validate_remote_squads(
            self._validate_string_list(
                payload.get("activeInternalSquads"),
                "activeInternalSquads",
                validation,
                required=False,
            ),
            validation,
        )
        if not bool(getattr(self.settings, "PANEL_DRY_RUN_SYNTHETIC_CREATE", True)):
            validation.add("PANEL_DRY_RUN_SYNTHETIC_CREATE is disabled.")
        if self._remote_validation_enabled and username:
            await self._validate_create_uniqueness(payload, validation)

    async def _validate_update_user_payload(
        self,
        payload: Dict[str, Any],
        validation: _DryRunValidation,
    ) -> None:
        user_uuid = self._validate_non_empty_string(payload.get("uuid"), "uuid", validation)
        self._validate_user_mutation_payload(payload, validation, require_uuid=True)
        await self._validate_remote_user(user_uuid, validation)
        await self._validate_remote_squads(
            self._validate_string_list(
                payload.get("activeInternalSquads"),
                "activeInternalSquads",
                validation,
                required=False,
            ),
            validation,
        )

    def _validate_user_mutation_payload(
        self,
        payload: Dict[str, Any],
        validation: _DryRunValidation,
        *,
        require_uuid: bool,
    ) -> None:
        if require_uuid:
            self._validate_non_empty_string(payload.get("uuid"), "uuid", validation)
        if "expireAt" in payload:
            self._validate_datetime(payload.get("expireAt"), "expireAt", validation)
        if "trafficLimitBytes" in payload:
            self._validate_non_negative_int(
                payload.get("trafficLimitBytes"),
                "trafficLimitBytes",
                validation,
            )
        if "trafficLimitStrategy" in payload:
            strategy = self._validate_non_empty_string(
                payload.get("trafficLimitStrategy"),
                "trafficLimitStrategy",
                validation,
            )
            if strategy and strategy.upper() not in _KNOWN_TRAFFIC_STRATEGIES:
                validation.add(f"trafficLimitStrategy {strategy!r} is not supported.")
        if "hwidDeviceLimit" in payload:
            self._validate_non_negative_int(
                payload.get("hwidDeviceLimit"),
                "hwidDeviceLimit",
                validation,
            )
        if "telegramId" in payload:
            self._validate_positive_int(payload.get("telegramId"), "telegramId", validation)
        if "email" in payload and payload.get("email") is not None:
            self._validate_non_empty_string(payload.get("email"), "email", validation)
        if "externalSquadUuid" in payload and payload.get("externalSquadUuid") is not None:
            self._validate_non_empty_string(
                payload.get("externalSquadUuid"),
                "externalSquadUuid",
                validation,
            )
        self._validate_json_serializable(payload, validation)

    @property
    def _remote_validation_enabled(self) -> bool:
        return bool(getattr(self.settings, "PANEL_DRY_RUN_VALIDATE_REMOTE", True))

    async def _validate_remote_user(
        self,
        user_uuid: Optional[str],
        validation: _DryRunValidation,
    ) -> Optional[Dict[str, Any]]:
        if not user_uuid or not self._remote_validation_enabled:
            return self._synthetic_users.get(str(user_uuid or ""))
        user = self._synthetic_users.get(str(user_uuid))
        if user:
            return user
        try:
            user = await super().get_user_by_uuid(str(user_uuid), log_response=False)
        except Exception as exc:
            validation.add(f"failed to validate panel user {user_uuid}: {type(exc).__name__}")
            return None
        if not user:
            validation.add(f"panel user {user_uuid} was not found.")
        return user

    async def _validate_remote_squads(
        self,
        squad_uuids: List[str],
        validation: _DryRunValidation,
    ) -> None:
        if not squad_uuids or not self._remote_validation_enabled:
            return
        try:
            squads = await super().get_internal_squads()
        except Exception as exc:
            validation.add(f"failed to validate panel squads: {type(exc).__name__}")
            return
        if squads is None:
            validation.add("failed to validate panel squads: empty panel response.")
            return
        known = {
            str(squad.get("uuid") or squad.get("id") or "").strip()
            for squad in squads
            if isinstance(squad, dict)
        }
        missing = sorted({squad_uuid for squad_uuid in squad_uuids if squad_uuid not in known})
        if missing:
            validation.add(f"panel squads were not found: {', '.join(missing)}.")

    async def _validate_create_uniqueness(
        self,
        payload: Dict[str, Any],
        validation: _DryRunValidation,
    ) -> None:
        checks = (
            ("username", "username", payload.get("username")),
            ("telegramId", "telegram_id", payload.get("telegramId")),
            ("email", "email", payload.get("email")),
        )
        for label, argument_name, value in checks:
            if value in (None, ""):
                continue
            try:
                users = await super().get_users_by_filter(**{argument_name: value})
            except Exception as exc:
                validation.add(f"failed to validate unique {label}: {type(exc).__name__}")
                continue
            if users:
                validation.add(f"panel user with {label} {value!r} already exists.")

    @staticmethod
    def _validate_non_empty_string(
        value: Any,
        name: str,
        validation: _DryRunValidation,
    ) -> Optional[str]:
        if not isinstance(value, str) or not value.strip():
            validation.add(f"{name} must be a non-empty string.")
            return None
        return value.strip()

    @staticmethod
    def _validate_string_list(
        value: Any,
        name: str,
        validation: _DryRunValidation,
        *,
        required: bool = True,
    ) -> List[str]:
        if value is None:
            if required:
                validation.add(f"{name} must be a list of strings.")
            return []
        if not isinstance(value, list):
            validation.add(f"{name} must be a list of strings.")
            return []
        result = []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                validation.add(f"{name} contains an empty or non-string value.")
                continue
            result.append(item.strip())
        return result

    @staticmethod
    def _validate_non_negative_int(
        value: Any,
        name: str,
        validation: _DryRunValidation,
    ) -> None:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            validation.add(f"{name} must be an integer.")
            return
        if parsed < 0:
            validation.add(f"{name} must be >= 0.")

    @staticmethod
    def _validate_positive_int(value: Any, name: str, validation: _DryRunValidation) -> None:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            validation.add(f"{name} must be an integer.")
            return
        if parsed <= 0:
            validation.add(f"{name} must be > 0.")

    @staticmethod
    def _validate_datetime(value: Any, name: str, validation: _DryRunValidation) -> None:
        if not isinstance(value, str) or not value.strip():
            validation.add(f"{name} must be an ISO datetime string.")
            return
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            validation.add(f"{name} must be a valid ISO datetime string.")

    @staticmethod
    def _validate_json_serializable(value: Any, validation: _DryRunValidation) -> None:
        try:
            json.dumps(value, default=str)
        except (TypeError, ValueError):
            validation.add("payload must be JSON serializable.")

    async def _dry_run_response(
        self,
        method: str,
        endpoint: str,
        payload: Any,
    ) -> Dict[str, Any]:
        data = payload if isinstance(payload, dict) else {}
        if method == "POST" and endpoint == "/users":
            return self._dry_run_create_user_response(data)
        if method == "PATCH" and endpoint == "/users":
            return await self._dry_run_patch_user_response(data)
        if method == "POST" and (match := _USER_ACTION_RE.match(endpoint)):
            return self._dry_run_user_action_response(
                match.group("user_uuid"),
                match.group("action"),
            )
        if method == "DELETE" and endpoint.startswith("/users/"):
            return {"uuid": endpoint.removeprefix("/users/"), "deleted": True, "dryRun": True}
        if method == "POST" and endpoint == "/hwid/devices/delete":
            return {"userUuid": data.get("userUuid"), "hwid": data.get("hwid"), "dryRun": True}
        if match := _INTERNAL_SQUAD_BULK_RE.match(endpoint):
            return {
                "squadUuid": match.group("squad_uuid"),
                "action": match.group("action"),
                "users": data.get("userUuids") or data.get("users") or [],
                "dryRun": True,
            }
        return {"dryRun": True}

    def _dry_run_create_user_response(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        identity = ":".join(
            str(payload.get(key) or "") for key in ("username", "telegramId", "email")
        )
        user_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"remnawave-minishop:dry-run:{identity}"))
        short_uuid = user_uuid.split("-")[0]
        response = {
            **payload,
            "uuid": user_uuid,
            "shortUuid": short_uuid,
            "subscriptionUuid": short_uuid,
            "subscriptionUrl": self._subscription_url(short_uuid),
            "dryRun": True,
        }
        self._synthetic_users[user_uuid] = response
        return response

    async def _dry_run_patch_user_response(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        user_uuid = str(payload.get("uuid") or "")
        existing = self._synthetic_users.get(user_uuid)
        if not existing and self._remote_validation_enabled:
            try:
                existing = await super().get_user_by_uuid(user_uuid, log_response=False)
            except Exception:
                existing = None
        response = {**(existing or {"uuid": user_uuid}), **payload, "dryRun": True}
        if user_uuid in self._synthetic_users:
            self._synthetic_users[user_uuid] = response
        return response

    @staticmethod
    def _dry_run_user_action_response(user_uuid: str, action: str) -> Dict[str, Any]:
        response: Dict[str, Any] = {"uuid": user_uuid, "action": action, "dryRun": True}
        if action == "enable":
            response["status"] = "ACTIVE"
        elif action == "disable":
            response["status"] = "DISABLED"
        elif action == "reset-traffic":
            response["userTraffic"] = {"usedTrafficBytes": 0}
        return response

    def _subscription_url(self, short_uuid: str) -> Optional[str]:
        if not self.settings.PANEL_API_URL:
            return None
        return f"{self.settings.PANEL_API_URL.rstrip('/')}/sub/{short_uuid}"
