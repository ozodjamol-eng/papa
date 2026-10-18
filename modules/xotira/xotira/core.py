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
    if re.search(r"[A-Za-z]", s):                     # имена — всегда узбекские: латиницу переводим всегда
        return translit.to_cyrillic(s)
    return s


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


# ---------- повторы (18.10, решение владельца) ----------
import difflib  # noqa: E402

_FOLD = str.maketrans({"ў": "у", "қ": "к", "ғ": "г", "ҳ": "х", "ё": "е", "э": "е", "ъ": "", "ь": "", "й": "и"})
OLD = re.compile(r"Марҳум:\s*(?P<n>.+?)\s*\n.*?Туғилган сана:\s*(?P<b>.+?)\s*\n.*?Вафот этган сана:\s*(?P<d>.+?)(?:\n|$)", re.S)


TITLES = {"хожи", "ҳожи", "хожа", "дада", "она", "ота", "тога", "тоға", "ая", "буви", "бувим", "бобо", "бобом", "ака",
          "опа", "домла", "марҳум", "мархум", "раҳматли", "рахматли"}


def key(name: str) -> str:
    """Ключ имени для сравнения: кириллица, без регистра, знаков и обращений (хожи, дада, она, тоға…);
    ў/у қ/к ғ/г ҳ/х — одно и то же."""
    n = _cyr(name or "").lower()
    words = [w for w in re.sub(r"[^a-zа-яёўқғҳ ]+", " ", n).split() if w not in TITLES]
    return " ".join(words).translate(_FOLD)


def extract(caption_text: str) -> list[dict]:
    """Люди из поста канала. Форматы: «ФИО 1942-2005-63 ёш», «ФИО» ⏎ «1928/2011/83 ёш», «1932й - 1964й»,
    старый «Марҳум: … Туғилган сана: …». Ничего не бросает: непонятное пропускается."""
    out = []
    t = caption_text or ""
    for m in OLD.finditer(t):
        b, d = re.search(r"\d{4}", m["b"]), re.search(r"\d{4}", m["d"])
        if b and d:
            out.append({"name": m["n"].strip(), "born": int(b[0]), "died": int(d[0])})
    if out:
        return out
    pending: list[str] = []                       # строки имени без цифр — до строки с годами
    for line in t.splitlines():
        line = line.strip()
        if not line or line.startswith("@") or re.fullmatch(r"[\W_]+", line):
            continue
        m = YEARS.search(line)
        if not m:
            if re.search(r"\d", line):
                pending = []
            else:
                pending = (pending + [line])[-2:]
            continue
        here = re.sub(r"[^\w\s'ʻ‘’-]+", " ", line[:m.start()]).strip()
        name = here if len(key(here)) >= 3 else " ".join(pending)
        if len(key(name)) >= 3 and 1880 <= int(m.group(2)) <= int(m.group(4)):
            out.append({"name": re.sub(r"\s+", " ", name).strip(" .,"), "born": int(m.group(2)), "died": int(m.group(4))})
        pending = []
    return out


def compare(person: dict, rec: dict) -> str | None:
    """'same' — то же имя и те же годы; 'similar' — имя похоже (или то же) — проверить глазами; None — другой человек."""
    a, b = key(person["name"]), key(rec["name"])
    same_years = person["born"] == rec["born"] and person["died"] == rec["died"]
    if a == b and same_years:
        return "same"
    wa, wb = a.split(), b.split()
    if len(wa) >= 2 and len(wb) >= 2 and wa[:2] == wb[:2]:       # отчество/обращение есть только в одном варианте
        return "same" if same_years else "similar"
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    if len(wa) >= 2 and len(wb) >= 2:                              # фамилия+имя похожи (опечатка), отчество не мешает
        ratio = max(ratio, difflib.SequenceMatcher(None, " ".join(wa[:2]), " ".join(wb[:2])).ratio())
    if same_years and ratio >= 0.85:
        return "same" if ratio >= 0.93 else "similar"
    if a == b or (ratio >= 0.9 and abs(person["died"] - rec["died"]) <= 1):
        return "similar"
    return None
