"""Выбор рубрики как в пульте Хўжаобода (GENPLAN 5, архив 07.10: telegram_ui._add_post_root_keyboard,
dynamic_rubrics.APPROVED_*_TOPICS, hashtag_catalog.SUBCATEGORY_DEFAULT_TAGS).

Экран 1: 6 групп + 💡 Фойдали / ❤️ Соғлиқ + 🚨 Срочный пост + 🌙 Якуний пост.
Экран 2: подрубрики группы (по одной в ряд, по 10 на страницу).
Подрубрика = смысл поста → ОДИН хэштег (решение владельца 17.10: «только один, двойных не будет»)
и место в сетке канала (рубрика расписания — по карте kind → рубрика канала)."""
from __future__ import annotations

# (код, эмодзи, название, хэштег, kind) — kind решает рубрику расписания в конкретном канале
GROUPS: list[tuple[str, str, list[tuple[str, str, str, str, str]]]] = [
    ("news", "📰 Новости", [
        ("news_big_local", "📍", "ХЎЖАОБОД / АНДИЖОН", "#ХЎЖАОБОД", "local"),
        ("news_big_uzbekistan", "🇺🇿", "ЎЗБЕКИСТОН", "#ЎЗБЕКИСТОН", "news"),
        ("news_big_world", "🌍", "ДУНЁ", "#ДУНЁ", "news"),
        ("news_big_urgent", "🚨", "ТЕЗКОР / ОГОҲЛАНТИРУВ", "#ТЕЗКОР", "news"),
        ("news_big_official", "🏛", "РАСМИЙ / ҲОКИМИЯТ", "#РАСМАН", "news"),
        ("news_big_society_law", "⚖️", "ЖАМИЯТ / ҚОНУН", "#ЖАМИЯТ", "news"),
        ("news_big_incidents", "🚔", "ҲОДИСА / ЖИНОЯТ", "#ҲОДИСА", "news"),
        ("news_big_economy_business", "💼", "ИҚТИСОД / БИЗНЕС", "#ИҚТИСОД", "news"),
        ("news_big_jobs_migration", "👷", "ИШ / МИГРАЦИЯ", "#ИШ", "news"),
        ("news_big_market_prices", "💰", "БОЗОР / НАРХ / ВАЛЮТА", "#БОЗОР", "news"),
        ("news_big_transport_auto", "🚗", "ЙЎЛ / ТРАНСПОРТ / АВТО", "#ЙЎЛЛАР", "news"),
        ("news_big_utilities", "💡", "ГАЗ / СУВ / ЭЛЕКТР", "#ГАЗ", "news"),
        ("news_big_health", "❤️", "СОҒЛИҚ / ТИББИЁТ", "#САЛОМАТЛИК", "news"),
        ("news_big_education", "🎓", "ТАЪЛИМ / ЁШЛАР", "#ТАЪЛИМ", "news"),
        ("news_big_agriculture", "🌾", "ҚИШЛОҚ ХЎЖАЛИГИ", "#ҚИШЛОҚ_ХЎЖАЛИГИ", "news"),
        ("news_big_weather_ecology", "🌦", "ОБ-ҲАВО / ЭКОЛОГИЯ", "#ОБ_ҲАВО", "news"),
        ("news_big_tech_cyber", "🛡", "КИБЕР / ФИРИБГАРЛИК / ТЕХНОЛОГИЯ", "#ТЕХНОЛОГИЯ", "news"),
        ("news_big_sport", "⚽", "СПОРТ", "#СПОРТ", "sport"),
        ("news_big_culture_events", "🎭", "МАДАНИЯТ / ТАДБИР", "#МАДАНИЯТ", "news"),
        ("news_big_viral", "🔥", "ШОВ-ШУВ / ҚИЗИҚ", "#ШОВ_ШУВ", "news"),
    ]),
    ("video", "🎬 Видео", [
        ("video_big_oila_munosabat", "👨‍👩‍👧", "ОИЛА ВА МУНОСАБАТ", "#ОИЛА", "health"),
        ("video_big_bola_tarbiya", "👶", "БОЛА ВА ТАРБИЯ", "#ФАРЗАНД", "health"),
        ("video_big_erkaklar", "👨", "ЭРКАКЛАР", "#ЭРКАКЛАР", "useful"),
        ("video_big_ayollar", "👩", "АЁЛЛАР", "#АЁЛЛАР", "useful"),
        ("video_big_sogliq", "❤️", "СОҒЛИҚ", "#САЛОМАТЛИК", "health"),
        ("video_big_psixologiya", "🧠", "ПСИХОЛОГИЯ", "#ПСИХОЛОГИЯ", "useful"),
        ("video_big_foydali_maslahat", "💡", "ФОЙДАЛИ МАСЛАҲАТ", "#ФОЙДАЛИ", "useful"),
        ("video_big_uy_ruzgor", "🏠", "УЙ-РЎЗҒОР", "#УЙ_РЎЗҒОР", "useful"),
        ("video_big_ovqat_retsept", "🍳", "ОВҚАТ / РЕЦЕПТ", "#РЕЦЕПТ", "health"),
        ("video_big_diniy_marifiy", "🕌", "ДИНИЙ / МАЪРИФИЙ", "#ДИНИЙ_МАЪРИФАТ", "culture"),
        ("video_big_kongilochar", "🎭", "КЎНГИЛОЧАР", "#КЎНГИЛОЧАР", "interesting"),
        ("video_big_kulgili_qiziq", "😂", "КУЛГИЛИ / ҚИЗИҚ", "#КУЛГУ", "humor"),
        ("video_big_tasirli_ibratli", "😢", "ТАЪСИРЛИ / ИБРАТЛИ", "#ИБРАТ", "interesting"),
        ("video_big_musiqa_sanat", "🎵", "МУСИҚА / САНЪАТ", "#МУСИҚА", "music"),
        ("video_big_sport", "⚽", "СПОРТ", "#СПОРТ", "sport"),
        ("video_big_tarix_arxiv", "📚", "ТАРИХ / АРХИВ", "#ТАРИХ", "retro"),
        ("video_big_talim_bilim", "🎓", "ТАЪЛИМ / БИЛИМ", "#ТАЪЛИМ", "useful"),
        ("video_big_ish_biznes", "💼", "ИШ / БИЗНЕС", "#БИЗНЕС", "business"),
        ("video_big_pul_moliya", "💰", "ПУЛ / МОЛИЯ", "#ПУЛ", "business"),
        ("video_big_savdo_bozor", "🛒", "САВДО / БОЗОР", "#САВДО", "business"),
        ("video_big_dolzarb_ogohlantiruv", "🚨", "ДОЛЗАРБ / ОГОҲЛАНТИРУВ", "#ДОЛЗАРБ", "useful"),
        ("video_big_xojaobod_andijon", "📍", "ХЎЖАОБОД / АНДИЖОН", "#ХЎЖАОБОД", "local"),
        ("video_big_uzbekiston_dunyo", "🌍", "ЎЗБЕКИСТОН / ДУНЁ", "#ЎЗБЕКИСТОН", "video"),
        ("video_big_avto", "🚗", "АВТО", "#АВТО", "useful"),
        ("video_big_usta_qurilish_layfxak", "🛠", "УСТА / ҚУРИЛИШ / ЛАЙФХАК", "#ЛАЙФХАК", "useful"),
        ("video_big_qishloq_dehqonchilik", "🌾", "ҚИШЛОҚ / ДЕҲҚОНЧИЛИК", "#ДЕҲҚОНЧИЛИК", "useful"),
        ("video_big_chorva_hayvonlar", "🐄", "ЧОРВА / ҲАЙВОНЛАР", "#ЧОРВА", "useful"),
        ("video_big_tabiat", "🌿", "ТАБИАТ", "#ТАБИАТ", "video"),
        ("video_big_boshqa", "❓", "БОШҚА / АНИҚЛАНМАГАН", "", "video"),
    ]),
    ("entertainment", "😂 Юмор", [
        ("ent_big_humor", "😂", "КУЛГУ / ЮМОР", "#КУЛГУ", "humor"),
        ("ent_big_funny_video", "🤣", "КУЛГИЛИ ВИДЕО", "#КУЛГУ", "humor"),
        ("ent_big_life", "😄", "ҲАЁТИЙ ҲОЛАТ", "#ТАНИШ_ҲОЛАТ", "humor"),
        ("ent_big_family", "👨‍👩‍👧", "ОИЛАВИЙ ЮМОР", "#ОИЛАВИЙ_ЮМОР", "humor"),
        ("ent_big_interesting", "😲", "ҚИЗИҚ / ҲАЙРАТЛАНАРЛИ", "#ҚИЗИҚ_ЛАВҲА", "interesting"),
        ("ent_big_meme", "📱", "МЕМ / ТРЕНД", "#МЕМ", "humor"),
        ("ent_big_vine", "🎥", "ВАЙН / СКЕТЧ", "#ВАЙН", "humor"),
        ("ent_big_askiya", "🎭", "АСКИЯ", "#АСКИЯ", "humor"),
        ("ent_big_comedy_show", "🎪", "КУЛГУ КОНЦЕРТИ", "#КУЛГУ_КОНЦЕРТИ", "humor"),
        ("ent_big_prank", "😜", "ПРАНК / ШЎХЛИК", "#ШЎХЛИК", "humor"),
        ("ent_big_animals", "🐾", "ҲАЙВОНЛАР / ҚИЗИҚ", "#ҲАЙВОНЛАР", "humor"),
        ("ent_big_children", "👶", "БОЛАЛАР / ҚИЗИҚ", "#БОЛАЛАР", "humor"),
        ("ent_big_evening", "🌙", "КЕЧКИ КАЙФИЯТ", "#КЕЧКИ_КАЙФИЯТ", "evening"),
        ("ent_big_other", "🎉", "БОШҚА КЎНГИЛОЧАР", "#КЎНГИЛОЧАР", "interesting"),
    ]),
    ("music", "🎵 Музыка", [
        ("music_big_uzbek", "🇺🇿", "ЎЗБЕК МУСИҚАСИ", "#ЎЗБЕК_МУСИҚАСИ", "music"),
        ("music_big_world", "🌍", "ЖАҲОН МУСИҚАСИ", "#ЖАҲОН_МУСИҚАСИ", "music"),
        ("music_big_singer", "🎙", "КУН ХОНАНДАСИ", "#КУН_ХОНАНДАСИ", "singer"),
        ("music_big_song", "🎵", "КУН ТАРОНАСИ", "#КУН_ТАРОНАСИ", "music"),
        ("music_big_premiere", "🆕", "ПРЕМЬЕРА", "#ПРЕМЬЕРА", "premiere"),
        ("music_big_hit", "🔥", "ХИТ / ТРЕНД", "#БУГУНГИ_ХИТ", "music"),
        ("music_big_live", "🎹", "ЖОНЛИ ИЖРО", "#ЖОНЛИ_ИЖРО", "live"),
        ("music_big_retro", "💿", "РЕТРО", "#РЕТРО", "retro"),
        ("music_big_maqom", "🎼", "МАҚОМ / МИЛЛИЙ", "#МАҚОМ", "music"),
        ("music_big_lyric", "🎤", "ЛИРИК", "#ЛИРИК", "lyric"),
        ("music_big_emotional", "❤️", "ДАРДЛИ", "#ДАРДЛИ", "lyric"),
        ("music_big_mood", "🎧", "КАЙФИЯТ УЧУН", "#КАЙФИЯТ", "music"),
        ("music_big_evening", "🌙", "КЕЧКИ МУСИҚА", "#КЕЧКИ_МУСИҚА", "night_music"),
        ("music_big_cover", "🎸", "КАВЕР / ИНСТРУМЕНТАЛ", "#КАВЕР", "music"),
    ]),
    ("culture", "🎭 Культура / просвещение", [
        ("culture_big_religion", "🕌", "ДИНИЙ / МАЪРИФИЙ", "#ДИНИЙ_МАЪРИФАТ", "culture"),
        ("culture_big_enlightenment", "📖", "МАЪРИФАТ / БИЛИМ", "#МАЪРИФАТ", "culture"),
        ("culture_big_history", "📜", "ТАРИХ / АРХИВ", "#ТАРИХ", "retro"),
        ("culture_big_values", "🏛", "МИЛЛИЙ ҚАДРИЯТ", "#МИЛЛИЙ_ҚАДРИЯТ", "culture"),
        ("culture_big_traditions", "🪆", "УРФ-ОДАТ / АНЪАНА", "#УРФ_ОДАТ", "culture"),
        ("culture_big_art", "🎨", "САНЪАТ / МАДАНИЯТ", "#САНЪАТ", "culture"),
        ("culture_big_literature", "📚", "КИТОБ / АДАБИЁТ", "#КИТОБ", "culture"),
        ("culture_big_science", "🎓", "ТАЪЛИМ / ИЛМ-ФАН", "#ТАЪЛИМ", "culture"),
        ("culture_big_motivation", "💡", "МОТИВАЦИЯ / ИБРАТ", "#МОТИВАЦИЯ", "culture"),
        ("culture_big_event", "🎤", "ТАДБИР / КОНЦЕРТ", "#ТАДБИР", "culture"),
        ("culture_big_travel", "🗺", "САЁҲАТ / ЖОЙЛАР", "#САЁҲАТ", "culture"),
        ("culture_big_people", "👤", "МАШҲУР ИНСОНЛАР", "#МАШҲУР_ИНСОНЛАР", "people"),
        ("culture_big_language", "✍️", "ТИЛ / ЎЗБЕКЧА", "#ЎЗБЕК_ТИЛИ", "culture"),
        ("culture_big_craft", "🧵", "ҲУНАР / ҚЎЛ МЕҲНАТИ", "#ҲУНАР", "culture"),
        ("culture_big_other", "📘", "БОШҚА МАЪРИФИЙ", "#МАЪРИФАТ", "culture"),
    ]),
    ("community", "💬 Интерактив", [
        ("community_big_poll", "📊", "СЎРОВ", "#СЎРОВ", "community"),
        ("community_big_vote", "🗳", "ОВОЗ БЕРИШ", "#ОВОЗ_БЕРИШ", "community"),
        ("community_big_question", "❓", "САВОЛ", "#САВОЛ", "question"),
        ("community_big_opinion", "💬", "ФИКР СЎРАШ", "#ФИКР", "community"),
        ("community_big_discussion", "🗣", "МУҲОКАМА", "#МУҲОКАМА", "community"),
        ("community_big_appeal", "📢", "МУРОЖААТ / ЧАҚИРИҚ", "#МУРОЖААТ", "community"),
        ("community_big_problem", "⚠️", "МУАММО / ШИКОЯТ", "#МУАММО", "community"),
        ("community_big_idea", "💡", "ТАКЛИФ / ҒОЯ", "#ТАКЛИФ", "community"),
        ("community_big_help", "🤝", "ЁРДАМ / ХАЙРИЯ", "#ЁРДАМ", "community"),
        ("community_big_lost_found", "🔎", "ЙЎҚОЛГАН / ТОПИЛГАН", "#ЙЎҚОЛГАН", "community"),
        ("community_big_announcement", "📌", "ЭЪЛОН / ЖАМОА", "#ЭЪЛОН", "community"),
        ("community_big_thanks", "🙏", "ТАШАККУР / ТАБРИК", "#ТАШАККУР", "community"),
    ]),
]

