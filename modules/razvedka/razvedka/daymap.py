"""Карта дня конкурентов (30.10, владелец: «сначала изучить конкурентов — и по ним режим дня»).

Для каждой папки-темы (XOJAOBODCITY, KATTA DAVRA …):
  • рубрика каждого поста — по словам в тексте (без ИИ, бесплатно);
  • по часам 05–23: что лидеры публикуют чаще всего и насколько сильный этот час;
  • сильные рубрики: доля в ленте и сила (просмотры / обычные для канала).
Свои каналы в карту не входят — только конкуренты. Чистые функции — проверяются тестами."""
from __future__ import annotations

from collections import Counter, defaultdict
from statistics import median

# рубрика: (код, подпись, слова); порядок = приоритет при совпадении нескольких
RUBRICS = [
    ("greet", "🌅 Тилак/салом", ("хайрли тонг", "xayrli tong", "тонгингиз", "tongingiz", "жума муборак", "juma muborak",
                                "хайрли тун", "xayrli tun", "хайрли кеч", "xayrli kech", "муборак бўлсин", "muborak bo'lsin")),
    ("scam", "⚠️ Огоҳлантириш", ("фирибгар", "firibgar", "эҳтиёт бўлинг", "ehtiyot bo'ling", "ehtiyot bo‘ling", "алдов",
                                "aldov", "огоҳ бўлинг", "ogoh bo'ling", "сохта", "soxta")),
    ("jobs", "💼 Иш ўринлари", ("иш ўрни", "иш ўринлари", "ish o'rni", "ish o‘rni", "вакансия", "vakansiya", "ишга марҳамат",
                               "ishga marhamat", "ишчи керак", "ishchi kerak", "ишга таклиф", "ishga taklif")),
    ("weather", "☀️ Об-ҳаво", ("об-ҳаво", "ob-havo", "ob havo", "погода", "ҳарорат", "harorat", "ёғингарчилик", "yog'ingarchilik")),
    ("money", "💵 Курс/пул", ("доллар", "dollar", "валюта", "valyuta", "курси", "kursi", "нархлар", "narxlar", "пенсия",
                             "pensiya", "маош", "maosh")),
    ("faith", "🕌 Маънавият", ("намоз", "ислом", "islom", "дуо ", "duo ", "муфтий", "muftiy", "шайх", "shayx", "қуръон",
                              "qur'on", "ҳадис", "hadis", "аллоҳ", "alloh", "пайғамбар", "payg'ambar")),
    ("food", "🍲 Таом/соғлиқ", ("таом", "taom", "рецепт", "retsept", "ошхона", "oshxona", "пишир", "pishir", "соғлиқ",
                               "sog'liq", "саломатлик", "salomatlik", "шифо", "shifo", "врач", "шифокор", "shifokor")),
    ("humor", "😂 Кулги", ("кулги", "kulgi", "ҳажвия", "hajviya", "юмор", "prikol", "прикол", "😂", "🤣", "латифа", "latifa")),
    ("music", "🎵 Мусиқа/шоу", ("қўшиқ", "qo'shiq", "qoshiq", "мусиқа", "musiqa", "клип", "klip", "хонанда", "xonanda",
                               "концерт", "konsert", "ижро", "ijro", "🎵", "🎶", "сериал", "serial")),
    ("sport", "⚽ Спорт", ("футбол", "futbol", "спорт", "sport", "матч", "чемпионат", "chempionat", "терма жамоа", "terma jamoa")),
    ("useful", "💡 Фойдали", ("фойдали", "foydali", "маслаҳат", "maslahat", "лайфхак", "layfxak", "биласизми", "bilasizmi",
                             "қандай қилиб", "qanday qilib", "сир", "sir ")),
    ("local", "📍 Андижон/Хўжаобод", ("андижон", "andijon", "хўжаобод", "xo'jaobod", "xo‘jaobod", "xojaobod", "водий", "vodiy")),
    ("news", "🗞 Янгилик", ("янгилик", "yangilik", "хабар", "xabar", "тезкор", "tezkor", "вазирлиги", "vazirligi",
                           "президент", "prezident", "қарор", "qaror", "ҳоким", "hokim", "#долзарб", "долзарб")),
]
NAME = {c: n for c, n, _ in RUBRICS} | {"ad": "📢 Реклама", "other": "🎞 Бошқа (без подписи)"}
NEWS_TITLE = ("янгилик", "yangilik", "хабар", "xabar", "tezkor", "тезкор", "news", "dunyo", "дунё", "uz |", "расмий", "rasmiy")
HOURS = range(5, 24)       # ночью не публикуем — смотрим 05:00–23:00
MIN_RUBRIC = 8             # постов, чтобы считать силу рубрики


