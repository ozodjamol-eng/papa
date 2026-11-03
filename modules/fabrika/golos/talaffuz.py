"""Талаффуз PAPA (03.11.2026): матнни озвучкадан олдин «оғзаки» ёзувга ўтказиш + асосий голос.

Владелец: «биринчи» деб ўқияпти, ўзбекча гапда «бирнчи». Экран/пост — тўғри имло, TTS га — эшитилгандек.
Луғат — talaffuz.json (сўз ўзаги → талаффуз). Сўз бошидан мос келса, қўшимчаси сақланади: «биринчидан» → «бирнчидан».
voice.py буни ҳар tts қадамида ишлатади (ўчириш: "talaffuz": false).
"""
import json, re
from pathlib import Path

# ГЛАВНЫЙ голос PAPA (03.11.2026, владелец: «сделать этот голос самым главным в наших проектах»)
# = голос Умры: клон диктора «Jannatim» SAFO-MARVA-diktor, вариант C (docs/brand/safo-marva/README.md)
ASOSIY = {
    "voice_id": "ph7cEBlVHFfCY5GiGvA2",
    "name": "SAFO-MARVA-diktor",
    "model": "eleven_v4",
    "settings": {"stability": 0.55, "similarity_boost": 0.9, "style": 0.1},
}

_DICT = Path(__file__).with_name("talaffuz.json")


def lugat(path=_DICT):
    return json.loads(Path(path).read_text(encoding="utf-8")).get("sozlar", {})


def _case(src, dst):
    if src.isupper() and len(src) > 1:
        return dst.upper()
    if src[:1].isupper():
        return dst[:1].upper() + dst[1:]
    return dst


def tayyorla(text, sozlar=None, undov=True):
    """Матн → озвучка матни. Қайтаради (янги_матн, [(эски, янги), ...])."""
    sozlar = lugat() if sozlar is None else sozlar
    ozgar = []
    for stem in sorted(sozlar, key=len, reverse=True):
        rx = re.compile(r"(?<![\w'ʻʼ])" + re.escape(stem), re.IGNORECASE)

        def rep(m, stem=stem):
            new = _case(m.group(0), sozlar[stem])
            ozgar.append((m.group(0), new))
            return new
        text = rx.sub(rep, text)
    if undov and "!" in text:  # «!» — голос бақиради (safo-marva README)
        text = text.replace("!", ".")
        ozgar.append(("!", "."))
    return text, ozgar


def asosiy_qadam(st):
    """tts қадамида voice_id йўқ ёки "$asosiy" бўлса — асосий голос ва унинг созламалари."""
    if st.get("voice_id") in (None, "", "$asosiy"):
        st["voice_id"] = ASOSIY["voice_id"]
        st.setdefault("model", ASOSIY["model"])
        st.setdefault("settings", dict(ASOSIY["settings"]))
    return st
