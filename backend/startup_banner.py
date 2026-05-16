import os
import sys
from urllib.parse import urlsplit

_BANNER_TEMPLATE = """
              ~ ~ ~  r e m n a w a v e  ~ ~ ~

  ███╗   ███╗██╗███╗   ██╗██╗███████╗██╗  ██╗ ██████╗ ██████╗
  ████╗ ████║██║████╗  ██║██║██╔════╝██║  ██║██╔═══██╗██╔══██╗
  ██╔████╔██║██║██╔██╗ ██║██║███████╗███████║██║   ██║██████╔╝
  ██║╚██╔╝██║██║██║╚██╗██║██║╚════██║██╔══██║██║   ██║██╔═══╝
  ██║ ╚═╝ ██║██║██║ ╚████║██║███████║██║  ██║╚██████╔╝██║
  ╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝

              container :: {service}
{details}
         https://github.com/3252a8/remnawave-minishop
"""


def _env(name: str, default: str = "-") -> str:
    return os.getenv(name) or default


def _bool_env(name: str) -> str:
    value = _env(name, "").lower()
    if value in {"1", "true", "yes", "on"}:
        return "on"
    if value in {"0", "false", "no", "off"}:
        return "off"
    return _env(name)


def _redis_target() -> str:
    value = _env("REDIS_URL")
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "-"
    if not parsed.hostname:
        return "-"
    port = f":{parsed.port}" if parsed.port else ""
    db = parsed.path.lstrip("/") or "0"
    return f"{parsed.hostname}{port}/{db}"


def _postgres_target() -> str:
    return f"{_env('POSTGRES_HOST')}:{_env('POSTGRES_PORT', '5432')}/{_env('POSTGRES_DB')}"


def _detail_line(text: str) -> str:
    return f"              {text[:64]}"


def _service_details(service: str) -> str:
    image_tag = _env("IMAGE_TAG", "local")
    log_level = _env("LOG_LEVEL", "INFO")
    common = [f"image tag :: {image_tag}", f"log level :: {log_level}"]
    if service == "backend":
        lines = [
            *common,
            f"webhooks :: :{_env('WEB_SERVER_PORT', '8080')}",
            f"webapp api :: {_bool_env('WEBAPP_ENABLED')} / :{_env('WEBAPP_SERVER_PORT', '8081')}",
            f"postgres :: {_postgres_target()}",
            f"redis :: {_redis_target()}",
        ]
    elif service == "worker":
        panel_sync_interval = _env("WORKER_PANEL_SYNC_INTERVAL_SECONDS")
        panel_sync_interval = f"{panel_sync_interval}s" if panel_sync_interval != "-" else "-"
        lines = [
            *common,
            f"queue concurrency :: {_env('WEBHOOK_QUEUE_CONCURRENCY', '1')}",
            f"panel sync interval :: {panel_sync_interval}",
            f"tariffs config :: {_env('TARIFFS_CONFIG_PATH', '-')}",
            f"postgres :: {_postgres_target()}",
            f"redis :: {_redis_target()}",
        ]
    elif service == "migrate":
        lines = [
            *common,
            "mode :: one-shot migrations",
            f"postgres :: {_postgres_target()}",
            "data dir :: /app/data",
        ]
    else:
        lines = common
    return "\n".join(_detail_line(line) for line in lines)


def print_startup_banner(service: str) -> None:
    normalized_service = service.lower()
    banner = (
        _BANNER_TEMPLATE.format(
            service=normalized_service.upper(),
            details=_service_details(normalized_service),
        )
        + "\n"
    )
    try:
        sys.stdout.write(banner)
        sys.stdout.flush()
    except UnicodeEncodeError:
        try:
            sys.stdout.buffer.write(banner.encode("utf-8"))
            sys.stdout.buffer.flush()
        except Exception:
            pass
    except Exception:
        pass
