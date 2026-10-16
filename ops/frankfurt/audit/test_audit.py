"""Тест аудита на временной базе GENPLAN (схема — из самого GENPLAN)."""
import datetime as dt
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "modules" / "genplan"))
import papa_audit as pa  # noqa: E402
from genplan import store  # noqa: E402

CFG = tomllib.loads((HERE.parents[2] / "modules/genplan/config.toml").read_text(encoding="utf-8"))


class TestAudit(unittest.TestCase):
    def setUp(self):
        self.p = Path(tempfile.mkdtemp()) / "g.db"
        db = store.connect(str(self.p))
        self.now = dt.datetime(2026, 10, 17, 2, 0, tzinfo=pa.TZ)
        mid = store.add_material(db, 1, 1, "Пост", True)
        store.update(db, mid, channel="davra", status="queued", scheduled_at=(self.now - dt.timedelta(hours=1)).isoformat())
        db.commit()
        db.close()
        pa.GP_DB = self.p

    def test_stuck_post_is_problem(self):
        a = pa.Audit()
        a.genplan(CFG, self.now, quick=False)
        self.assertTrue(any("застряли" in x for x in a.bad), a.bad)
        self.assertTrue(any("КАТТА ДАВРА: вышло" in x for x in a.info), a.info)
        self.assertIn("❌ Проблем: 1", a.text(False, self.now))

    def test_all_good_text(self):
        a = pa.Audit()
        a.info.append("диск 34%")
        self.assertIn("✅ Всё в порядке", a.text(False, self.now))


if __name__ == "__main__":
    unittest.main()
