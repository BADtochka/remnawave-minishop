import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
from startup_banner import print_startup_banner

from bot.main_bot import run_bot
from config.settings import get_settings


def _resolve_log_level(value: str) -> int:
    return getattr(logging, value.upper(), logging.INFO)


async def main():
    settings = get_settings()
    await run_bot(settings, run_web=True, run_tariff_worker=False)


if __name__ == "__main__":
    load_dotenv()
    print_startup_banner("bot")
    logging.basicConfig(
        level=_resolve_log_level(os.getenv("LOG_LEVEL", "INFO")),
        stream=sys.stdout,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped manually")
    except Exception as e_global:
        logging.critical(f"Global unhandled exception in main: {e_global}", exc_info=True)
        sys.exit(1)