# 💡 Фойдали — свои подтемы (как в GENPLAN 5, _FOYDALI_SUBTOPICS), один хэштег
USEFUL: list[tuple[str, str, str, str, str]] = [
    ("u_maslahat", "💡", "Маслаҳат", "#МАСЛАҲАТ", "useful"),
    ("u_lifehack", "🧠", "Лайфхак", "#ЛАЙФХАК", "useful"),
    ("u_internet", "📱", "Телефон / интернет", "#ИНТЕРНЕТ", "useful"),
    ("u_security", "🛡", "Хавфсизлик", "#ОГОҲЛИК", "useful"),
    ("u_law", "📋", "Ҳужжат / ҳуқуқ", "#ҲУҚУҚ", "useful"),
    ("u_saving", "💰", "Тежамкорлик", "#ТЕЖАМКОРЛИК", "useful"),
    ("u_online", "🌐", "Онлайн хизматлар", "#ОНЛАЙН", "useful"),
    ("u_daily", "🧰", "Кундалик ечим", "#ЛАЙФХАК", "useful"),
    ("u_knowledge", "📚", "Қизиқ билим", "#БИЛИМ", "useful"),
    ("u_career", "💼", "Иш / касб маслаҳати", "#КАСБ", "business"),
    ("u_business", "📈", "Бизнес ғоя", "#БИЗНЕС_ҒОЯ", "business"),
    ("u_other", "❓", "Бошқа фойдали", "#ФОЙДАЛИ", "useful"),
]
HEALTH = ("video_big_sogliq", "❤️", "Соғлиқ / саломатлик", "#САЛОМАТЛИК", "health")

