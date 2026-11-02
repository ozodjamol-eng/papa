import asyncio
import logging
from dataclasses import dataclass
from datetime import date
from datetime import datetime, time, timedelta

from telegram import Bot
from telegram.error import Forbidden

from bot.daily_duas import dua_for_date, format_daily_dua
from bot.database import (
    active_daily_dua_groups,
    active_bot_users,
    mark_daily_dua_group_status,
    mark_daily_dua_status,
    record_daily_dua_stats,
    release_daily_dua_group,
    release_daily_dua,
    reserve_daily_dua_group,
    reserve_daily_dua,
    set_bot_user_active,
)
from bot.handlers.prayer import TASHKENT_TIMEZONE

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DailyDuaStats:
    user_sent: int = 0
    group_sent: int = 0
    user_errors: int = 0
    group_errors: int = 0

    @property
    def total_sent(self) -> int:
        return self.user_sent + self.group_sent


class DailyDuaService:
    def __init__(self) -> None:
        self.last_stats = DailyDuaStats()

    async def check_once(self, bot: Bot, now: datetime | None = None) -> int:
        current = now or datetime.now(TASHKENT_TIMEZONE)
        if current.tzinfo is None:
            raise ValueError("Scheduler vaqti timezone bilan berilishi kerak")
        tashkent_now = current.astimezone(TASHKENT_TIMEZONE)
        if (tashkent_now.hour, tashkent_now.minute) != (7, 5):
            return 0

        stats = await self.deliver_for_date(bot, tashkent_now.date())
        return stats.total_sent

    async def deliver_for_date(self, bot: Bot, day: date) -> DailyDuaStats:
        """Send one day's dua now; used by the scheduler and deterministic tests."""
        delivery_date = day.isoformat()
        dua = dua_for_date(day)
        text = format_daily_dua(dua)
        user_sent = group_sent = user_errors = group_errors = 0

        for user_id in active_bot_users():
            if not reserve_daily_dua(user_id, delivery_date, dua.id):
                continue
            try:
                await bot.send_message(user_id, text)
                mark_daily_dua_status(user_id, delivery_date, "sent")
                user_sent += 1
            except Forbidden:
                set_bot_user_active(user_id, False)
                mark_daily_dua_status(user_id, delivery_date, "blocked")
                user_errors += 1
                logger.info("Kunlik duo yuborilmadi: user=%s botni bloklagan", user_id)
            except Exception:
                release_daily_dua(user_id, delivery_date)
                user_errors += 1
                logger.exception(
                    "Kunlik duoni yuborishda xato: user=%s date=%s",
                    user_id,
                    delivery_date,
                )

        for group in active_daily_dua_groups():
            chat_id = int(group["chat_id"])
            if not reserve_daily_dua_group(chat_id, delivery_date, dua.id):
                continue
            try:
                await bot.send_message(chat_id, text)
                mark_daily_dua_group_status(chat_id, delivery_date, "sent")
                group_sent += 1
            except Exception:
                release_daily_dua_group(chat_id, delivery_date)
                group_errors += 1
                logger.exception(
                    "Kunlik duoni guruhga yuborishda xato: chat=%s date=%s",
                    chat_id,
                    delivery_date,
                )

        self.last_stats = DailyDuaStats(user_sent, group_sent, user_errors, group_errors)
        record_daily_dua_stats(
            delivery_date,
            user_sent,
            group_sent,
            user_errors,
            group_errors,
        )
        logger.info(
            "Kunlik duo statistikasi: date=%s users=%s groups=%s user_errors=%s group_errors=%s",
            delivery_date,
            user_sent,
            group_sent,
            user_errors,
            group_errors,
        )
        return self.last_stats


async def daily_dua_loop(
    bot: Bot,
    stop_event: asyncio.Event,
) -> None:
    service = DailyDuaService()
    last_attempt_date = None
    while not stop_event.is_set():
        now = datetime.now(TASHKENT_TIMEZONE)
        today_target = datetime.combine(now.date(), time(7, 5), tzinfo=TASHKENT_TIMEZONE)

        if (now.hour, now.minute) == (7, 5) and last_attempt_date != now.date():
            target = now
        elif now < today_target:
            target = today_target
        else:
            target = today_target + timedelta(days=1)

        delay = max(0.0, (target - now).total_seconds())
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=delay)
        except TimeoutError:
            try:
                run_time = datetime.now(TASHKENT_TIMEZONE)
                await service.check_once(bot, run_time)
                last_attempt_date = run_time.date()
            except Exception:
                logger.exception("Kunlik duo schedulerida xato")
