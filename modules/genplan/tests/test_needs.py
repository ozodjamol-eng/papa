"""30.10: заказ штаба — пустые часы с рубриками, кодами источников и складами."""
import datetime as dt
import json
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import needs, plan, store  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
MON = dt.date(2026, 10, 19)


class T(unittest.TestCase):
    def test_needs(self):
        db = store.connect(":memory:")
        cfg = {**CFG, "channels": {k: dict(v) for k, v in CFG["channels"].items()}}
        mid = store.add_material(db, -100777, 1, "кулги", False)
        store.update(db, mid, channel="xojaobod", rubric="Ҳажвия", status="draft", stock=1)
        now = plan.slot_time(MON, "12:20")
        d = needs.build(db, cfg, now)
        x = d["channels"]["xojaobod"]
        hours = [e["h"] for e in x["empty"]]
        self.assertNotIn("21", hours)                  # кулги в запасе закрывает 21:00
        e17 = next(e for e in x["empty"] if e["h"] == "17")
        self.assertEqual(e17["want"][0], "Огоҳлантириш")
        self.assertIn("warn", e17["codes"])
        e20 = next(e for e in x["empty"] if e["h"] == "20")
        self.assertIn("МАЪНАВИЯТ", e20["stash"])
        self.assertNotIn("paparazzi", d["channels"])   # без карты часов — заказа нет
        p = Path(tempfile.mkdtemp()) / "needs.json"
        self.assertTrue(needs.write(db, cfg, now, p, force=True))
        self.assertIn("xojaobod", json.loads(p.read_text())["channels"])


class Evening(unittest.TestCase):
    def test_evening_report(self):
        from genplan import service
        db = store.connect(":memory:")
        mid = store.add_material(db, -100777, 1, "пост", False)
        store.update(db, mid, channel="davra", rubric="Ҳажвия", status="published")
        day = MON
        store.record(db, "davra", day.isoformat(), "10:00", mid, "done", 5)
        db.execute("UPDATE publications SET at=? WHERE material_id=?", (plan.slot_time(day, "10:00").isoformat(), mid))
        self.assertIsNone(service.evening_report(db, CFG, plan.slot_time(day, "20:00")))
        t = service.evening_report(db, CFG, plan.slot_time(day, "21:50"))
        self.assertIn("ШТАБ", t)
        self.assertIn("КАТТА ДАВРА: вышло 1 · часы 1/16", t)
        self.assertIsNone(service.evening_report(db, CFG, plan.slot_time(day, "22:00")))   # раз в день
