import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from bot.middlewares.i18n import JsonI18n
from bot.services.panel_api_service import PanelApiService
from bot.services.subscription_service import SubscriptionService
from bot.utils.date_utils import month_start
from config.settings import Settings
from db.dal import subscription_dal, tariff_dal
from db.models import Subscription

PREMIUM_WARNING_LEVEL_OFFSET = 1000


class TariffTrafficWorker:
    def __init__(
        self,
        settings: Settings,
        session_factory: sessionmaker,
        panel_service: PanelApiService,
        subscription_service: SubscriptionService,
        bot: Optional[Bot] = None,
        i18n: Optional[JsonI18n] = None,
    ):
        self.settings = settings
        self.session_factory = session_factory
        self.panel_service = panel_service
        self.subscription_service = subscription_service
        self.bot = bot
        self.i18n = i18n
        self._stopped = asyncio.Event()
        self._premium_nodes_cache = {}

    async def run(self) -> None:
        if not self.settings.tariffs_config:
            return
        while not self._stopped.is_set():
            try:
                async with self.session_factory() as session:
                    await self.traffic_period_tick(session)
                    await session.commit()
                async with self.session_factory() as session:
                    await self.legacy_throttle_recovery_tick(session)
                    await session.commit()
            except Exception:
                logging.exception("TariffTrafficWorker tick failed")
            try:
                await asyncio.wait_for(self._stopped.wait(), timeout=300)
            except asyncio.TimeoutError:
                pass

    def stop(self) -> None:
        self._stopped.set()

    async def traffic_period_tick(self, session: AsyncSession) -> None:
        now = datetime.now(timezone.utc)
        warning_period_start = month_start(now)
        result = await session.execute(
            select(Subscription).where(
                Subscription.is_active == True,
                Subscription.end_date > now,
                Subscription.tariff_key.is_not(None),
            )
        )
        for sub in result.scalars().all():
            try:
                tariff = self.settings.tariffs_config.require(sub.tariff_key)
            except Exception:
                continue
            panel_data = await self.panel_service.get_user_by_uuid(sub.panel_user_uuid, log_response=False) or {}
            used, limit, panel_strategy = self.subscription_service._extract_panel_traffic_details(panel_data)
            panel_status = str(panel_data.get("status") or "").upper()
            if used is not None and used != sub.traffic_used_bytes:
                sub.traffic_used_bytes = used
            if limit is not None and limit != sub.traffic_limit_bytes:
                sub.traffic_limit_bytes = limit
            if panel_status and panel_status != (sub.status_from_panel or "").upper():
                sub.status_from_panel = panel_status

            if tariff.billing_model == "period":
                await self._ensure_period_reset_strategy(sub, tariff, limit, panel_strategy)
            await self._maybe_warn_or_throttle(
                session,
                sub,
                tariff,
                used,
                limit,
                warning_period_start=warning_period_start if tariff.billing_model == "period" else None,
            )

            await self._sync_premium_squad_limit(session, sub, tariff, now)

    async def _ensure_period_reset_strategy(
        self,
        sub: Subscription,
        tariff,
        limit: Optional[int],
        panel_strategy: Optional[str],
    ) -> None:
        if str(panel_strategy or "").upper() == "MONTH":
            return
        traffic_limit_bytes = int(limit or sub.traffic_limit_bytes or (tariff.monthly_bytes + int(sub.topup_balance_bytes or 0)))
        payload = self.subscription_service._build_panel_update_payload(
            panel_user_uuid=sub.panel_user_uuid,
            expire_at=sub.end_date,
            traffic_limit_bytes=traffic_limit_bytes,
            traffic_limit_strategy="MONTH",
        )
        payload["activeInternalSquads"] = self.subscription_service._panel_squads_for_tariff(
            tariff,
            include_premium=not bool(getattr(sub, "premium_is_limited", False)),
        )
        await self.panel_service.update_user_details_on_panel(sub.panel_user_uuid, payload, log_response=False)

    async def _maybe_warn_or_throttle(
        self,
        session: AsyncSession,
        sub: Subscription,
        tariff,
        used: Optional[int],
        limit: Optional[int],
        *,
        warning_period_start: Optional[datetime] = None,
    ) -> None:
        used_val = int(used or sub.traffic_used_bytes or 0)
        limit_val = int(limit or sub.traffic_limit_bytes or 0)
        if limit_val <= 0:
            return
        ratio = used_val / limit_val
        levels = list(getattr(self.settings, "tariff_traffic_warning_levels", [85, 90, 95]))
        for level in levels:
            threshold = level / 100
            if ratio < threshold:
                continue
            warning = await tariff_dal.get_warning(
                session,
                subscription_id=sub.subscription_id,
                period_start_at=warning_period_start if tariff.billing_model == "period" else None,
                level=level,
                traffic_limit_bytes=limit_val if tariff.billing_model == "traffic" else None,
            )
            if warning:
                continue
            await tariff_dal.create_warning(
                session,
                subscription_id=sub.subscription_id,
                period_start_at=warning_period_start if tariff.billing_model == "period" else None,
                level=level,
                traffic_limit_bytes=limit_val if tariff.billing_model == "traffic" else None,
            )
            if self.bot:
                try:
                    left_pct = max(0, 100 - level)
                    if level < 100:
                        text = f"Трафик тарифа {tariff.name(self.settings.DEFAULT_LANGUAGE)} почти закончился. Осталось около {left_pct}%."
                    else:
                        text = "Трафик закончился. Доступ временно ограничен до сброса или докупки пакета."
                    markup = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="Докупить трафик",
                                    callback_data="tariff_topup:list",
                                )
                            ]
                        ]
                    )
                    await self.bot.send_message(sub.user_id, text, reply_markup=markup)
                except Exception:
                    logging.exception("Failed to send traffic warning to user %s", sub.user_id)
        if ratio >= 1.0 and not sub.is_throttled:
            logging.info(
                "Tariff traffic limit reached for user %s subscription %s. "
                "Leaving access control to Remnawave status handling.",
                sub.user_id,
                sub.subscription_id,
            )

    async def _sync_premium_squad_limit(
        self,
        session: AsyncSession,
        sub: Subscription,
        tariff,
        now: datetime,
    ) -> None:
        if not getattr(tariff, "premium_squad_uuids", None):
            if any(
                int(value or 0) > 0
                for value in (
                    sub.premium_baseline_bytes,
                    sub.premium_topup_balance_bytes,
                    sub.premium_used_bytes,
                )
            ) or sub.premium_is_limited:
                sub.premium_baseline_bytes = 0
                sub.premium_topup_balance_bytes = 0
                sub.premium_used_bytes = 0
                sub.premium_is_limited = False
            return

        premium_period_start = month_start(now)
        same_period = bool(getattr(sub, "premium_period_start_at", None) == premium_period_start)
        premium_baseline = int(tariff.premium_monthly_bytes or 0)
        premium_topup_balance = int(sub.premium_topup_balance_bytes or 0)
        premium_topup_used = int(getattr(sub, "premium_topup_used_bytes", 0) or 0) if same_period else 0
        premium_limit = premium_baseline + premium_topup_balance + premium_topup_used
        if premium_limit <= 0:
            return

        node_uuids = await self._premium_node_uuids_for_tariff(tariff)
        if not node_uuids:
            logging.warning("Premium squads for tariff %s have no accessible nodes", tariff.key)
            return

        start_date = now.date().replace(day=1).isoformat()
        end_date = now.date().isoformat()
        premium_used = await self._premium_usage_for_user(sub.panel_user_uuid, node_uuids, start_date, end_date)
        if premium_used is None:
            return

        overflow = max(0, int(premium_used) - premium_baseline)
        delta_overflow = max(0, overflow - premium_topup_used)
        consume_from_topup = min(premium_topup_balance, delta_overflow)
        if consume_from_topup > 0:
            premium_topup_balance -= consume_from_topup
            premium_topup_used += consume_from_topup
            premium_limit = premium_baseline + premium_topup_balance + premium_topup_used

        should_limit = premium_used >= premium_limit
        changed = (
            int(sub.premium_baseline_bytes or 0) != premium_baseline
            or int(sub.premium_topup_balance_bytes or 0) != premium_topup_balance
            or int(getattr(sub, "premium_topup_used_bytes", 0) or 0) != premium_topup_used
            or int(sub.premium_used_bytes or 0) != premium_used
            or bool(sub.premium_is_limited) != should_limit
            or getattr(sub, "premium_period_start_at", None) != premium_period_start
        )
        sub.premium_baseline_bytes = premium_baseline
        sub.premium_topup_balance_bytes = premium_topup_balance
        sub.premium_topup_used_bytes = premium_topup_used
        sub.premium_used_bytes = int(premium_used)
        sub.premium_is_limited = bool(should_limit)
        sub.premium_period_start_at = premium_period_start
        await self._maybe_warn_premium_squad_limit(
            session,
            sub,
            tariff,
            premium_used,
            premium_limit,
            premium_period_start,
        )
        if not changed:
            return

        squads = self.subscription_service._panel_squads_for_tariff(
            tariff,
            include_premium=not should_limit,
        )
        await self.panel_service.update_user_details_on_panel(
            sub.panel_user_uuid,
            {"uuid": sub.panel_user_uuid, "activeInternalSquads": squads},
            log_response=False,
        )
        logging.info(
            "Premium squad access %s for user %s tariff %s: %s/%s bytes",
            "limited" if should_limit else "restored",
            sub.user_id,
            tariff.key,
            premium_used,
            premium_limit,
        )

    @staticmethod
    def _fmt_bytes(value: int) -> str:
        size = float(max(0, int(value or 0)))
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024 or unit == "TB":
                return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
            size /= 1024
        return f"{size:.1f} TB"

    async def _maybe_warn_premium_squad_limit(
        self,
        session: AsyncSession,
        sub: Subscription,
        tariff,
        used: int,
        limit: int,
        period_start_at: datetime,
    ) -> None:
        if limit <= 0:
            return
        ratio = int(used or 0) / int(limit)
        levels = list(getattr(self.settings, "tariff_traffic_warning_levels", [85, 90, 95]))
        for level in levels:
            if ratio < level / 100:
                continue
            storage_level = PREMIUM_WARNING_LEVEL_OFFSET + int(level)
            warning = await tariff_dal.get_warning(
                session,
                subscription_id=sub.subscription_id,
                period_start_at=period_start_at,
                level=storage_level,
            )
            if warning:
                continue
            await tariff_dal.create_warning(
                session,
                subscription_id=sub.subscription_id,
                period_start_at=period_start_at,
                level=storage_level,
                traffic_limit_bytes=None,
            )
            if not self.bot:
                continue
            try:
                access = await self.subscription_service.premium_access_for_tariff(tariff)
                labels = access.get("node_labels") or access.get("squad_labels") or []
                if labels:
                    visible = labels[:8]
                    servers = "\n".join(f"• {label}" for label in visible)
                    if len(labels) > len(visible):
                        servers += f"\n• ... еще {len(labels) - len(visible)}"
                else:
                    servers = "• premium-серверы тарифа"
                text = (
                    "⚠️ Отдельный лимит premium-серверов почти закончился.\n\n"
                    f"Тариф: {tariff.name(self.settings.DEFAULT_LANGUAGE)}\n"
                    f"Использовано: {self._fmt_bytes(used)} из {self._fmt_bytes(limit)} ({level}%).\n\n"
                    "Этот лимит действует на:\n"
                    f"{servers}\n\n"
                    "Можно докупить premium-трафик. Докупленный остаток переносится на следующие месяцы, пока не израсходуется."
                )
                markup = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Докупить premium-трафик",
                                callback_data="tariff_topup:list",
                            )
                        ]
                    ]
                )
                await self.bot.send_message(sub.user_id, text, reply_markup=markup)
            except Exception:
                logging.exception("Failed to send premium traffic warning to user %s", sub.user_id)

    async def _premium_node_uuids_for_tariff(self, tariff) -> list[str]:
        cache_key = tuple(sorted(tariff.premium_squad_uuids or []))
        cached = self._premium_nodes_cache.get(cache_key)
        now_ts = datetime.now(timezone.utc).timestamp()
        if cached and now_ts - cached["ts"] < 600:
            return list(cached["nodes"])

        nodes: list[str] = []
        for squad_uuid in tariff.premium_squad_uuids or []:
            accessible = await self.panel_service.get_internal_squad_accessible_nodes(squad_uuid) or []
            for node in accessible:
                if not isinstance(node, dict):
                    continue
                node_uuid = node.get("uuid") or node.get("nodeUuid") or node.get("node_uuid")
                if node_uuid:
                    nodes.append(str(node_uuid))
        deduped = list(dict.fromkeys(nodes))
        self._premium_nodes_cache[cache_key] = {"ts": now_ts, "nodes": deduped}
        return deduped

    async def _premium_usage_for_user(
        self,
        user_uuid: str,
        node_uuids: list[str],
        start_date: str,
        end_date: str,
    ) -> Optional[int]:
        total = 0
        found = False
        for node_uuid in node_uuids:
            stats = await self.panel_service.get_node_users_bandwidth_stats(
                node_uuid,
                start=start_date,
                end=end_date,
            )
            if not stats:
                continue
            entries = stats.get("topUsers") or stats.get("usersStats") or stats.get("users") or []
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                user_obj = entry.get("user") if isinstance(entry.get("user"), dict) else {}
                entry_uuid = (
                    user_obj.get("uuid")
                    or entry.get("userUuid")
                    or entry.get("uuid")
                    or entry.get("user_uuid")
                )
                if entry_uuid != user_uuid:
                    continue
                value = entry.get("total")
                if value is None:
                    value = int(entry.get("download", 0) or 0) + int(entry.get("upload", 0) or 0)
                total += int(value or 0)
                found = True
            if len(node_uuids) > 1:
                await asyncio.sleep(0.1)
        return total if found else 0

    async def legacy_throttle_recovery_tick(self, session: AsyncSession) -> None:
        """Recover subscriptions throttled by older bot versions.

        Current Remnawave versions enforce exhausted user traffic limits by
        switching the user status to LIMITED, so new ticks must not remove users
        from Internal Squads.
        """
        result = await session.execute(
            select(Subscription).where(
                Subscription.is_active == True,
                Subscription.is_throttled == True,
            )
        )
        for sub in result.scalars().all():
            try:
                tariff = self.settings.tariffs_config.require(sub.tariff_key)
            except Exception:
                continue
            if int(sub.traffic_limit_bytes or 0) <= int(sub.traffic_used_bytes or 0):
                continue
            for squad_uuid in tariff.squad_uuids:
                await self.panel_service.add_users_to_internal_squad(squad_uuid, [sub.panel_user_uuid])
            await subscription_dal.update_subscription(
                session,
                sub.subscription_id,
                {"is_throttled": False, "status_from_panel": "ACTIVE"},
            )
