import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from bot.keyboards.reply import prayer_keyboard
from config import config

logger = logging.getLogger(__name__)
TASHKENT_TIMEZONE = timezone(timedelta(hours=5), name="Asia/Tashkent")
REFERENCE_PATH = Path(__file__).resolve().parents[2] / "data" / "prayer_reference.json"
PRAYER_KEYS = ("Fajr", "Dhuhr", "Asr", "Maghrib", "Isha")
PRAYER_NAMES = {
    "Fajr": "Бомдод",
    "Dhuhr": "Пешин",
    "Asr": "Аср",
    "Maghrib": "Шом",
    "Isha": "Хуфтон",
}
BOT_FOOTER = "🤖 @XOJAOBODCITY24BOT"
PRAYER_ENCOURAGEMENTS = (
    "Намоз — қалбга хотиржамлик, ҳаётга баракадир. Намозингизни вақтида адо этинг.",
    "Намозни ўз вақтида адо этишга шошилинг ва қалбингизни зикр билан обод қилинг.",
    "Кунлик ишлар орасида намоз учун вақт ажратишни унутманг.",
    "Намоз вақти — қалбни тинчлантириш ва Роббини ёд этиш фурсатидир.",
    "Ҳар бир намозни эътибор ва хушуъ билан адо этишга интилинг.",
)


@dataclass(frozen=True)
class PrayerTimesResult:
    requested_date: date
    api_date: date
    timings: dict[str, str]


@dataclass(frozen=True)
class MosqueReference:
    reference_date: date
    mosque_timings: dict[str, str]
    aladhan_timings: dict[str, str]
    offsets: dict[str, int]
    date_overrides: dict[str, dict[str, str]] = field(default_factory=dict)
    display_date: date | None = None


@dataclass(frozen=True)
class NextPrayer:
    key: str
    name: str
    at: datetime
    remaining_minutes: int


def _minutes(value: str) -> int:
    parsed = datetime.strptime(value, "%H:%M")
    return parsed.hour * 60 + parsed.minute


def _clock(total_minutes: int) -> str:
    normalized = total_minutes % (24 * 60)
    return f"{normalized // 60:02d}:{normalized % 60:02d}"


def load_mosque_reference(path: Path = REFERENCE_PATH) -> MosqueReference:
    with path.open(encoding="utf-8") as source:
        payload = json.load(source)
    reference_date = datetime.strptime(payload["reference_date"], "%Y-%m-%d").date()
    mosque = payload["mosque_timings"]
    aladhan = payload["aladhan_timings"]
    stored_offsets = payload.get("offsets_minutes", {})
    offsets = {
        key: int(stored_offsets.get(key, _minutes(mosque[key]) - _minutes(aladhan[key])))
        for key in PRAYER_KEYS
    }
    display_date_text = payload.get("display_date")
    display_date = (
        datetime.strptime(display_date_text, "%Y-%m-%d").date()
        if display_date_text
        else None
    )
    return MosqueReference(
        reference_date,
        mosque,
        aladhan,
        offsets,
        payload.get("date_overrides", {}),
        display_date,
    )


def apply_mosque_corrections(
    api_timings: dict[str, str], reference: MosqueReference
) -> dict[str, str]:
    return {
        key: _clock(_minutes(api_timings[key]) + reference.offsets[key])
        for key in PRAYER_KEYS
    }


