#!/usr/bin/env python3
"""«🕌 Намоз обои» (03.11.2026, шаблоны владельца NAMOZ_EDITOR): 5 обоев 1080×2400 с временем недели.

Владелец: «5 материалов кидаются вместе с готовым текстом — человек сам выбирает». Время — из «Намоз маркази»
(выгрузка PAPA /var/lib/papa-namaz/namaz.json); перерисовка только когда время изменилось. Координаты — из редактора
владельца (index.html, android). Результат: /var/lib/papa-namaz/oboi/<день>/{01..05}.jpg + caption.txt.
"""
import datetime as dt
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
STYLES = ("01_Rassvet", "02_Nochnaya_mechet", "03_Bely_mramor", "04_Zelenaya_priroda", "05_Nasledie_Uzbekistana")
POS = {"01_Rassvet": ((.50, .468), (.556, .598, .640, .683, .726)), "02_Nochnaya_mechet": ((.50, .468), (.556, .598, .640, .683, .726))}
POS_B = ((.50, .409), (.505, .550, .596, .641, .687))
X_TIME = .7135
NAMES = ("bomdod", "peshin", "asr", "shom", "xufton")
MONTHS = ("январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь")
CAPTION = ("🕌 <b>ХЎЖАОБОД ТУМАНИ — НАМОЗ ВАҚТЛАРИ</b>\n\n📅 {week}\n\n"
           "🕔 Бомдод — <b>{bomdod}</b>\n🕑 Пешин — <b>{peshin}</b>\n🕒 Аср — <b>{asr}</b>\n"
           "🕔 Шом — <b>{shom}</b>\n🕖 Хуфтон — <b>{xufton}</b>\n\n"
           "🤲 Аллоҳ барчамизнинг ибодатларимизни қабул қилсин!\n\n"
           "📱 Ёққан расмни сақлаб, телефонингизга обои қилиб қўйинг.\n"
           "📿 Зикр, дуо ва эслатмалар: @XOJAOBODCITY24BOT\n"
           "⚠️ Вақтлар фақат Хўжаобод тумани учун.")


def week_label(day: dt.date) -> str:
    end = day + dt.timedelta(days=7)
    a = f"{day.day} {MONTHS[day.month - 1]}"
    return f"{a} – {end.day} {MONTHS[end.month - 1]} {end.year} йил"


def text(draw, xy, s, size, fill, stroke):
    f = ImageFont.truetype(str(HERE / "assets" / "DejaVuSerif-Bold.ttf"), size)
    draw.text(xy, s, font=f, fill=fill, anchor="mm", stroke_width=max(2, round(size * .065)), stroke_fill=stroke)


def render(row: dict, out: Path) -> list[Path]:
    day = dt.date.fromisoformat(row["day"])
    week = week_label(day)
    out.mkdir(parents=True, exist_ok=True)
    files = []
    for i, st in enumerate(STYLES, 1):
        im = Image.open(HERE / "assets" / f"{st}_android.jpg").convert("RGB")
        w, h = im.size
        d = ImageDraw.Draw(im)
        (dx, dy), rows = POS.get(st, POS_B)
        size = 40                                  # сана пиллага сиғсин (DejaVu Georgia'дан кенгроқ)
        fnt = lambda z: ImageFont.truetype(str(HERE / "assets" / "DejaVuSerif-Bold.ttf"), z)
        while size > 22 and d.textlength(week, font=fnt(size)) > .58 * w:
            size -= 1
        text(d, (dx * w, dy * 2400), week, size, "#FFF9E9", "#0c2745")
        for n, y in zip(NAMES, rows):
            text(d, (X_TIME * w, y * 2400), row[n], 54, "#081632", "#fff9e8")
        f = out / f"{i:02d}_{st}.jpg"
        im.save(f, quality=92)
        files.append(f)
    (out / "caption.txt").write_text(CAPTION.format(week=week, **{n: row[n] for n in NAMES}), encoding="utf-8")
    return files


def current(schedule: list[dict], today: dt.date) -> dict | None:
    rows = [r for r in schedule if r.get("day", "") <= today.isoformat()]
    return rows[-1] if rows else None


def main() -> int:
    src = Path(os.getenv("PAPA_NAMAZ_JSON", "/var/lib/papa-namaz/namaz.json"))
    base = Path(os.getenv("PAPA_NAMAZ_OBOI", "/var/lib/papa-namaz/oboi"))
    row = current(json.loads(src.read_text(encoding="utf-8"))["schedule"], dt.date.today())
    if not row:
        print("обои: нет времени"); return 0
    key = row["day"] + "_" + "-".join(row[n].replace(":", "") for n in NAMES)
    out = base / key
    if not (out / "caption.txt").exists():
        render(row, out)
        print("обои: нарисованы", key)
    (base / "CURRENT").write_text(key + "\n", encoding="utf-8")
    for p in [base, out, *out.iterdir()]:
        os.chmod(p, 0o755 if p.is_dir() else 0o644)
    return 0


if __name__ == "__main__":
    sys.exit(main())
