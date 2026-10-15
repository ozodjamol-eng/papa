import asyncio
import datetime as dt
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import plan, publish, text  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
X, P = CFG["channels"]["xojaobod"], CFG["channels"]["paparazzi"]
MON = dt.date(2026, 10, 19)   # понедельник
SUN = dt.date(2026, 10, 18)   # воскресенье
T0 = dt.datetime(2026, 10, 15, 10, 0, tzinfo=plan.TZ)


def M(i, rubric, ch=None, minutes=0):
    return plan.Material(i, rubric, T0 + dt.timedelta(minutes=minutes), ch)


class TestGrid(unittest.TestCase):
    def test_config_sane(self):
        for name, ch in CFG["channels"].items():
            times = [s["t"] for s in ch["slots"]]
            self.assertEqual(len(times), len(set(times)), name)
            for s in ch["slots"]:
                self.assertIn(s["kind"], ("anchor", "content", "ad", "music"))
        self.assertEqual(sum(1 for s in P["slots"] if s["kind"] == "content"), 10)  # решение владельца: 10 в день
        self.assertEqual([s["t"] for s in X["slots"] if s["kind"] == "ad"],
                         ["07:30", "09:40", "11:50", "15:10", "17:40", "20:10"])

    def test_sunday_ad_limit(self):
        self.assertEqual(sum(1 for s in plan.day_slots(X, MON) if s["kind"] == "ad"), 6)
        self.assertEqual(sum(1 for s in plan.day_slots(X, SUN) if s["kind"] == "ad"), 4)


class TestPlan(unittest.TestCase):
    def test_rubrics_fallback_and_empty(self):
        mats = [M(1, "Янгиликлар"), M(2, "Ҳажвия", minutes=1), M(3, "Видео", minutes=2)]
        p = plan.build("xojaobod", X, MON, mats, ads={})
        by = {e.at.strftime("%H:%M"): e for e in p}
        self.assertEqual(by["07:00"].status, plan.AUTO)
        self.assertEqual(by["08:15"].material_id, 1)          # «Тонг» нет → запасная «Янгиликлар»
        self.assertIn("вместо", by["08:15"].note)
        self.assertEqual(by["12:40"].material_id, 2)
        self.assertEqual(by["09:00"].status, plan.EMPTY)       # новость уже ушла в 08:15 — второй раз не идёт
        ids = [e.material_id for e in p if e.material_id]
        self.assertEqual(len(ids), len(set(ids)))              # один материал — один слот

    def test_free_ad_window_goes_to_content_not_self_promo(self):
        mats = [M(1, "Ҳажвия")]
        p = plan.build("xojaobod", X, MON, mats, ads={"09:40": 77})
        by = {e.at.strftime("%H:%M"): e for e in p}
        self.assertEqual((by["09:40"].status, by["09:40"].ad_id), (plan.AD, 77))
        self.assertEqual(by["12:40"].material_id, 1)           # рубрика важнее свободного окна
        self.assertEqual(by["07:30"].status, plan.FREE)        # лишнего материала нет — окно пустует, без самопиара
        p = plan.build("xojaobod", X, MON, [M(i, "Ҳажвия", minutes=i) for i in range(1, 5)], ads={})
        by = {e.at.strftime("%H:%M"): e for e in p}
        self.assertEqual((by["07:30"].kind, by["07:30"].material_id), ("content", 4))  # 3 ушли в рубрики 12:40, 16:00, 21:00; лишний материал → в окно

    def test_channel_isolation(self):
        mats = [M(1, "Видео", ch="paparazzi"), M(2, "Видео", ch="xojaobod", minutes=1)]
        p = plan.build("paparazzi", P, MON, mats, ads={})
        self.assertEqual({e.material_id for e in p if e.material_id}, {1})

    def test_due_and_ready(self):
        mats = [M(1, "Шоу-бизнес янгилик")]
        now = plan.slot_time(MON, "08:20")
        p = plan.build("paparazzi", P, MON, mats, ads={}, now=now)
        self.assertEqual(p[0].status, plan.READY)
        self.assertEqual([e.at.strftime("%H:%M") for e in plan.due(p, plan.slot_time(MON, "08:31"))], ["08:30"])
        self.assertEqual(plan.due(p, plan.slot_time(MON, "09:30")), [])  # опоздали больше чем на 20 мин — не публикуем

    def test_published_kept(self):
        p = plan.build("paparazzi", P, MON, [M(1, "Видео")], ads={}, published={"08:30": plan.DONE})
        self.assertEqual(p[0].status, plan.DONE)

    def test_render(self):
        out = plan.render("PaparazziUZ", plan.build("paparazzi", P, MON, [M(1, "Қўшиқ")], ads={}))
        self.assertIn("📅 План на сегодня", out)
        self.assertIn("⚠️ Нет материала", out)


