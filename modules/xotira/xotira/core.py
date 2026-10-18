"""ХОТИРА МАРКАЗИ — логика без сети: разбор «ФИО 1942-2005», возраст, подпись поста как в канале.

Формат поста (как в ХОТИРА КАНАЛИ ХЎЖАОБОД):
    Қосимов Қўчқарвой 1942-2005-63 ёш

    Қосимова Мўътабархон 1942-2026-84 ёш

    @XOTIRAXOJAOBOD
"""
from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "genplan"))
try:
    from genplan import translit          # латиница → кириллица (общая для PAPA)
except Exception:  # noqa: BLE001
    translit = None

MAX_PEOPLE = 2
YEARS = re.compile(r"((?:\d{1,2}[./]\d{1,2}[./])?(\d{4}))\s*(?:й\.?|йил|yil)?\s*[-–—~/ ]+\s*((?:\d{1,2}[./]\d{1,2}[./])?(\d{4}))")


class BadInput(ValueError):
    pass


def _cyr(s: str) -> str:
    if translit is None:
        return s
    out, _ = translit.auto(s)
    return out


def _name(raw: str) -> str:
    n = re.sub(r"[\s,;:–—-]+$", "", raw.strip())
    n = re.sub(r"^[\s•\-–—*\d.)]+", "", n)          # «1) », «- », «• »
    n = re.sub(r"\s+", " ", n)
    n = _cyr(n)
    if n and (n.islower() or n.isupper()):            # «қосимов қўчқарвой» / «ҚОСИМОВ» → «Қосимов Қўчқарвой»
        n = " ".join(w[:1].upper() + w[1:].lower() for w in n.split(" "))
    return n


def parse(text: str, today: dt.date | None = None) -> list[dict]:
    """Строки «ФИО 1942-2005» → [{"name", "born", "died", "age"}]. Ошибка — BadInput с понятным (узб.) текстом."""
    today = today or dt.date.today()
    people = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        m = YEARS.search(line)
        if not m:
            if re.search(r"\d", line):
                raise BadInput(f"«{line}» — йилларни 1942-2005 кўринишида ёзинг.")
            continue                                   # пустые/служебные строки без цифр пропускаем
        born, died = int(m.group(2)), int(m.group(4))
        name = _name(line[:m.start()] + " " + line[m.end():])
        name = re.sub(r"\s*\d+\s*ёш\s*$|\s*\d+\s*yosh\s*$", "", name).strip()
        if len(name) < 3:
            raise BadInput(f"«{line}» — исм-фамилия ёзилмаган.")
        if not (1880 <= born <= died <= today.year):
            raise BadInput(f"«{line}» — йиллар нотўғри: туғилган йил вафот йилидан олдин бўлиши керак.")
        if died - born > 120:
            raise BadInput(f"«{line}» — ёш 120 дан ошиб кетди, йилларни текширинг.")
        people.append({"name": name, "born": born, "died": died, "age": died - born})
    if not people:
        raise BadInput("Маълумот топилмади. Намуна: Қосимов Қўчқарвой 1942-2005")
    if len(people) > MAX_PEOPLE:
        raise BadInput(f"Бир постда кўпи билан {MAX_PEOPLE} киши бўлади. Ҳар бир жуфтлик учун алоҳида юборинг.")
    return people


def caption(people: list[dict], footer: str) -> str:
    lines = [f"{p['name']} {p['born']}-{p['died']}-{p['age']} ёш" for p in people]
    return "\n\n".join(lines + [footer])
