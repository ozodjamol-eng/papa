#!/usr/bin/env python3
"""«🕌 Намоз обои» (06.11.2026 v3, шаблоны владельца из ChatGPT): обои на весь экран с пустой рамкой.

Владелец 06.11: «все эти фоны с пустым шаблоном утверждаю… впредь, если буду менять фоны, буду так использовать этот
шаблон… когда намаз хотят видеть, пускай выходят все варианты». Старые шаблоны 1080×2400 были картинкой с мутными
полосами — на телефоне выглядело «не до конца». Код вписывает только неделю (в синюю ленту) и 5 времён (в кремовые плашки),
шрифт — жирный засечный, как названия на шаблоне. Новый фон = положить PNG в assets/v3 + строку в TEMPLATES.
Результат: /var/lib/papa-namaz/oboi/<день_время_v3>/{01..}.jpg + caption.txt.
"""
import datetime as dt
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
VERSION = "v3"
FRAME_1290 = {"date": (646, 1120, 500, 42), "times": (901, (1392, 1523, 1650, 1778, 1909), 70)}   # одна рамка у всех 1290×2796
TEMPLATES = [   # (файл, разметка). 03_Tong_masjid — двойная рамка (брак ChatGPT): включить, только если владелец скажет
    ("01_Bogcha.png", {"date": (471, 690, 345, 30), "times": (657, (885, 983, 1072, 1165, 1265), 50)}),
    ("02_Samarqand.png", FRAME_1290),
    ("04_Tungi_masjid.png", FRAME_1290),
    ("05_Tungi_fonus.png", FRAME_1290),
    ("06_Vodiy.png", FRAME_1290),
]
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


def fnt(size: int):
    return ImageFont.truetype(str(HERE / "assets" / "DejaVuSerif-Bold.ttf"), size)


def text(draw, xy, s, size, fill, stroke):
    draw.text(xy, s, font=fnt(size), fill=fill, anchor="mm", stroke_width=max(2, round(size * .06)), stroke_fill=stroke)


def render(row: dict, out: Path, templates=None) -> list[Path]:
    day = dt.date.fromisoformat(row["day"])
    week = week_label(day)
    out.mkdir(parents=True, exist_ok=True)
    files = []
    for i, (name, lay) in enumerate(templates or TEMPLATES, 1):
        im = Image.open(HERE / "assets" / VERSION / name).convert("RGB")
        d = ImageDraw.Draw(im)
        cx, cy, maxw, size = lay["date"]
        while size > 16 and d.textlength(week, font=fnt(size)) > maxw:      # неделя сама влезает в ленту
            size -= 1
        text(d, (cx, cy), week, size, "#FFF6DC", "#0b1d45")
        tx, ys, ts = lay["times"]
        for n, y in zip(NAMES, ys):
            text(d, (tx, y), row[n], ts, "#0b1838", "#fffaf0")
        f = out / f"{i:02d}_{Path(name).stem}.jpg"
        im.save(f, quality=93)
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
    key = row["day"] + "_" + "-".join(row[n].replace(":", "") for n in NAMES) + "_" + VERSION
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