def rubric(text: str, is_ad: bool, channel_title: str = "") -> str:
    if is_ad:
        return "ad"
    t = (text or "").lower()
    for code, _, words in RUBRICS:
        if any(w in t for w in words):
            return code
    if any(w in (channel_title or "").lower() for w in NEWS_TITLE) and len(t) > 40:
        return "news"
    return "other"


def build(posts: list[dict], chans: dict) -> list[dict]:
    """posts — из analyze.load (с local, ad; у созревших — rel). Возвращает карту по каждой папке-теме."""
    by_topic: dict[str, list[dict]] = defaultdict(list)
    for p in posts:
        ch = chans.get(p["channel_id"], {})
        if ch.get("is_own"):
            continue
        p["rubric"] = rubric(p.get("text") or "", p.get("ad", False), ch.get("title", ""))
        for topic in str(ch.get("folder") or "?").split(" + "):
            by_topic[topic.strip()].append(p)
    out = []
    for topic, ps in sorted(by_topic.items(), key=lambda kv: -len(kv[1])):
        total = len(ps)
        vol = Counter(p["rubric"] for p in ps)
        rel = defaultdict(list)
        for p in ps:
            if p.get("rel"):
                rel[p["rubric"]].append(p["rel"])
        rubrics = [{"code": c, "name": NAME[c], "share": round(100 * n / total), "posts": n,
                    "strength": round(median(rel[c]), 2) if len(rel[c]) >= MIN_RUBRIC else None}
                   for c, n in vol.most_common()]
        hours = []
        for h in HOURS:
            hp = [p for p in ps if p["local"].hour == h]
            if not hp:
                hours.append({"hour": h, "posts": 0, "top": [], "strength": None, "best": None})
                continue
            cnt = Counter(p["rubric"] for p in hp if p["rubric"] != "ad")
            top = [{"code": c, "name": NAME[c], "share": round(100 * n / len(hp))} for c, n in cnt.most_common(2)]
            hr = [p["rel"] for p in hp if p.get("rel")]
            # лучшая рубрика часа: самая сильная среди тех, где ≥3 созревших поста
            br = defaultdict(list)
            for p in hp:
                if p.get("rel") and p["rubric"] != "ad":
                    br[p["rubric"]].append(p["rel"])
            best = max(((c, median(v)) for c, v in br.items() if len(v) >= 3), key=lambda x: x[1], default=None)
            hours.append({"hour": h, "posts": len(hp), "top": top,
                          "ads": sum(1 for p in hp if p["rubric"] == "ad"),
                          "strength": round(median(hr), 2) if len(hr) >= 5 else None,
                          "best": {"code": best[0], "name": NAME[best[0]], "strength": round(best[1], 2)} if best else None})
        out.append({"topic": topic, "posts": total,
                    "channels": len({p["channel_id"] for p in ps}), "rubrics": rubrics, "hours": hours})
    return out


def render(maps: list[dict]) -> list[str]:
    L = []
    for m in maps:
        L.append(f"🗺 КАРТА ДНЯ КОНКУРЕНТОВ · {m['topic']} ({m['channels']} кан., {m['posts']} постов)")
        strong = [r for r in m["rubrics"] if r["strength"] is not None and r["code"] != "ad"]
        strong.sort(key=lambda r: r["strength"], reverse=True)
        if strong:
            L.append("  Рубрики (сила · доля ленты): " + " · ".join(
                f"{r['name']} ×{r['strength']} ({r['share']}%)" for r in strong[:8]))
        other = next((r for r in m["rubrics"] if r["code"] == "other"), None)
        if other:
            L.append(f"  Без понятной подписи: {other['share']}% постов")
        for h in m["hours"]:
            if not h["posts"]:
                continue
            top = ", ".join(f"{t['name']} {t['share']}%" for t in h["top"]) or "—"
            s = f" · сила ×{h['strength']}" if h["strength"] is not None else ""
            b = f" · сильнее всего: {h['best']['name']} ×{h['best']['strength']}" if h["best"] else ""
            ad = f" · 📢{h['ads']}" if h.get("ads") else ""
            L.append(f"  {h['hour']:02d}:00 ({h['posts']}) {top}{s}{b}{ad}")
        L.append("")
    return L
