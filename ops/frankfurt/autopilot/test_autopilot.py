"""Тесты исполнителя автопилота: политика, маскировка секретов, путь задачи через базу шлюза и кнопку владельца."""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "modules" / "pult" / "gateway"))
import papa_autopilot as ap  # noqa: E402
from nexus_control.core import Store  # noqa: E402


class TestPolicy(unittest.TestCase):
    def test_lists(self):
        self.assertEqual(ap.policy("genplan-restart"), "auto")
        self.assertEqual(ap.policy("morning-pool-clear"), "approve")
        self.assertEqual(ap.policy("something-new"), "approve")          # незнакомое — только с кнопкой
        for t in ("genplan-bot-token", "genplan-gemini-key", "razvedka-login", "tg-account-qr", "autopilot-install", "../x", "a;b"):
            self.assertEqual(ap.policy(t), "deny", t)

    def test_every_listed_task_exists(self):
        allow = json.loads(ap.ALLOW.read_text(encoding="utf-8"))
        tasks = HERE.parent / "tasks"
        for t in allow["auto"] + allow["approve"]:
            self.assertTrue((tasks / f"{t}.sh").exists(), t)

    def test_mask(self):
        out = ap.mask("bot 1234567890:AAH" + "x" * 33 + " key=AIza" + "y" * 35 + " GEMINI_API_KEY=abcdefghijklmnop ok")
        self.assertNotIn("x" * 20, out)
        self.assertNotIn("y" * 20, out)
        self.assertNotIn("abcdefghijklmnop", out)
        self.assertIn("ok", out)


class TestFlow(unittest.TestCase):
    def setUp(self):
        d = Path(tempfile.mkdtemp())
        self.gw = d / "gw.db"
        self.store = Store(self.gw, d / "state")
        self.gp = d / "gp.db"
        c = sqlite3.connect(self.gp)
        c.execute("CREATE TABLE kv(k TEXT PRIMARY KEY, v TEXT)")
        c.commit()
        c.close()
        self.sent = []
        ap.in_window = lambda now: ""          # тесты не зависят от времени запуска
        ap.notify = lambda text, markup=None: self.sent.append((text, markup)) or [(1, 1)]

    def new(self, task):
        return self.store.create("ai", "papa_task", {"task": task, "reason": "тест"}, "frankfurt")["id"]

    def test_auto_runs_and_stores_output(self):
        tid = self.new("genplan-restart")
        t = ap.claim(self.gw)
        self.assertEqual(t["task"], "genplan-restart")
        r = ap.handle(t, self.gw, self.gp, runner=lambda task: (0, "OK\n== GENPLAN_RESTART_DONE"), sleep=lambda s: None)
        self.assertEqual(r, "ok")
        row = self.store.get(tid)
        self.assertEqual(row["status"], "succeeded")
        self.assertIn("GENPLAN_RESTART_DONE", json.loads(row["result"])["output"])
        self.assertIsNone(ap.claim(self.gw))

    def test_deny_never_runs(self):
        tid = self.new("genplan-bot-token")
        ran = []
        ap.handle(ap.claim(self.gw), self.gw, self.gp, runner=lambda task: ran.append(task) or (0, ""), sleep=lambda s: None)
        self.assertEqual(ran, [])
        self.assertEqual(self.store.get(tid)["status"], "failed")

    def test_approve_waits_for_owner_button(self):
        tid = self.new("morning-pool-clear")
        ran = []
        ticks = []

        def sleep(_):
            ticks.append(1)
            if len(ticks) == 2:                       # владелец нажал «✅ Разрешить»
                c = sqlite3.connect(self.gp)
                c.execute("INSERT INTO kv VALUES (?, 'yes')", (f"autopilot_{tid}",))
                c.commit()
                c.close()
        r = ap.handle(ap.claim(self.gw), self.gw, self.gp, runner=lambda task: ran.append(task) or (0, "done"), sleep=sleep)
        self.assertEqual((r, ran), ("ok", ["morning-pool-clear"]))
        self.assertIn("ap:" + tid + ":y", json.dumps(self.sent[0][1]))

    def test_owner_says_no(self):
        tid = self.new("morning-pool-clear")
        c = sqlite3.connect(self.gp)
        c.execute("INSERT INTO kv VALUES (?, 'no')", (f"autopilot_{tid}",))
        c.commit()
        c.close()
        ran = []
        self.assertEqual(ap.handle(ap.claim(self.gw), self.gw, self.gp, runner=lambda t: ran.append(t) or (0, ""),
                                   sleep=lambda s: None), "rejected")
        self.assertEqual(ran, [])

    def test_recover_marks_stuck(self):
        tid = self.new("status")
        ap.claim(self.gw)
        ap.recover(self.gw)
        self.assertEqual(self.store.get(tid)["status"], "failed")



def NORUN(task):
    raise AssertionError("задачу Лондона Франкфурт сам не выполняет")


