"""🕌 30.10 владелец: в 22:00 «Муфтий минбари» — только уроки (#muftiy_minbari), не поздравления (#tabrik);
у КАТТА ДАВРА и Хўжаобод Сити 24 посты Муфтия разные."""
import datetime as dt
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import plan, smart, store  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
MON = dt.date(2026, 10, 19)


def at(hhmm):
    return plan.slot_time(MON, hhmm)


class T(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")
        self.n = 0
        self.cfg = {**CFG, "channels": {k: dict(v) for k, v in CFG["channels"].items()}}

    def add(self, text, ch, fp=None):
        self.n += 1
        mid = store.add_material(self.db, -100777, self.n, text, True, fp=fp)
        store.update(self.db, mid, channel=ch, rubric=smart.MINBAR, status="draft", stock=1, auto=1)
        return mid

    def test_tabrik_not_in_minbar_slot(self):
        self.add("#tabrik\nЖума муборак!", "xojaobod", fp="m:a")
        self.assertEqual(smart.fill_from_stock(self.db, self.cfg, "xojaobod", at("21:00")), [])

    def test_minbar_lesson_goes(self):
        self.add("#tabrik\nЖума муборак!", "xojaobod", fp="m:a")
        lesson = self.add("#muftiy_minbari\nДарс", "xojaobod", fp="m:b")
        self.assertEqual(smart.fill_from_stock(self.db, self.cfg, "xojaobod", at("21:00")), [lesson])

    def test_channels_get_different_posts(self):
        self.add("#muftiy_minbari\nДарс 1", "davra", fp="m:1")
        self.add("#muftiy_minbari\nДарс 2", "davra", fp="m:2")
        x1 = self.add("#muftiy_minbari\nДарс 1", "xojaobod", fp="m:1")
        x2 = self.add("#muftiy_minbari\nДарс 2", "xojaobod", fp="m:2")
        d = smart.fill_from_stock(self.db, self.cfg, "davra", at("21:00"))
        x = smart.fill_from_stock(self.db, self.cfg, "xojaobod", at("21:00"))
        self.assertEqual(len(d), 1)
        self.assertEqual(x, [x2])                      # Дарс 1 уже взял КАТТА ДАВРА → Хўжаобод берёт другой
        self.assertNotEqual(store.get(self.db, d[0])["fp"], store.get(self.db, x[0])["fp"])
        self.assertNotIn(x1, x)

    def test_same_lesson_not_repeated_in_own_channel(self):
        """31.10: урок «Соғлом турмуш тарзи» вышел в Хўжаобод два дня подряд — копия того же поста из запаса."""
        old = self.add("#muftiy_minbari\nДарс 1", "xojaobod", fp="m:1")
        store.update(self.db, old, status="published", stock=0)
        self.add("#muftiy_minbari\nДарс 1", "xojaobod", fp="m:1")
        new = self.add("#muftiy_minbari\nДарс 2", "xojaobod", fp="m:2")
        self.assertEqual(smart.fill_from_stock(self.db, self.cfg, "xojaobod", at("21:00")), [new])

    def test_final_post_off_in_config(self):
        """31.10 владелец: «остальное лишнее убрать» — в 22:00 только Муфтий, Якуний пост выключен."""
        self.assertNotIn("final_post", CFG["channels"]["xojaobod"])

    def test_minbar_beyond_day_limit(self):
        """31.10: КАТТА ДАВРА — лимит 20 кончился к 20:30, Муфтий не вышел. Час Муфтия — вне лимита."""
        lesson = self.add("#muftiy_minbari\nДарс", "davra", fp="m:1")
        other = self.add("видео", "davra", fp="v:1")
        store.update(self.db, other, rubric="Мусиқа")
        for i in range(25):
            self.db.execute("INSERT INTO pulse(channel, at, source) VALUES (?,?,?)", ("davra", at("08:00").isoformat(), "bot"))
        self.db.commit()
        self.assertLessEqual(smart.day_room(self.db, self.cfg, "davra", at("21:00")), 0)
        self.assertEqual(smart.fill_from_stock(self.db, self.cfg, "davra", at("21:00")), [lesson])
        self.assertEqual(store.get(self.db, lesson)["scheduled_at"], at("22:00").isoformat())

    def test_needs_orders_lesson_when_stock_is_not_lesson(self):
        """31.10: в запасе Давры был только #kun_oyati — заказ думал, что 22:00 закрыт. Теперь час заказывается."""
        from genplan import needs
        self.add("#kun_oyati\nОят", "davra", fp="m:k")
        d = needs.build(self.db, self.cfg, at("20:00"))["channels"]["davra"]
        self.assertIn("22", [e["h"] for e in d["empty"]])


if __name__ == "__main__":
    unittest.main()