# kind → рубрика сетки канала (у канала можно переопределить: picker_rubrics в config.toml)
KIND_RUBRIC = {
    "davra": {"news": "Янгиликлар", "local": "Янгиликлар", "useful": "Фойдали видео", "health": "Фойдали видео",
              "business": "Уйда бизнес", "sport": "Спорт", "humor": "Ҳажвия", "interesting": "Қизиқарли",
              "evening": "Кечки кучли пост", "music": "Мусиқа", "singer": "Мусиқа", "premiere": "Мусиқа",
              "live": "Мусиқа", "retro": "Қизиқарли", "lyric": "Мусиқа", "night_music": "Мусиқа",
              "culture": "Қизиқарли", "people": "Қизиқарли", "community": "Қизиқарли", "question": "Қизиқарли",
              "video": "Видео", "final": "Якуний пост"},
    "xojaobod": {"news": "Янгиликлар", "local": "Хўжаобод/Андижон", "useful": "Фойдали видео",
                 "health": "Соғлиқ/Оила", "business": "Фойдали видео", "sport": "Видео", "humor": "Ҳажвия",
                 "interesting": "Видео", "evening": "Кечки кучли пост", "music": "Лирик чекиниш",
                 "singer": "Кун хонандаси", "premiere": "Лирик чекиниш", "live": "Лирик чекиниш",
                 "retro": "Видео", "lyric": "Лирик чекиниш", "night_music": "Лирик чекиниш",
                 "culture": "Фойдали видео", "people": "Видео", "community": "Сўровнома",
                 "question": "Савол-жавоб", "video": "Видео", "final": "Якуний пост"},
    "paparazzi": {"news": "Шоу-бизнес янгилик", "local": "Шоу-бизнес янгилик", "useful": "Видео", "health": "Видео",
                  "business": "Видео", "sport": "Видео", "humor": "Ҳажвия", "interesting": "Видео",
                  "evening": "Видео", "music": "Қўшиқ", "singer": "Кун қўшиғи", "premiere": "Клип/премьера",
                  "live": "Жонли ижро", "retro": "Ретро хотира", "lyric": "Қўшиқ", "night_music": "Тунги қўшиқ",
                  "culture": "Видео", "people": "Юлдузлар ҳаёти", "community": "Видео", "question": "Видео",
                  "video": "Видео"},
}

