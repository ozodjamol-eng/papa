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

    def test_report_goes_to_pult(self):
        """20.10 владелец: отчёт — прямо в бот-пульт; канал отчётов — только запасной путь."""
        import papa_audit as A
        send, calls = self._send()
        A.envf = lambda *p: {"PAPA_TEST_BOT_TOKEN": "t", "PAPA_REPORTS_CHANNEL_ID": "-100900"}
        self.assertEqual(A.deliver({"OWNER_IDS": "42", "GENPLAN_BOT_TOKEN": "g"}, "x", urgent=False, send=send), ["pult"])
        self.assertEqual(calls, ["42"])

    def test_pult_failed_fallback_to_channel(self):
        import papa_audit as A
        calls = []

        def send(tok, method, **p):
            calls.append(p["chat_id"])
            return {"ok": p["chat_id"] == "-100900"}
        A.envf = lambda *p: {"PAPA_TEST_BOT_TOKEN": "t", "PAPA_REPORTS_CHANNEL_ID": "-100900"}
        self.assertEqual(A.deliver({"OWNER_IDS": "42", "GENPLAN_BOT_TOKEN": "g"}, "x", urgent=True, send=send), ["reports"])

class TestGuard(unittest.TestCase):
    """🛡 Страж: права, ИИ, реклама — сразу тревога, без повторов-спама, починка ставится в очередь."""
    def setUp(self):
        d = Path(tempfile.mkdtemp())
        self.p = d / "g.db"
        db = store.connect(str(self.p))
        self.now = dt.datetime(2026, 10, 20, 18, 45, tzinfo=pa.TZ)
        mid = store.add_material(db, 1, 1, "Реклама: ўтин", True)
        store.update(db, mid, channel="davra", rubric="Реклама", status="queued",
                     scheduled_at=(self.now - dt.timedelta(minutes=15)).isoformat())
        db.commit()
        db.close()
        self.queued = []
        pa.tg = lambda tok, method, **p: {"ok": True, "result": {"id": 1, "username": "bot"}} if method == "getMe" else \
            {"ok": True, "result": {"status": "administrator", "can_post_messages": True}}

    def run_guard(self, state, rights=None, ai=None):
        return pa.guard(CFG, {}, self.now, state, db_path=self.p,
                        rights=rights or (lambda: {"session": True, "member": True, "admin": True}),
                        ai_check=ai or (lambda e: None),
                        queue=lambda task, reason, key: self.queued.append(task) or True)

    def test_stuck_ad_alerts_once(self):
        st = {}
        a = self.run_guard(st)
        self.assertTrue(any("🚨 РЕКЛАМА" in x for x in a), a)
        self.assertFalse(any("РЕКЛАМА" in x for x in self.run_guard(st)))   # второй раз — без спама

    def test_post_moved_again_and_again_alerts(self):
        """30.10 сверка №14: пост переносят +10 снова и снова — Страж видит по исходному времени (planned_at)."""
        db = store.connect(str(self.p))
        db.execute("DELETE FROM materials")
        mid = store.add_material(db, 1, 2, "Пост", True)
        store.update(db, mid, channel="davra", rubric="Видео", status="queued",
                     scheduled_at=(self.now - dt.timedelta(minutes=90)).isoformat())
        store.update(db, mid, scheduled_at=(self.now + dt.timedelta(minutes=5)).isoformat())   # авто-перенос
        db.commit()
        db.close()
        self.assertTrue(any("не вышла вовремя" in x for x in self.run_guard({})))

    def test_short_move_after_ad_is_quiet(self):
        db = store.connect(str(self.p))
        db.execute("DELETE FROM materials")
        mid = store.add_material(db, 1, 3, "Пост", True)
        store.update(db, mid, channel="davra", rubric="Видео", status="queued",
                     scheduled_at=(self.now - dt.timedelta(minutes=8)).isoformat())
        store.update(db, mid, scheduled_at=(self.now + dt.timedelta(minutes=2)).isoformat())   # +10 после рекламы
        db.commit()
        db.close()
        self.assertFalse(any("не вышла вовремя" in x for x in self.run_guard({})))

    def test_lost_admin_alerts_and_heals(self):
        st = {}
        a = self.run_guard(st, rights=lambda: {"session": True, "member": True, "admin": False})
        self.assertTrue(any("Хўжаобод" in x and "НЕ МОЖЕТ" in x for x in a), a)
        self.assertEqual(self.queued, ["xojaobod-admin"])
        b = self.run_guard(st)
        self.assertTrue(any("снова в порядке" in x for x in b), b)

    def test_ai_disabled_alerts(self):
        a = self.run_guard({}, ai=lambda e: "ключ не принят (истёк или удалён)")
        self.assertTrue(any("Gemini" in x for x in a), a)

    def test_voronka_stale_alerts_once_and_recovers(self):
        st, old = {}, self.now - dt.timedelta(hours=55)
        on = lambda n: True
        a = pa.voronka_guard(self.now, st, dbs={"X": None}, last=lambda p: old, enabled=on)
        self.assertTrue(any("Воронка X СТОИТ" in x for x in a), a)
        self.assertEqual(pa.voronka_guard(self.now, st, dbs={"X": None}, last=lambda p: old, enabled=on), [])
        b = pa.voronka_guard(self.now, st, dbs={"X": None}, last=lambda p: self.now - dt.timedelta(minutes=2), enabled=on)
        self.assertTrue(any("снова работает" in x for x in b), b)

    def test_voronka_disabled_is_silent(self):
        old = self.now - dt.timedelta(hours=5)
        self.assertEqual(pa.voronka_guard(self.now, {}, dbs={"X": None}, last=lambda p: old, enabled=lambda n: False), [])

    def test_unit_restart_twice_then_alert(self):
        st, done = {}, []
        down = lambda u: (True, False)
        a = pa.unit_guard(self.now, st, units=["papa-x"], st=down, restart=done.append)
        b = pa.unit_guard(self.now, st, units=["papa-x"], st=down, restart=done.append)
        c = pa.unit_guard(self.now, st, units=["papa-x"], st=down, restart=done.append)
        self.assertEqual(done, ["papa-x", "papa-x"])
        self.assertTrue(any("перезапустил" in x for x in a + b), a + b)
        self.assertTrue(any("не поднимается" in x for x in c), c)
        self.assertEqual(pa.unit_guard(self.now, st, units=["papa-x"], st=down, restart=done.append), [])  # без спама
        ok = pa.unit_guard(self.now, st, units=["papa-x"], st=lambda u: (True, True), restart=done.append)
        self.assertTrue(any("снова работает" in x for x in ok), ok)

    def test_unit_disabled_untouched(self):
        done = []
        self.assertEqual(pa.unit_guard(self.now, {}, units=["papa-x"], st=lambda u: (False, False), restart=done.append), [])
        self.assertEqual(done, [])

    def test_voronka_dead_token_paused_once(self):
        st, old = {}, self.now - dt.timedelta(hours=1)
        orig = pa.token_dead, pa.stop
        stopped = []
        pa.token_dead, pa.stop = (lambda u: True), stopped.append
        try:
            a = pa.voronka_guard(self.now, st, dbs={"Shodiyona": None}, last=lambda p: old, enabled=lambda n: True)
            self.assertTrue(any("паузу" in x and "shodiyona-voronka-token" in x for x in a), a)
            self.assertEqual(stopped, ["papa-voronka-shodiyona"])
            self.assertEqual(pa.voronka_guard(self.now, st, dbs={"Shodiyona": None}, last=lambda p: old, enabled=lambda n: True), [])
            r = pa.voronka_guard(self.now, st, dbs={"Shodiyona": None}, last=lambda p: self.now, enabled=lambda n: True)
            self.assertTrue(any("снова работает" in x for x in r), r)
            self.assertNotIn("Shodiyona", st["guard_paused"])
        finally:
            pa.token_dead, pa.stop = orig

    def test_gemini_saver_flag(self):
        import tempfile
        from pathlib import Path
        d = Path(tempfile.mkdtemp())
        f, sh = d / "saver", d / "shared-saver"
        a = pa.saver_guard(self.now, {}, hit=lambda: True, flag=f, shared=sh)
        self.assertTrue(a and "лимит" in a[0], a)
        self.assertEqual(f.read_text(), self.now.date().isoformat())
        self.assertEqual(sh.read_text(), self.now.date().isoformat())     # 30.10: флаг видит и Разведка
        self.assertEqual(pa.saver_guard(self.now, {}, hit=lambda: True, flag=f, shared=sh), [])   # один раз в день
        self.assertEqual(pa.saver_guard(self.now, {}, hit=lambda: False, flag=Path(str(f) + "2"), shared=None), [])

    def test_ai_alive_parsing(self):
        self.assertIsNone(pa.ai_alive({"GEMINI_API_KEY": "k"}, get=lambda: (200, "")))
        self.assertIn("не принят", pa.ai_alive({"GEMINI_API_KEY": "k"}, get=lambda: (400, '{"reason":"API_KEY_INVALID"}')))
        self.assertIsNone(pa.ai_alive({"ANTHROPIC_API_KEY": "k"}, get=lambda: (400, "organization_on_hold")))
        self.assertIsNone(pa.ai_alive({}, get=lambda: (401, "")))


if __name__ == "__main__":
    unittest.main()
