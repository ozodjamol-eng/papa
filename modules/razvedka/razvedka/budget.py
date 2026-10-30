"""💡 30.10 полный аудит: один бесплатный ключ Gemini на всех (ассистент, GENPLAN, Разведка).
Фоновая Разведка (куратор, архивариус, тренды, приколы, хабы, папки) тратит Gemini только пока:
  1) страж не включил «экономию» (флаг-дата `gemini-saver` — пишет papa_audit при лимите/429);
  2) за день всеми вместе израсходовано меньше BACKGROUND_SHARE от GEMINI_DAY_BUDGET.
Ассистент и GENPLAN (хуки, перевод, проверка кадров) этим не ограничиваются — они первые.
Счётчик — общий файл в /var/lib/papa-sources-choice (пишут papa-genplan и papa-razvedka; группа papa-razvedka, 2770).
Нет доступа к файлу — не мешаем работе (только флаг экономии). Откат: GEMINI_BACKGROUND_SHARE=1 в ai.env."""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

TZ = dt.timezone(dt.timedelta(hours=5))
def _shared() -> Path:
    return Path(os.environ.get("PAPA_GEMINI_DIR", "/var/lib/papa-sources-choice"))
# Бесплатный дневной лимит Gemini делят все; число — с запасом (flash-lite ≈ 1000/день, flash меньше).
DAY_BUDGET = int(os.environ.get("GEMINI_DAY_BUDGET", "600"))
BACKGROUND_SHARE = float(os.environ.get("GEMINI_BACKGROUND_SHARE", "0.6"))
SAVER_FILES = ("/var/lib/papa-genplan/gemini-saver",)   # + SHARED/gemini-saver


class BudgetStop(RuntimeError):
    """Фоновой Разведке сегодня Gemini не тратим — бережём лимит для ассистента и постов."""


def _today(now: dt.datetime | None = None) -> str:
    return (now or dt.datetime.now(TZ)).astimezone(TZ).date().isoformat()


def saver_on(now: dt.datetime | None = None, shared: Path | None = None) -> bool:
    today = _today(now)
    for p in (*SAVER_FILES, str((shared or _shared()) / "gemini-saver")):
        try:
            if Path(p).read_text(encoding="utf-8").strip() == today:
                return True
        except OSError:
            continue
    return False


def used(now: dt.datetime | None = None, shared: Path | None = None) -> int:
    try:
        day, n = (Path(shared or _shared()) / "gemini-count").read_text(encoding="utf-8").split()[:2]
        return int(n) if day == _today(now) else 0
    except (OSError, ValueError):
        return 0


def spend(n: int = 1, now: dt.datetime | None = None, shared: Path | None = None) -> int:
    """+n к общему счётчику дня (с блокировкой). Ошибка доступа — молча 0: счётчик не должен ломать работу."""
    p = Path(shared or _shared()) / "gemini-count"
    try:
        import fcntl
        with open(p, "a+", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0)
            parts = f.read().split()
            today = _today(now)
            cur = int(parts[1]) if len(parts) >= 2 and parts[0] == today and parts[1].isdigit() else 0
            f.seek(0)
            f.truncate()
            f.write(f"{today} {cur + n}\n")
        try:
            os.chmod(p, 0o660)
        except OSError:
            pass
        return cur + n
    except OSError:
        return 0


def background_ok(now: dt.datetime | None = None, shared: Path | None = None) -> tuple[bool, str]:
    if saver_on(now, shared):
        return False, "экономия Gemini (страж): фоновая Разведка ждёт до завтра"
    u, cap = used(now, shared), int(DAY_BUDGET * BACKGROUND_SHARE)
    if u >= cap:
        return False, f"Gemini за день {u}/{DAY_BUDGET}: фоновой Разведке хватит ({cap}) — остаток ассистенту и постам"
    return True, ""


def gate(now: dt.datetime | None = None, shared: Path | None = None) -> None:
    """Перед каждым запросом фоновой Разведки к Gemini: можно → +1 к счётчику; нельзя → BudgetStop."""
    ok, why = background_ok(now, shared)
    if not ok:
        raise BudgetStop(why)
    spend(1, now, shared)