def calculate_next_prayer(
    now: datetime,
    today_timings: dict[str, str],
    tomorrow_fajr: str | None = None,
) -> NextPrayer | None:
    if now.tzinfo is None:
        raise ValueError("Joriy vaqt timezone bilan berilishi kerak")

    candidates: list[tuple[str, datetime]] = []
    for key in PRAYER_KEYS:
        prayer_time = datetime.strptime(today_timings[key], "%H:%M").time()
        candidates.append((key, datetime.combine(now.date(), prayer_time, tzinfo=now.tzinfo)))

    if tomorrow_fajr is not None:
        fajr_time = datetime.strptime(tomorrow_fajr, "%H:%M").time()
        candidates.append(
            (
                "Fajr",
                datetime.combine(now.date() + timedelta(days=1), fajr_time, tzinfo=now.tzinfo),
            )
        )

    for key, prayer_at in candidates:
        if prayer_at > now:
            remaining_seconds = (prayer_at - now).total_seconds()
            remaining_minutes = max(1, int((remaining_seconds + 59) // 60))
            return NextPrayer(key, PRAYER_NAMES[key], prayer_at, remaining_minutes)
    return None


def format_next_prayer(next_prayer: NextPrayer) -> str:
    hours, minutes = divmod(next_prayer.remaining_minutes, 60)
    return with_bot_footer(
        f"🕌 Кейинги намоз: {next_prayer.name}\n"
        f"⏳ {hours} соат {minutes} дақиқа қолди"
    )


def encouragement_for_date(selected_date: date) -> str:
    return PRAYER_ENCOURAGEMENTS[selected_date.toordinal() % len(PRAYER_ENCOURAGEMENTS)]


def with_bot_footer(text: str) -> str:
    """Place one bot username footer at the very end of a prayer message."""
    lines = [line for line in text.rstrip().splitlines() if line.strip() != BOT_FOOTER]
    body = "\n".join(lines).rstrip()
    return f"{body}\n\n{BOT_FOOTER}" if body else BOT_FOOTER


def manual_prayer_timings(day: date) -> dict[str, str]:
    """Return only an owner/admin supplied timetable for the exact requested date.

    No web/API calculation or stale fallback is allowed. The historical
    reference date and explicit date_overrides are treated as manual entries.
    """
    reference = load_mosque_reference()
    if day == reference.reference_date:
        return {key: reference.mosque_timings[key] for key in PRAYER_KEYS}
    override = reference.date_overrides.get(day.isoformat())
    if override:
        return {key: override[key] for key in PRAYER_KEYS}
    raise RuntimeError(
        f"{day.isoformat()} учун қўлда тасдиқланган намоз жадвали йўқ"
    )


def fetch_prayer_times(day: date) -> PrayerTimesResult:
    """Compatibility wrapper around the manual-only timetable source."""
    timings = manual_prayer_timings(day)
    logger.info("Қўлдаги намоз жадвали санаси: %s", day.isoformat())
    return PrayerTimesResult(requested_date=day, api_date=day, timings=timings)

def format_prayer_message(timings: dict[str, str], selected_date: date) -> str:
    lines = [
        f"🕌 Намоз вақтлари: {selected_date:%d.%m.%Y} йил",
        "",
        f"🕔 Бомдод     {timings['Fajr']}",
        f"🕑 Пешин      {timings['Dhuhr']}",
        f"🕔 Аср        {timings['Asr']}",
        f"🕖 Шом        {timings['Maghrib']}",
        f"🕘 Хуфтон     {timings['Isha']}",
        "",
        "📅 Жадвал ҳар пайшанба янгиланади.",
    ]
    if selected_date.weekday() == 4:
        lines.extend(["", "Жума кунининг хайру баракати Сизга бўлсин."])
    return with_bot_footer("\n".join(lines))


def prayer_display_date(current_date: date) -> date:
    manual_prayer_timings(current_date)
    return current_date


async def prayer_section(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    try:
        selected_date = prayer_display_date(datetime.now(TASHKENT_TIMEZONE).date())
        timings = manual_prayer_timings(selected_date)
        text = format_prayer_message(timings, selected_date)
    except Exception:
        logger.exception("Namoz vaqtlarini olishda xato")
        text = (
            "⚠️ Бугунги намоз вақтларини манбадан тасдиқлаб бўлмади. "
            "Эски вақтлар кўрсатилмади. Бироздан кейин қайта уриниб кўринг."
        )
    await update.message.reply_text(
        with_bot_footer(text), reply_markup=prayer_keyboard(), parse_mode="HTML"
    )


async def next_prayer_section(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    try:
        now = datetime.now(TASHKENT_TIMEZONE)
        today_timings = manual_prayer_timings(now.date())
        next_prayer = calculate_next_prayer(now, today_timings)
        if next_prayer is None:
            try:
                tomorrow_fajr = manual_prayer_timings(now.date() + timedelta(days=1))["Fajr"]
            except RuntimeError:
                tomorrow_fajr = None
            next_prayer = calculate_next_prayer(now, today_timings, tomorrow_fajr)
        if next_prayer is None:
            raise RuntimeError("Keyingi namozni aniqlab bo‘lmadi")
        text = format_next_prayer(next_prayer)
    except Exception:
        logger.exception("Keyingi namozni aniqlashda xato")
        text = (
            "⚠️ Кейинги намоз вақтини манбадан тасдиқлаб бўлмади. "
            "Бироздан кейин қайта уриниб кўринг."
        )
    await update.message.reply_text(with_bot_footer(text), reply_markup=prayer_keyboard())


def prayer_handler() -> MessageHandler:
    return MessageHandler(filters.TEXT & filters.Regex(f"^{config.MENU_PRAYER}$"), prayer_section)


def next_prayer_handler() -> MessageHandler:
    return MessageHandler(
        filters.TEXT & filters.Regex(f"^{config.BTN_NEXT_PRAYER}$"),
        next_prayer_section,
    )