class TestText(unittest.TestCase):
    def test_strip_and_sign(self):
        src = "Янгилик матни\n\n👉 @bugungi_gap\nhttps://t.me/bugungi_gap\nМанба: @kunuzofficial"
        out = text.finalize(src, "👉 @XOJAOBODCITY24")
        self.assertNotIn("bugungi", out)
        self.assertNotIn("kunuz", out)
        self.assertTrue(out.endswith("👉 @XOJAOBODCITY24"))
        self.assertTrue(out.startswith("Янгилик матни"))

    def test_ads_untouched_and_no_double_sign(self):
        ad = "Чегирма! @shop_bot +998901234567"
        self.assertEqual(text.finalize(ad, "👉 @X", is_ad=True), ad)
        self.assertEqual(text.finalize("Матн\n👉 @XOJAOBODCITY24", "👉 @XOJAOBODCITY24", own=("XOJAOBODCITY24",)).count("XOJAOBODCITY24"), 1)


class TestHook(unittest.TestCase):
    CH = {"hooks": ["A", "B"], "rubric_hooks": {"Мусиқа": ["M1", "M2"]}, "cross": {"every": 5, "text": "X"}}

    def test_rotation_rubric_cross(self):
        self.assertEqual([text.pick_hook(self.CH, "Видео", n) for n in range(4)], ["A", "B", "A", "B"])
        self.assertEqual(text.pick_hook(self.CH, "Мусиқа", 1), "M2")
        self.assertEqual(text.pick_hook(self.CH, "Мусиқа", 4), "X")
        self.assertEqual(text.pick_hook({}, "Видео", 3), "")

    def test_footer_survives_caption_limit(self):
        out = text.finalize("ж" * 2000, "🎉 @kattadavrauz", hook="🔔 Хук", limit=1024)
        self.assertLessEqual(len(out), 1024)
        self.assertTrue(out.endswith("🔔 Хук\n🎉 @kattadavrauz"))
        out2 = text.finalize("Матн\n🎉 @kattadavrauz", "🎉 @kattadavrauz", own=("kattadavrauz",), hook="🔔 Хук")
        self.assertEqual(out2, "Матн\n\n🔔 Хук\n🎉 @kattadavrauz")


class TestSmartHook(unittest.TestCase):
    import tomllib as _t
    CFG = _t.load(open(Path(__file__).parent.parent / "config.toml", "rb"))
    D = CFG["channels"]["davra"]

    def h(self, body, n=1, rubric="Видео"):
        return text.pick_hook(self.D, rubric, n, body, self.CFG["topics"])

    def test_topics(self):
        self.assertIn("Об-ҳаво", self.h("Эртага кучли ёмғир ёғади", n=0))
        self.assertIn("Кулдингизми", self.h("Бу видео 😂😂", n=0))
        self.assertEqual(self.h("Машҳур актёр вафот этди"), "")              # печаль — без хука
        self.assertEqual(self.h("Ретро видео\nЁқса, реакция қолдиринг!"), "")  # свой призыв уже есть
        self.assertNotIn("Об-ҳаво", self.h("Бошлади ишни"))                  # нет ложных совпадений

    def test_translit(self):
        out = text.finalize("Xo'jaobodda yangi bozor ochildi, bugun ko'ring va do'stlarga ayting", "🎉 @kattadavrauz")
        self.assertTrue(out.startswith("Хўжаободда янги бозор очилди"))
        self.assertIn("@kattadavrauz", out)
        ru = "Сегодня в Ташкенте прошла выставка"
        self.assertTrue(text.finalize(ru, "").startswith(ru))


class FakeHTTP:
    def __init__(self, ok=True):
        self.calls, self.ok = [], ok

    def __call__(self, method, payload):
        self.calls.append((method, payload))
        return {"ok": True, "result": {"message_id": 42}} if self.ok else {"ok": False, "description": "Forbidden"}


class TestPublish(unittest.TestCase):
    def test_bot_copy_media_and_text(self):
        h = FakeHTTP()
        b = publish.BotPublisher("t", http=h)
        self.assertEqual(b.publish("@ozodjamoll", "caption", -100, 5, has_media=True), 42)
        self.assertEqual(h.calls[0][0], "copyMessage")          # без «переслано из»
        b.publish("@ozodjamoll", "just text", button={"text": "📲", "url": "https://t.me/share/url?url=x"})
        self.assertEqual(h.calls[1][0], "sendMessage")
        self.assertEqual(h.calls[1][1]["reply_markup"]["inline_keyboard"][0][0]["text"], "📲")

    def test_bot_error(self):
        with self.assertRaises(publish.PublishError):
            publish.BotPublisher("t", http=FakeHTTP(ok=False)).publish("@x", "t")

    def test_account_publisher(self):
        class Msg:
            def __init__(self, i, media=None):
                self.id, self.media = i, media

        class FakeClient:
            def __init__(self):
                self.sent = []

            async def get_messages(self, chat, ids):
                return Msg(ids, media="PHOTO")

            async def send_file(self, chat, media, caption):
                self.sent.append(("file", chat, media, caption)); return Msg(7)

            async def send_message(self, chat, txt):
                self.sent.append(("msg", chat, txt)); return Msg(8)

        c = FakeClient()
        a = publish.AccountPublisher(c)
        self.assertEqual(asyncio.run(a.publish("xojaobodcity24", "cap", -100, 3, has_media=True)), 7)
        self.assertEqual(asyncio.run(a.publish("xojaobodcity24", "txt")), 8)
        self.assertEqual(c.sent[0][2], "PHOTO")


if __name__ == "__main__":
    unittest.main()
