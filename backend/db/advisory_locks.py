from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Serializes background jobs that rewrite subscription rows from panel state.
SUBSCRIPTION_BACKGROUND_SYNC_LOCK_ID = 817512404897421338


async def acquire_subscription_background_sync_lock(session: AsyncSession) -> None:
    await session.execute(
        text("SELECT pg_advisory_xact_lock(:lock_id)"),
        {"lock_id": SUBSCRIPTION_BACKGROUND_SYNC_LOCK_ID},
    )
