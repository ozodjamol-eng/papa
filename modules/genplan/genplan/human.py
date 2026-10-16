"""«Очеловечиватель» и проверка заголовка (идея из instagram-agent-skill /ig-human и /ig-reel, MIT; переделано под
узбекскую кириллицу и стиль владельца).

clean()          — тихо чистит текст перед публикацией: невидимые символы-«водяные знаки» ИИ, неразрывные пробелы,
                   «!!!!» → «!». Тире не трогаем: в узбекском/русском «Бугун — …» это нормальная пунктуация.
headline_note()  — одна подсказка владельцу в карточке, если первая строка слабая. Ничего не переписывает и не блокирует.
"""
from __future__ import annotations

import re

# невидимые символы (ZWSP, LRM/RLM, bidi, word joiner, BOM, мягкий перенос). ZWJ (U+200D) и U+FE0F НЕ трогаем — из них
# собираются эмодзи 👨‍👩‍👧 и ❤️
INVISIBLE = re.compile("[​‌‎‏‪-‮⁠-⁤﻿­]")
NBSP = re.compile("[   ]")
REPEAT = re.compile(r"([!?.])\1{2,}")          # «!!!!» → «!», «....» → «…»

GREETING = re.compile(r"(?i)^\W*(ассалому?\s+алайкум|assalomu?\s+alaykum|салом|salom|ҳурматли\s+обуна|hurmatli\s+obuna|"
                      r"азиз(?:лар)?\s+обуна|aziz\s+obuna|привет|здравствуйте|всем\s+привет)")
CLICHE = ("хулоса қилиб айтганда", "шуни таъкидлаш жоизки", "таъкидлаш лозимки", "xulosa qilib aytganda",
          "в заключение", "стоит отметить, что", "важно отметить, что")
TAG_LINE = re.compile(r"^#\w+\s*$")
HEAD_MAX = 100       # длиннее — в уведомлении и превью видно только начало


def clean(text: str) -> str:
    t = INVISIBLE.sub("", text or "")
    t = NBSP.sub(" ", t)
    return REPEAT.sub(lambda m: "…" if m.group(1) == "." else m.group(1), t)


def _first_line(text: str) -> str:
    for ln in (text or "").splitlines():
        s = ln.strip()
        if s and not TAG_LINE.match(s):
            return s
    return ""


def headline_note(text: str) -> str:
    """Самая важная подсказка по заголовку или ''. Только одна — чтобы карточка не превращалась в лекцию."""
    head = _first_line(text)
    if not head:
        return ""
    if GREETING.match(head):
        return "💡 Начинается с приветствия — лучше сразу суть в первой строке."
    low = (text or "").lower()
    hit = next((c for c in CLICHE if c in low), "")
    if hit:
        return f"💡 «{hit}» — звучит как ИИ, лучше проще."
    if len(head) > HEAD_MAX:
        return "💡 Первая строка длинная — в уведомлении видно только начало."
    return ""
