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



class TestWatch(unittest.TestCase):
    def test_admin_changes(self):
        old = {"1": {"name": "@ozod", "status": "creator", "rights": []},
               "2": {"name": "@bot", "status": "administrator", "rights": ["can_post_messages"]}}
        new = {**old, "2": {"name": "@bot", "status": "administrator", "rights": ["can_post_messages", "can_promote_members"]},
               "3": {"name": "@chuzhoy", "status": "administrator", "rights": ["can_change_info"]}}
        msgs = pa.admin_changes(old, new)
        self.assertTrue(any("новый админ @chuzhoy" in m for m in msgs))
        self.assertTrue(any("@bot" in m and "can_promote_members" in m for m in msgs))
        self.assertEqual(pa.admin_changes(new, new), [])



class TestDeliver(unittest.TestCase):
    def setUp(self):
        import papa_audit as A
        orig = A.envf
        self.addCleanup(setattr, A, "envf", orig)

    def _send(self, ok_chan=True):
        calls = []

        def send(tok, method, **p):
            calls.append(p["chat_id"])
            return {"ok": ok_chan if p["chat_id"] == "-100900" else True}
        return send, calls

    def test_report_to_reports_channel_only(self):
        import papa_audit as A
        send, calls = self._send()
        A.envf = lambda *p: {"PAPA_TEST_BOT_TOKEN": "t", "PAPA_REPORTS_CHANNEL_ID": "-100900"}
        self.assertEqual(A.deliver({"OWNER_IDS": "42", "GENPLAN_BOT_TOKEN": "g"}, "x", urgent=False, send=send), ["reports"])
        self.assertEqual(calls, ["-100900"])

    def test_urgent_also_to_pult_and_fallback(self):
        import papa_audit as A
        send, calls = self._send()
        A.envf = lambda *p: {"PAPA_TEST_BOT_TOKEN": "t", "PAPA_REPORTS_CHANNEL_ID": "-100900"}
        self.assertEqual(A.deliver({"OWNER_IDS": "42", "GENPLAN_BOT_TOKEN": "g"}, "x", urgent=True, send=send), ["reports", "pult"])
        send, calls = self._send(ok_chan=False)          # канал не принял — в пульт
        self.assertEqual(A.deliver({"OWNER_IDS": "42", "GENPLAN_BOT_TOKEN": "g"}, "x", urgent=False, send=send), ["pult"])
        A.envf = lambda *p: {}                            # канал не настроен — в пульт
        send, calls = self._send()
        self.assertEqual(A.deliver({"OWNER_IDS": "42", "GENPLAN_BOT_TOKEN": "g"}, "x", urgent=False, send=send), ["pult"])

if __name__ == "__main__":
    unittest.main()
