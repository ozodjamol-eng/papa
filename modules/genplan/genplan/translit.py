"""Узбекская латиница → кириллица (по правилам, без ИИ, бесплатно).
Не трогает: ссылки, @юзернеймы, #хэштеги, e-mail, бренды со смешанным регистром (PaparazziUZ, YouTube, TikTok)."""
from __future__ import annotations

import re

AP = "'‘’ʻʼ`´"
DIGRAPHS = [("o" + a, "ў") for a in AP] + [("g" + a, "ғ") for a in AP] + [
    ("sh", "ш"), ("ch", "ч"), ("yo", "ё"), ("yu", "ю"), ("ya", "я"), ("ye", "е")]
SINGLE = dict(zip("abdfghijklmnopqrstuvxyz", "абдфгҳижклмнопқрстувхйз"))
PROTECT = re.compile(r"(https?://\S+|www\.\S+|t\.me/\S+|[@#][\w_]+|\S+@\S+\.\w+)")
WORD = re.compile(r"[A-Za-z" + re.escape(AP) + r"]+")
UZ_MARK = re.compile(r"(?i)\b(va|bilan|uchun|bu|emas|yil|kuni|bo['‘’ʻ`]l|o['‘’ʻ`]z|qil|edi|ham|endi|yangi)\w*|[og]['‘’ʻ`]|q\w")


def _brand(w: str) -> bool:
    core = w.strip(AP)
    return any(c.isupper() for c in core[1:]) and not core.isupper()   # PaparazziUZ, YouTube; не «XO'JAOBOD»


def _word(w: str) -> str:
    if _brand(w):
        return w
    low, out, i = w.lower(), [], 0
    while i < len(w):
        two = low[i:i + 2]
        rep = next((c for d, c in DIGRAPHS if two == d), None)
        if two == "yo" and i + 2 < len(w) and w[i + 2] in AP:      # Yangiyo'l → Янгийўл
            rep = None
        if rep:
            src, i = w[i:i + 2], i + 2
        else:
            ch = low[i]
            if ch == "e":
                rep = "э" if i == 0 else "е"
            elif ch == "c":
                rep = "с"
            elif ch == "w":
                rep = "в"
            elif ch in AP:
                rep = "ъ" if i > 0 else ""          # тутуқ белгиси: ma'no → маъно
            else:
                rep = SINGLE.get(ch, ch)
            src, i = w[i], i + 1
        if src[0].isupper():
            rep = rep.upper() if (len(w) > 1 and w.isupper()) else rep.capitalize()
        out.append(rep)
    return "".join(out)


# 30.10 сверка (№6): короткая латиница («Juma muborak!») проходила без кириллицы — порог был ≥12 букв и ≥2 признака.
# Для текста совсем без кириллицы хватает одного частого узбекского слова или ўзак-признака (o'/g'), если нет английских слов.
UZ_WORDS = re.compile(r"(?i)(?<![\w'‘’ʻ`])(juma|muborak\w*|assalomu|as-salomu|aleykum|alaykum|salom|xayrli|tong\w*|kech\w*|tun\w*|"
                      r"kun\w*|uchun|bilan|rahmat|barchangiz\w*|barcha\w*|murodbaxsh|yangilik\w*|bugun\w*|ertaga|hayot\w*|"
                      r"yaxshi\w*|sog['‘’ʻ`]liq\w*|oila\w*|farzand\w*|duo\w*|namoz\w*|muborakbod|tabrik\w*|ota|ona\w*|"
                      r"jonli|ijro\w*|qadrli|aziz\w*|do['‘’ʻ`]st\w*|ko['‘’ʻ`]p|emas|yoki|lekin|nima\w*|qanday|qanaqa|siz\w*|biz\w*)(?![\w'‘’ʻ`])")
UZ_APOS = re.compile(r"(?i)\b\w*[og]['‘’ʻ`]\w+")
EN_WORDS = re.compile(r"(?i)\b(the|and|you|your|is|are|to|of|for|with|this|that|my|happy|new|good|best|day|love|from|in|on|at|it|we|our|be)\b")


def is_uz_latin(text: str) -> bool:
    plain = PROTECT.sub("", text or "")
    lat = len(re.findall(r"[A-Za-z]", plain))
    cyr = len(re.findall(r"[А-Яа-яЁёЎўҚқҒғҲҳ]", text or ""))
    if lat >= 12 and lat > cyr * 2 and len(UZ_MARK.findall(text)) >= 2:
        return True
    if cyr == 0 and lat >= 4 and not EN_WORDS.search(plain):          # короткий пост без кириллицы
        words = [w for w in WORD.findall(plain) if not _brand(w)]
        uz = len(UZ_WORDS.findall(plain)) + len(UZ_APOS.findall(plain))
        return uz >= 1 and uz * 3 >= len(words)                       # узбекские слова — не меньше трети
    return False


def to_cyrillic(text: str) -> str:
    parts = PROTECT.split(text or "")
    return "".join(p if PROTECT.fullmatch(p) else WORD.sub(lambda m: _word(m.group(0)), p) for p in parts)


def auto(text: str) -> tuple[str, bool]:
    """(текст, было_ли_преобразование). Кириллицу и другие языки не трогает."""
    return (to_cyrillic(text), True) if is_uz_latin(text) else (text, False)


RU_ONLY = re.compile(r"[ыщэьЫЩЭЬ]")
UZ_CYR = re.compile(r"[ЎўҚқҒғҲҳ]")
# 20.10: частые русские слова — у узбекского таких нет (раньше ловили только по ы/щ/э ≥3 и пропускали русские посты)
RU_WORDS = re.compile(r"(?<![а-яё])(и|не|в|на|что|это|как|для|с|по|вы|вас|ваш[а-я]*|если|или|но|от|за|все|всё|у|к|из|чтобы|только|очень|можно|нужно|стоит|который|которая|так|же|при)(?![а-яё])", re.I)


def is_russian(text: str) -> bool:
    t = text or ""
    cyr = len(re.findall(r"[А-Яа-яЁё]", t))
    if cyr < 20:
        return False
    uz = len(UZ_CYR.findall(t))
    if uz and uz * 40 >= cyr:            # заметно узбекских букв — это узбекский текст (возможны русские вставки)
        return False
    return len(RU_ONLY.findall(t)) >= 2 or len(RU_WORDS.findall(t)) >= 3


def language_note(text: str) -> str:
    """Подсказка владельцу в хабе: русский текст переводит ИИ (утверждено 20.10)."""
    if is_russian(text):
        return "🌐 Текст на русском — ИИ переводит на узбекский (кириллица)"
    return ""
