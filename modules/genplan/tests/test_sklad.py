"""📦 26.10 владелец: склады — доверенный материал. Пост из склада → 📦 запас с рубрикой склада,
сам выходит в свободный час, в пульте не меньше чем за 30 минут видна строка с 🗑."""
import datetime as dt
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import hub, plan, service, smart, store  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
MON = dt.date(2026, 10, 19)


def at(hhmm, day=MON):
    return plan.slot_time(day, hhmm)


class Bot:
    def __init__(self):
        self.calls = []

    def __call__(self, method, **p):
        self.calls.append((method, p))
        return {"message_id": 900 + len(self.calls)}


def fwd(mid, title, text="Фойдали маслаҳат: уйда нон", chat_id=-1001, username=None):
    chat = {"id": chat_id, "title": title, "type": "channel"}
    if username:
        chat["username"] = username
    return {"message_id": mid, "from": {"id": 42}, "chat": {"id": 42, "type": "private"},
            "photo": [{"file_id": f"f{mid}", "file_unique_id": f"u{mid}"}], "caption": text,
            "forward_origin": {"type": "channel", "chat": chat}}


class T(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")
        self.cfg = {**CFG, "channels": {k: dict(v) for k, v in CFG["channels"].items()}}

    def test_config_maps_rubrics_that_exist(self):
        for ch in ("davra", "xojaobod", "paparazzi"):
            c = self.cfg["channels"][ch]
            for rub in c["sklad"].values():
                self.assertIn(rub, c["hashtags"], f"{ch}: {rub}")
        self.assertEqual(smart.sklad_rubric(self.cfg["channels"]["davra"], "📦 Фойдалик"), "Фойдали видео")
        self.assertIsNone(smart.sklad_rubric(self.cfg["channels"]["davra"], "@bugungi_gap"))
        self.assertIsNone(smart.sklad_rubric(self.cfg["channels"]["davra"], "Jonlik ijrolar"))  # не склад Давры

    def test_intake_from_sklad_goes_to_stock(self):
        bot = Bot()
        m = fwd(10, "ФОЙДАЛИК")
        hub.intake(bot, self.db, self.cfg, {42}, 42, [10], [m], reply_chat=42, channel="davra")
        r = store.get(self.db, 1)
        self.assertEqual((r["stock"], r["status"], r["rubric"], r["channel"]), (1, "draft", "Фойдали видео", "davra"))
        txt = bot.calls[-1][1]["text"]
        self.assertIn("📦 Склад «ФОЙДАЛИК»", txt)
        self.assertNotIn("Куратор нашёл", txt)

    def test_ordinary_forward_not_stock(self):
        bot = Bot()
        hub.intake(bot, self.db, self.cfg, {42}, 42, [11], [fwd(11, "BUGUNGI GAP")], reply_chat=42, channel="davra")
        self.assertEqual(store.get(self.db, 1)["stock"], 0)

    def test_chosen_source_goes_to_stock_auto(self):
        import json, tempfile
        from genplan import sources_choice
        f = Path(tempfile.mkdtemp()) / "choice.json"
        f.write_text(json.dumps({"version": 2, "channels": {"davra": {"news": [{"id": 1234567890, "title": "BUGUNGI GAP"}]}}}))
        old, sources_choice.CHOICE = sources_choice.CHOICE, f
        try:
            bot = Bot()
            hub.intake(bot, self.db, self.cfg, {42}, 42, [12], [fwd(12, "BUGUNGI GAP", "Янгилик матни",
                                                                    chat_id=-1001234567890, username="BugungiGap")],
                       reply_chat=42, channel="davra")
            r = store.get(self.db, 1)
            self.assertEqual((r["stock"], r["auto"]), (1, 1))
            self.assertIn("📡 Ваш источник @BugungiGap", bot.calls[-1][1]["text"])
            hub.intake(Bot(), self.db, self.cfg, {42}, 42, [13], [fwd(13, "Чужой", "Бошқа", chat_id=-1009999)],
                       reply_chat=42, channel="davra")
            self.assertEqual(store.get(self.db, 2)["stock"], 0)                      # не выбран — карточка, как раньше
            self.assertFalse(sources_choice.is_chosen("paparazzi", -1001234567890))  # выбран только для Давры
        finally:
            sources_choice.CHOICE = old

    def test_chosen_source_stale_after_12h(self):
        mid = store.add_material(self.db, 42, 3, "Эски янгилик", True)
        store.update(self.db, mid, channel="davra", rubric="Янгиликлар", status="draft", stock=1, auto=1,
                     source="@BugungiGap", created_at=(at("10:00") - dt.timedelta(hours=13)).isoformat())
        self.assertEqual(smart.fill_from_stock(self.db, self.cfg, "davra", at("10:00")), [])

    def test_fill_respects_30_min_lead_and_notice(self):
        mid = store.add_material(self.db, 42, 1, "Склад пост", True)
        store.update(self.db, mid, channel="davra", rubric="Фойдали видео", status="draft", stock=1, source="ФОЙДАЛИК")
        now = at("10:40")                                     # 11:00 — через 20 мин: рано для склада → 12:00
        ids = smart.fill_from_stock(self.db, self.cfg, "davra", now)
        self.assertEqual(ids, [mid])
        self.assertEqual(dt.datetime.fromisoformat(store.get(self.db, mid)["scheduled_at"]).strftime("%H:%M"), "12:00")
        store.update(self.db, mid, status="draft", stock=1, scheduled_at=None)
        now = at("10:25")                                     # 11:00 — через 35 мин: можно
        ids = smart.fill_from_stock(self.db, self.cfg, "davra", now)
        self.assertEqual(ids, [mid])
        self.assertEqual(dt.datetime.fromisoformat(store.get(self.db, mid)["scheduled_at"]).strftime("%H:%M"), "11:00")
        bot = Bot()
        n = service.sklad_notice(self.db, self.cfg, {"OWNER_IDS": "42"}, "davra", ids, now, bot=bot)
        self.assertEqual(n, 1)
        p = bot.calls[0][1]
        self.assertIn("выйдет сам в 11:00", p["text"])
        self.assertEqual(p["reply_markup"]["inline_keyboard"][0][0]["callback_data"], f"del:{mid}")

    def test_notice_ignores_non_sklad(self):
        mid = store.add_material(self.db, 42, 2, "Обычный запас", True)
        store.update(self.db, mid, channel="davra", rubric="Видео", status="queued", scheduled_at=at("11:00").isoformat())
        self.assertEqual(service.sklad_notice(self.db, self.cfg, {"OWNER_IDS": "42"}, "davra", [mid], at("10:00"), bot=Bot()), 0)


if __name__ == "__main__":
    unittest.main()
