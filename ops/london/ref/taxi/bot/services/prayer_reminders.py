import asyncio
import logging
from collections.abc import Callable
from datetime import date, datetime

from telegram import Bot

from bot.database import (
    enabled_prayer_users,
    release_prayer_notification,
    reserve_prayer_notification,
)
from bot.handlers.prayer import (
    PRAYER_KEYS,
    PRAYER_NAMES,
    TASHKENT_TIMEZONE,
    PrayerTimesResult,
    fetch_prayer_times,
    with_bot_footer,
)

logger = logging.getLogger(__name__)


class PrayerReminderService:
    def __init__(
        self,
        fetcher: Callable[[date], PrayerTimesResult] = fetch_prayer_times,
    ) -> None:
        self._fetcher = fetcher
        self._cached_date: date | None = None
        self._cached_timings: dict[str, str] | None = None

    async def timings_for(self, day: date) -> dict[str, str]:
        if self._cached_date != day or self._cached_timings is None:
            result = await asyncio.to_thread(self._fetcher, day)
            if result.requested_date != day or result.api_date != day:
                raise RuntimeError("Эслатма учун жадвал санаси жорий санага мос эмас")
            self._cached_date = day
            self._cached_timings = result.timings
        return self._cached_timings

    async def check_once(self, bot: Bot, now: datetime | None = None) -> int:
        current = now or datetime.now(TASHKENT_TIMEZONE)
        timings = await self.timings_for(current.date())
        current_clock = current.strftime("%H:%M")
        sent_count = 0

        for key in PRAYER_KEYS:
            if timings[key] != current_clock:
                continue
            prayer_date = current.date().isoformat()
            for user_id in enabled_prayer_users(key):
                if not reserve_prayer_notification(user_id, key, prayer_date):
                    continue
                try:
                    await bot.send_message(
                        user_id,
                        with_bot_footer(
                            f"🔔 {PRAYER_NAMES[key]} намози вақти бўлди — {timings[key]}"
                        ),
                    )
                    sent_count += 1
                except Exception:
                    release_prayer_notification(user_id, key, prayer_date)
                    logger.exception(
                        "Namoz eslatmasini yuborib bo‘lmadi: user=%s prayer=%s date=%s",
                        user_id,
                        key,
                        prayer_date,
                    )
        return sent_count


async def reminder_loop(
    bot: Bot,
    stop_event: asyncio.Event,
    interval_seconds: float = 30,
) -> None:
    service = PrayerReminderService()
    while not stop_event.is_set():
        try:
            await service.check_once(bot)
        except Exception:
            logger.exception("Namoz eslatmalarini tekshirishda xato")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except TimeoutError:
            pass
