"""📅 Режим дня по галочкам (06.11 владелец, путь А): по умолчанию всё ✅; снятая галочка + «✅ Утверждаю» —
час сегодня пустой; протоколы 🔒 не выключаются; в 21:30 карточка на завтра."""
import datetime as dt
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import hub, menu, plan, rezhim, smart, store  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
DAY = dt.date(2026, 11, 9)


def at(hhmm, day=DAY):
    return plan.slot_time(day, hhmm)


class Bot:
    def __init__(self):
        self.calls = []

    def __call__(self, method, **kw):
        self.calls.append((method, kw))
        return {"message_id": 1}


def cq(data):
    return {"id": "q", "from": {"id": 1}, "data": data, "message": {"chat": {"id": 1}, "message_id": 5, "text": ""}}


class T(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")
        self.cfg = {**CFG, "channels": {k: dict(v) for k, v in CFG["channels"].items()}}
        self.n = 0

    def add(self, t, rubric="Ҳажвия", locked=0):
        self.n += 1
        mid = store.add_material(self.db, -100777, self.n, f"Пост {self.n}", False)
        store.update(self.db, mid, channel="davra", rubric=rubric, status="queued", locked=locked, scheduled_at=t.isoformat())
        return mid

    def press(self, data, now):
        b = Bot()
        hub.callback(b, self.db, self.cfg, {1}, cq(data), now)
        return b

    def test_davra_and_xojaobod(self):                   # 07.11 владелец: и в Хўжаобод; PaparazziUZ — без часовой сетки
        self.assertTrue(rezhim.enabled(self.cfg["channels"]["davra"]))
        self.assertTrue(rezhim.enabled(self.cfg["channels"]["xojaobod"]))
        self.assertFalse(rezhim.enabled(self.cfg["channels"]["paparazzi"]))

    def test_default_all_on(self):
        now = at("06:00")
        self.assertEqual(rezhim.off_hours(self.db, "davra", DAY), [])
        free = smart.free_hours(self.db, self.cfg["channels"]["davra"], "davra", None, now, DAY, minbar=True)
        self.assertIn("09:00", [f"{t:%H:%M}" for t in free])

    def test_toggle_needs_approve_then_hour_off(self):
        now = at("06:00")
        d = DAY.strftime("%Y%m%d")
        self.press(f"rz:open:davra:{d}", now)
        self.press(f"rz:t:davra:{d}:09", now)
        self.assertEqual(rezhim.off_hours(self.db, "davra", DAY), [])          # без «Утверждаю» — не действует
        b = self.press(f"rz:ok:davra:{d}", now)
        self.assertEqual(rezhim.off_hours(self.db, "davra", DAY), ["09"])
        text = [kw["text"] for m, kw in b.calls if m == "editMessageText"][0]
        self.assertIn("✅ Принято", text)
        self.assertIn("09:00", text)
        free = smart.free_hours(self.db, self.cfg["channels"]["davra"], "davra", None, now, DAY, minbar=True)
        self.assertNotIn("09:00", [f"{t:%H:%M}" for t in free])
        self.assertIn("10:00", [f"{t:%H:%M}" for t in free])
        self.assertIn("⏸ 09:00", smart.day_view(self.db, self.cfg, "davra", now))

    def test_queued_grid_post_back_to_stock_owner_choice(self):
        now = at("06:00")
        d = DAY.strftime("%Y%m%d")
        a = self.add(at("09:00"))
        b = self.add(at("11:00"), locked=1)
        self.press(f"rz:open:davra:{d}", now)
        self.press(f"rz:t:davra:{d}:09", now)
        self.press(f"rz:t:davra:{d}:11", now)            # 07.11 владелец: и час с его постом — галочка, сняли → в запас
        self.press(f"rz:ok:davra:{d}", now)
        self.assertEqual(store.get(self.db, a)["stock"], 1)
        self.assertIsNone(store.get(self.db, a)["scheduled_at"])
        self.assertEqual(store.get(self.db, b)["status"], "draft")
        self.assertEqual(rezhim.off_hours(self.db, "davra", DAY), ["09", "11"])

    def test_past_hours_stay_in_list(self):
        hs = [h for h, _, _ in rezhim.items(self.db, self.cfg, "davra", DAY, at("15:00"))]
        self.assertIn("09", hs)
        text, kb = rezhim.card(self.db, self.cfg, "davra", DAY, at("15:00"))
        self.assertTrue(any("▶" in b["text"] for r in kb["inline_keyboard"] for b in r))

    def test_minbar_locked(self):
        its = {h: ok for h, _, ok in rezhim.items(self.db, self.cfg, "davra", DAY, at("06:00"))}
        self.assertFalse(its["22"])
        self.assertTrue(its["09"])

    def test_all_on_resets(self):
        now = at("06:00")
        d = DAY.strftime("%Y%m%d")
        self.press(f"rz:t:davra:{d}:09", now)
        self.press(f"rz:ok:davra:{d}", now)
        self.press(f"rz:all:davra:{d}", now)
        self.press(f"rz:ok:davra:{d}", now)
        self.assertEqual(rezhim.off_hours(self.db, "davra", DAY), [])

    def test_evening_once(self):
        self.assertEqual(rezhim.evening_due(self.db, self.cfg, at("21:00")), [])
        self.assertEqual(rezhim.evening_due(self.db, self.cfg, at("21:31")), ["davra", "xojaobod"])
        self.assertEqual(rezhim.evening_due(self.db, self.cfg, at("21:40")), [])

    def test_today_button_under_segodnya(self):
        kb = menu.panel_markup(self.cfg, "davra", menu.P_TODAY, db=self.db, now=at("06:00"))
        self.assertEqual(kb["inline_keyboard"][0][0]["text"], "🗓 Режим дня")
        self.assertEqual(menu.panel_markup(self.cfg, "paparazzi", menu.P_TODAY, db=self.db), menu.PANEL)

    def test_flag_removed_hours_work_again(self):
        now = at("06:00")
        d = DAY.strftime("%Y%m%d")
        self.press(f"rz:t:davra:{d}:09", now)
        self.press(f"rz:ok:davra:{d}", now)
        self.cfg["channels"]["davra"].pop("rezhim")
        free = smart.free_hours(self.db, self.cfg["channels"]["davra"], "davra", None, now, DAY, minbar=True)
        self.assertIn("09:00", [f"{t:%H:%M}" for t in free])


if __name__ == "__main__":
    unittest.main()