PAGE = 10


def rubric_for(cfg: dict, channel: str, kind: str, rubrics: list[str]) -> str | None:
    m = {**KIND_RUBRIC.get(channel, {}), **(cfg["channels"][channel].get("picker_rubrics") or {})}
    r = m.get(kind) or m.get("video")
    return r if r in rubrics else (rubrics[0] if rubrics else None)


def items(group: str) -> list[tuple[str, str, str, str, str]]:
    if group == "useful":
        return USEFUL
    return next((g[2] for g in GROUPS if g[0] == group), [])


def item(group: str, idx: int):
    if group == "health":
        return HEALTH
    lst = items(group)
    return lst[idx] if 0 <= idx < len(lst) else None


def root_kb(mid: int, has_final: bool) -> list:
    """Экран 1 — как «➕ ПОСТ» в пульте Хўжаобода."""
    cells = [{"text": label, "callback_data": f"pg:{mid}:{code}:1"} for code, label, _ in GROUPS]
    rows = [cells[i:i + 2] for i in range(0, len(cells), 2)]
    rows.append([{"text": "💡 Фойдали", "callback_data": f"pg:{mid}:useful:1"},
                 {"text": "❤️ Соғлиқ / саломатлик", "callback_data": f"pi:{mid}:health:0"}])
    rows.append([{"text": "🚨 Срочный пост", "callback_data": f"ur:{mid}"}])
    if has_final:
        rows.append([{"text": "🌙 Якуний пост", "callback_data": f"pf:{mid}"}])
    return rows


