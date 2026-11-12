"""📌 09.11 владелец: твёрдые слоты протокола — 06:30 зарядка, 06:45 здоровье, 07:15 завтрак, новости 07:40/13:00/19:00
(только из «СРОЧНО НОВОСТИ»). Вне сетки, не съедаются сеткой, нет материала — пропуск."""
import datetime as dt
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import plan, smart, store  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
MON = dt.date(2026, 11, 9)


def at(hhmm, day=MON):
    return plan.slot_time(day, hhmm)


class T(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")
        self.n = 0
        self.cfg = {**CFG, "channels": {k: dict(v) for k, v in CFG["channels"].items()}}

    def stock(self, source, rubric, ch="davra", created=None):
        self.n += 1
        mid = store.add_material(self.db, -100777, self.n, f"Машқ ва соғлом турмуш ҳақида пост {self.n}", True)
        store.update(self.db, mid, channel=ch, rubric=rubric, status="draft", stock=1, source=source, auto=1,
                     scheduled_at=None)
        if created:
            self.db.execute("UPDATE materials SET created_at=? WHERE id=?", (created.isoformat(), mid))
            self.db.commit()
        return mid

    def when(self, mid):
        m = store.get(self.db, mid)
        return dt.datetime.fromisoformat(m["scheduled_at"]).strftime("%H:%M") if m["scheduled_at"] else None

    def test_morning_slots(self):
        for ch in ("davra", "xojaobod"):
            ts = [f"{t:%H:%M}" for t, _ in smart.fixed_slots(CFG["channels"][ch], MON)]
            self.assertEqual(ts, ["06:30", "06:45", "07:15", "07:40", "13:00", "19:00"] + (["21:30"] if ch == "davra" else []))
        # 12.11: вечерние программы по дням недели — Пт жонли ижро, Сб жаҳон ретро, Вс ўзбек ретро (19:30)
        ev = {d: [s["rubric"] for t, s in smart.fixed_slots(CFG["channels"]["davra"], MON + dt.timedelta(days=d)) if f"{t:%H:%M}" == "19:30"]
              for d in range(7)}
        self.assertEqual(ev, {0: [], 1: [], 2: [], 3: [], 4: ["Жонли ижро"], 5: ["Жаҳон ретро"], 6: ["Ўзбек ретро"]})
        self.assertEqual(CFG["channels"]["davra"]["morning"]["day_post"], "06:20")

    def test_fills_zaryadka_and_health(self):
        z = self.stock("БАНК · БАДАНТАРБИЯ", "Бадантарбия", created=at("05:00") - dt.timedelta(days=1))
        h = self.stock("БАНК · САЛОМАТЛИК", "Саломатлик", created=at("05:00") - dt.timedelta(days=1))
        smart.fill_from_stock(self.db, self.cfg, "davra", at("05:30"))
        self.assertEqual((self.when(z), self.when(h)), ("06:30", "06:45"))
        m = store.get(self.db, z)
        self.assertEqual((m["fixed"], m["rubric"], m["status"]), (1, "Бадантарбия", "queued"))
        self.assertFalse(smart.is_grid_post(m))

    def test_breakfast_from_ovqat(self):
        b = self.stock("БАНК · ОВҚАТ", "Фойдали видео", created=at("05:00") - dt.timedelta(days=1))
        smart.fill_from_stock(self.db, self.cfg, "davra", at("06:00"))
        self.assertEqual(self.when(b), "07:15")
        self.assertEqual(store.get(self.db, b)["rubric"], "Нонушта")

    def test_news_only_fresh_newest(self):
        old = self.stock("СРОЧНО НОВОСТИ", "Янгиликлар", created=at("12:00") - dt.timedelta(hours=20))
        a = self.stock("СРОЧНО НОВОСТИ", "Янгиликлар", created=at("10:00"))
        b = self.stock("СРОЧНО НОВОСТИ", "Янгиликлар", created=at("11:30"))
        smart.fill_from_stock(self.db, self.cfg, "davra", at("12:00"))
        self.assertEqual(self.when(b), "13:00")          # самая свежая
        self.assertIsNone(self.when(a))                  # грид её в ближайший час не ставит
        self.assertIsNone(self.when(old))

    def test_no_material_no_post_and_no_double(self):
        smart.fill_from_stock(self.db, self.cfg, "davra", at("05:30"))
        z = self.stock("БАНК · БАДАНТАРБИЯ", "Бадантарбия", created=at("04:00"))
        z2 = self.stock("БАНК · БАДАНТАРБИЯ", "Бадантарбия", created=at("04:10"))
        smart.fill_from_stock(self.db, self.cfg, "davra", at("05:40"))
        smart.fill_from_stock(self.db, self.cfg, "davra", at("05:50"))
        self.assertEqual((self.when(z), self.when(z2)), ("06:30", None))   # один пост на слот

    def test_grid_does_not_eat_reserved_food(self):
        b = self.stock("БАНК · ОВҚАТ", "Фойдали видео", created=at("09:00") - dt.timedelta(days=2))
        smart.fill_from_stock(self.db, self.cfg, "davra", at("16:00"))   # 17:00 «Фойдали видео» — но ОВҚАТ под завтрак
        self.assertIsNone(self.when(b))


if __name__ == "__main__":
    unittest.main()
