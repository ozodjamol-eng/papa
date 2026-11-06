"""🕰 06.11 владелец: «Хайрли тонг — это хайрли тонг… такие вещи он должен различать; либо научи, либо отсеивай».
Текст, привязанный ко времени суток/дню недели (утро, Жума, «хайрли тун»), не лежит в вечных хабах направлений —
он живёт в отдельном хабе «ТАБРИКЛАР», а GENPLAN выпускает такие тексты только в своё время.
Правило без ИИ: мгновенно и бесплатно. Тот же словарь — в genplan/smart.py (GREET): менять оба места вместе."""
from __future__ import annotations

import re

GREET = {
    "juma": re.compile(r"жума\w*[\s_]*(?:айём\w*[\s_]*)?муборак|juma\w*[\s_]*(?:ayyom\w*[\s_]*)?muborak"),
    "morning": re.compile(r"хайрли[\s_]*тонг|тонги[\s_]*муборак|тонгингиз|xayrli[\s_]*tong|tongi[\s_]*muborak|tongingiz"),
    "night": re.compile(r"хайрли[\s_]*(?:тун|кеч)\b|тунингиз|xayrli[\s_]*(?:tun|kech)\b|tuningiz"),
}
HUB = "ТАБРИКЛАР"
NAMES = {"juma": "Жума", "morning": "Тонг", "night": "Тун"}


def kind(text: str | None) -> str | None:
    s = str(text or "").casefold()
    for k, rx in GREET.items():
        if rx.search(s):
            return k
    return None