def group_kb(mid: int, group: str, page: int = 1) -> tuple[str, list]:
    """Экран 2 — подрубрики группы, по одной в ряд, по 10 на страницу (как в GENPLAN 5)."""
    lst = items(group)
    pages = max(1, (len(lst) + PAGE - 1) // PAGE)
    page = max(1, min(page, pages))
    start = (page - 1) * PAGE
    rows = [[{"text": f"{e} {label}", "callback_data": f"pi:{mid}:{group}:{i}"}]
            for i, (_c, e, label, _t, _k) in enumerate(lst[start:start + PAGE], start)]
    if pages > 1:
        nav = []
        if page > 1:
            nav.append({"text": "⬅️ ОЛДИНГИ", "callback_data": f"pg:{mid}:{group}:{page - 1}"})
        nav.append({"text": f"{page}/{pages}", "callback_data": f"pg:{mid}:{group}:{page}"})
        if page < pages:
            nav.append({"text": "КЕЙИНГИ ➡️", "callback_data": f"pg:{mid}:{group}:{page + 1}"})
        rows.append(nav)
    rows.append([{"text": "⬅️ Назад", "callback_data": f"pr:{mid}"}])
    title = "💡 ФОЙДАЛИ\n\nМавзуни аниқ танланг:" if group == "useful" else \
        next((label for code, label, _ in GROUPS if code == group), group) + "\n\nВыберите подрубрику:"
    return title, rows