class TestLondon(unittest.TestCase):
    def setUp(self):
        d = Path(tempfile.mkdtemp())
        self.gw = d / "gw.db"
        self.store = Store(self.gw, d / "state")
        self.gp = d / "gp.db"
        c = sqlite3.connect(self.gp)
        c.execute("CREATE TABLE kv(k TEXT PRIMARY KEY, v TEXT)")
        c.commit()
        c.close()
        self.sent = []
        ap.in_window = lambda now: ""
        ap.notify = lambda text, markup=None: self.sent.append((text, markup)) or [(1, 1)]

    def new(self, task):
        return self.store.create("ai", "papa_task", {"task": task, "reason": "тест"}, "london")["id"]

    def runner_side(self, tid, ok=True):
        """То, что делает papa-runner на Лондоне, когда задача стала 'ready'."""
        def sleep(_):
            t = self.store.next_runner("london-runner")
            if t:
                self.assertEqual(t["id"], tid)
                self.store.runner_finish("london-runner", tid, ok, {"rc": 0 if ok else 1, "output": "x\n== LONDON_DIAGNOSE_DONE"})
        return sleep

    def test_london_policy_and_lists_exist(self):
        allow = json.loads(ap.ALLOW_LONDON.read_text(encoding="utf-8"))
        for t in allow["auto"] + allow["approve"]:
            self.assertTrue((HERE.parents[1] / "london" / "tasks" / f"{t}.sh").exists(), t)
        self.assertEqual(ap.policy("london-diagnose", server="london"), "auto")
        self.assertEqual(ap.policy("genplan5-overdue-skip", server="london"), "approve")
        for t in ("runner-install", "purge", "archive", "x-token", "core-install"):
            self.assertEqual(ap.policy(t, server="london"), "deny", t)
        self.assertEqual(ap.policy("london-diagnose"), "approve")      # на Франкфурте такой задачи нет в списке

    def test_auto_goes_to_runner_not_run_here(self):
        tid = self.new("london-diagnose")
        t = ap.claim(self.gw)
        self.assertEqual((t["server"], self.store.get(tid)["status"]), ("london", "deciding"))
        self.assertIsNone(self.store.next_runner("london-runner"))     # пока Франкфурт не решил — Лондон не видит
        ran = []
        r = ap.handle(t, self.gw, self.gp, runner=lambda task: ran.append(task) or (0, ""), sleep=self.runner_side(tid))
        self.assertEqual((r, ran), ("ok", []))
        self.assertEqual(self.store.get(tid)["status"], "succeeded")
        self.assertIn("Лондон", self.sent[-1][0])

    def test_approve_needs_button_before_runner_sees_it(self):
        tid = self.new("genplan5-overdue-skip")
        t = ap.claim(self.gw)
        seen_before = []
        ticks = []

        def sleep(_):
            ticks.append(1)
            st = self.store.get(tid)["status"]
            if st == "awaiting_owner":
                seen_before.append(self.store.next_runner("london-runner"))
                if len(ticks) == 2:
                    c = sqlite3.connect(self.gp)
                    c.execute("INSERT INTO kv VALUES (?, 'yes')", (f"autopilot_{tid}",))
                    c.commit()
                    c.close()
            else:
                self.runner_side(tid)(None)
        self.assertEqual(ap.handle(t, self.gw, self.gp, runner=NORUN, sleep=sleep), "ok")
        self.assertTrue(seen_before and all(x is None for x in seen_before))
        self.assertIn("ap:" + tid + ":y", json.dumps(self.sent[0][1]))

    def test_deny_never_reaches_runner(self):
        tid = self.new("purge")
        ap.handle(ap.claim(self.gw), self.gw, self.gp, runner=NORUN, sleep=lambda s: None)
        self.assertEqual(self.store.get(tid)["status"], "failed")
        self.assertIsNone(self.store.next_runner("london-runner"))

    def test_window_makes_changes_need_button(self):
        ap.in_window = lambda now: "19:00–22:00"
        tid = self.new("genplan5-prayer-find")          # auto, но не из «только чтение» — в главные часы с кнопкой
        c = sqlite3.connect(self.gp)
        c.execute("INSERT INTO kv VALUES (?, 'no')", (f"autopilot_{tid}",))
        c.commit()
        c.close()
        self.assertEqual(ap.handle(ap.claim(self.gw), self.gw, self.gp, runner=NORUN, sleep=lambda s: None), "rejected")

    def test_runner_offline_task_withdrawn(self):
        tid = self.new("london-diagnose")
        old = ap.LONDON_WAIT
        ap.LONDON_WAIT = 0
        try:
            self.assertEqual(ap.handle(ap.claim(self.gw), self.gw, self.gp, runner=NORUN, sleep=lambda s: None), "failed")
        finally:
            ap.LONDON_WAIT = old
        self.assertEqual(self.store.get(tid)["status"], "failed")
        self.assertIsNone(self.store.next_runner("london-runner"))   # снята — позже внезапно не выполнится

    def test_recover_keeps_london_running(self):
        tid = self.new("london-diagnose")
        ap.claim(self.gw)
        with sqlite3.connect(self.gw) as c:
            c.execute("UPDATE tasks SET status='running' WHERE id=?", (tid,))
        ap.recover(self.gw)
        self.assertEqual(self.store.get(tid)["status"], "running")     # её выполняет Лондон — не наше


class TestWindow(unittest.TestCase):
    def test_window(self):
        import importlib
        importlib.reload(ap)
        from datetime import datetime, timezone
        self.assertEqual(ap.in_window(datetime(2026, 10, 16, 1, 0, tzinfo=timezone.utc)), "04:30–07:30")   # 06:00 Ташкент
        self.assertEqual(ap.in_window(datetime(2026, 10, 16, 15, 0, tzinfo=timezone.utc)), "19:00–22:00")  # 20:00
        self.assertEqual(ap.in_window(datetime(2026, 10, 16, 8, 0, tzinfo=timezone.utc)), "")              # 13:00


if __name__ == "__main__":
    unittest.main()
