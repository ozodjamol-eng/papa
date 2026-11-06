"""🕰 06.11 разбор: в 20:00 в Хўжаобод из запаса МАЪНАВИЯТ вышел «🕌 ЖУМА МУБОРАК…» с #ХАЙРЛИ_ТОНГ —
утреннее поздравление вечером. Поздравления/прощания выходят только в своё время дня."""
import datetime as dt
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import plan, smart, store  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
FRI = dt.date(2026, 11, 6)
SAT = dt.date(2026, 11, 7)


def at(day, hhmm):
    return plan.slot_time(day, hhmm)


class Kind(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual(smart.greet_kind("🕌 ЖУМА МУБОРАК Масжидда жамланган мўминлар"), "juma")
        self.assertEqual(smart.greet_kind("🌙 ЖУМА АЙЁМИНГИЗ МУБОРАК БЎЛСИН!"), "juma")
        self.assertEqual(smart.greet_kind("#Хайрли_тонг азизлар"), "morning")
        self.assertEqual(smart.greet_kind("Xayrli tong, do'stlar"), "morning")
        self.assertEqual(smart.greet_kind("Хайрли тун, яқинларим"), "night")
        self.assertIsNone(smart.greet_kind("🤲 ҲАЁТИЙ ПАНД-НАСИҲАТЛАР"))
        self.assertIsNone(smart.greet_kind("Кечаси совуқ бўлади"))

    def test_times(self):
        j = "🕌 ЖУМА МУБОРАК"
        self.assertTrue(smart.greet_ok(j, at(FRI, "09:00")))
        self.assertFalse(smart.greet_ok(j, at(FRI, "20:00")))     # тот самый случай
        self.assertFalse(smart.greet_ok(j, at(SAT, "09:00")))
        self.assertTrue(smart.greet_ok("Хайрли тонг", at(SAT, "07:00")))
        self.assertFalse(smart.greet_ok("Хайрли тонг", at(SAT, "14:00")))
        self.assertFalse(smart.greet_ok("Хайрли тун", at(SAT, "20:00")))
        self.assertTrue(smart.greet_ok("Обычный пост", at(SAT, "20:00")))


class Stock(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")
        self.cfg = {**CFG, "channels": {k: dict(v) for k, v in CFG["channels"].items()}}
        self.n = 0

    def add(self, text, rubric="Маънавият"):
        self.n += 1
        mid = store.add_material(self.db, -100777, self.n, text, True, fp=f"m:{self.n}")
        store.update(self.db, mid, channel="xojaobod", rubric=rubric, status="draft", stock=1, auto=1,
                     created_at=at(FRI, "06:00").isoformat())
        return mid

    def test_evening_juma_not_taken(self):
        self.add("🕌 ЖУМА МУБОРАК Масжидда жамланган мўминлар қалби ҳузур топади.")
        placed = smart.fill_from_stock(self.db, self.cfg, "xojaobod", at(FRI, "19:15"))
        for mid in placed:
            m = store.get(self.db, mid)
            t = dt.datetime.fromisoformat(m["scheduled_at"])
            self.assertTrue(smart.greet_ok(m["text"], t), f"#{mid} поставлен на {t:%H:%M}")

    def test_plain_maanaviyat_still_goes(self):
        self.add("🕌 ЖУМА МУБОРАК вечером нельзя")
        ok = self.add("🤲 ҲАЁТИЙ ПАНД-НАСИҲАТЛАР Муҳим ҳаётий масалалар.")
        placed = smart.fill_from_stock(self.db, self.cfg, "xojaobod", at(FRI, "19:15"))
        self.assertNotIn(1, placed)
        if placed:
            self.assertIn(ok, placed)


if __name__ == "__main__":
    unittest.main()
