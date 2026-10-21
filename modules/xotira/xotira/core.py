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


# 19.10, владелец: пост ушёл в канал без имени («Йош 1979-2020-41 ёш») — такое пресекать.
# Служебные слова не считаются именем: их убираем, а для поста нужны минимум 2 слова имени (фамилия + исм).
SERVICE = {"йош", "ёш", "ёши", "йоши", "yosh", "yoshi", "туғилган", "тугилган", "вафот", "этган", "етган", "йил", "йили",
           "й", "сана", "санаси", "марҳум", "мархум", "марҳума", "мархума", "раҳматли", "рахматли", "ёшида", "йошида",
           "ёшда", "йошда", "тавалуд", "хотира", "фио", "исм", "фамилия"}


def _strip_service(name: str) -> str:
    words = [w for w in name.split(" ") if w.strip(".,:;!?()«»\"'").lower() not in SERVICE]
    return " ".join(words).strip(" .,:;-–—")


def name_ok(name: str) -> bool:
    """Есть ли настоящее имя: ≥ 2 слова из букв (≥ 2 буквы), не служебные и не обращения (хожи, ота, она…)."""
    real = [w for w in re.findall(r"[^\W\d_][^\W\d_'ʻ‘’-]*", name or "")
            if len(w) >= 2 and w.lower() not in SERVICE and w.lower() not in TITLES]
    return len(real) >= 2


T_NO_NAME = "«{line}» — марҳумнинг исм-фамилияси ёзилмаган. Тўлиқ ёзинг, масалан: Қосимов Қўчқарвой 1942-2005"


AGE_TAIL = re.compile(r"^\s*[-–—/]?\s*\d{1,3}\s*(?:ёш|йош|ёшда|yosh)?\b\.?", re.I)


def clean_name(raw: str) -> str:
    """19.10, владелец: в посте — ТОЛЬКО фамилия и имя. Обращения (хожи, дада, эна, ота…), служебные слова и цифры убираем."""
    n = _name(re.sub(r"\d+", " ", raw))
    words = [w for w in n.split(" ") if w and w.strip(".,:;!?()«»\"'").lower() not in SERVICE | TITLES]
    return " ".join(words).strip(" .,:;-–—")


def parse(text: str, today: dt.date | None = None) -> list[dict]:
    """«ФИО 1942-2005» (одна или две на строке) или «ФИО» ⏎ «1942-2005» → [{"name", "born", "died", "age"}].
    Ошибка — BadInput с понятным (узб.) текстом. Возраст всегда считаем сами из годов."""
    today = today or dt.date.today()
    people, pending = [], ""
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        ms = list(YEARS.finditer(line))
        if not ms:
            if re.search(r"\d", line):
                raise BadInput(f"«{line}» — йилларни 1942-2005 кўринишида ёзинг.")
            pending = line                            # имя на отдельной строке, годы — на следующей
            continue
        prev = 0
        for i, m in enumerate(ms):
            seg = AGE_TAIL.sub("", line[prev:m.start()])           # «-94 ёш» от предыдущего человека
            tail = line[m.end():] if i == len(ms) - 1 else ""
            tail = AGE_TAIL.sub("", tail)
            raw = (seg + " " + tail).strip()
            if not clean_name(raw) and pending:
                raw = pending
            pending = ""
            name = clean_name(raw)
            prev = m.end()
            if len(name) < 3 or not name_ok(name):
                raise BadInput(T_NO_NAME.format(line=line))
            born, died = int(m.group(2)), int(m.group(4))
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
    """19.10, владелец: имя-фамилия — строкой, годы — ПОД именем (не сбоку)."""
    blocks = [f"{p['name']}\n{p['born']}-{p['died']}-{p['age']} ёш" for p in people]
    return "\n\n".join(blocks + [footer])


# ---------- повторы (18.10, решение владельца) ----------
import difflib  # noqa: E402

_FOLD = str.maketrans({"ў": "у", "қ": "к", "ғ": "г", "ҳ": "х", "ё": "е", "э": "е", "ъ": "", "ь": "", "й": "и"})
OLD = re.compile(r"Марҳум:\s*(?P<n>.+?)\s*\n.*?Туғилган сана:\s*(?P<b>.+?)\s*\n.*?Вафот этган сана:\s*(?P<d>.+?)(?:\n|$)", re.S)


TITLES = {"хожи", "ҳожи", "хожа", "ҳожа", "хожия", "ҳожия", "эна", "ена", "ойи", "ойижон", "дадажон", "момо", "мома", "хола",
          "амаки", "тоғажон", "холажон", "бувижон", "бобожон", "опажон", "акажон", "домлажон", "ҳожиона", "хожиона",
          "дада", "она", "ота", "тога", "тоға", "ая", "буви", "бувим", "бобо", "бобом", "ака",
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


def _r(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def compare(person: dict, rec: dict) -> str | None:
    """'same' — то же имя и те же годы; 'similar' — имя похоже (или то же) — проверить глазами; None — другой человек.
    21.10: люди обходили проверку — меняли годы, писали фамилию иначе (Рахмов/Раҳмонов), меняли местами имя и фамилию.
    Теперь похожее имя показываем владельцу ПРИ ЛЮБЫХ годах; «same» (бот сам отвечает «уже есть») — только при точных годах."""
    a, b = key(person["name"]), key(rec["name"])
    same_years = person["born"] == rec["born"] and person["died"] == rec["died"]
    if a == b:
        return "same" if same_years else "similar"
    wa, wb = a.split(), b.split()
    if len(wa) >= 2 and len(wb) >= 2:
        if wa[:2] == wb[:2] or sorted(wa[:2]) == sorted(wb[:2]):   # отчество есть в одном варианте / имя и фамилия местами
            return "same" if same_years else "similar"
        pair = max(min(_r(wa[0], wb[0]), _r(wa[1], wb[1])), min(_r(wa[0], wb[1]), _r(wa[1], wb[0])))
        if same_years and pair >= 0.93:
            return "same"
        if pair >= 0.8:                                             # обе части имени похожи (опечатка, другое написание)
            return "similar"
        if same_years and (wa[1] == wb[1] or wa[0] == wb[0]) and min(len(wa[0]), len(wa[1])) >= 3:
            return "similar"                                        # годы точь-в-точь, одна часть имени та же
        return None
    ratio = _r(a, b)
    if same_years and ratio >= 0.85:
        return "same" if ratio >= 0.93 else "similar"
    if ratio >= 0.9:
        return "similar"
    return None
