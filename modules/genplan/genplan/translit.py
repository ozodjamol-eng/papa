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


def is_uz_latin(text: str) -> bool:
    lat = len(re.findall(r"[A-Za-z]", PROTECT.sub("", text or "")))
    cyr = len(re.findall(r"[А-Яа-яЁёЎўҚқҒғҲҳ]", text or ""))
    return lat >= 12 and lat > cyr * 2 and len(UZ_MARK.findall(text)) >= 2


def to_cyrillic(text: str) -> str:
    parts = PROTECT.split(text or "")
    return "".join(p if PROTECT.fullmatch(p) else WORD.sub(lambda m: _word(m.group(0)), p) for p in parts)


def auto(text: str) -> tuple[str, bool]:
    """(текст, было_ли_преобразование). Кириллицу и другие языки не трогает."""
    return (to_cyrillic(text), True) if is_uz_latin(text) else (text, False)


RU_ONLY = re.compile(r"[ыщэЫЩЭ]")
UZ_CYR = re.compile(r"[ЎўҚқҒғҲҳ]")


def language_note(text: str) -> str:
    """Подсказка владельцу в хабе: русский текст сам не переводится (это шаг ИИ)."""
    t = text or ""
    if len(RU_ONLY.findall(t)) >= 3 and not UZ_CYR.search(t):
        return "⚠️ Текст на русском — автоматически не переводится"
    return ""
