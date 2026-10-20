"""20.10: русский текст ИИ переводит сам; без перевода пост в канал не выходит."""
import asyncio
import datetime as dt
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_hub_service import CFG, ENV, FakeBot, post  # noqa: E402
from genplan import ai, hub, service, store, translit  # noqa: E402

RU = "Холодные руки и ноги? Простое решение согреет вас! Если мерзнут конечности, не стоит терпеть дискомфорт. Освойте простую технику."


class RuTranslate(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")

    def test_detects_russian(self):
        self.assertTrue(translit.language_note(RU))
        self.assertFalse(translit.language_note("Ассалому алайкум, қадрли дўстлар! Бугун ҳаво илиқ."))

    def test_intake_queues_ai_job(self):
        os.environ["ANTHROPIC_API_KEY"] = "x"
        try:
            hub.intake(FakeBot(), self.db, CFG, {42}, -100777, [5], [post(5, RU)["channel_post"]])
            j = store.job_take(self.db)
            self.assertIsNotNone(j)
            self.assertEqual(j["kind"], "ai")
        finally:
            del os.environ["ANTHROPIC_API_KEY"]

    def test_publish_blocked_without_translation(self):
        hub.intake(FakeBot(), self.db, CFG, {42}, -100777, [6], [post(6, RU)["channel_post"]])
        m = store.get(self.db, 1)
        service.ERRORS.clear()
        ok = asyncio.run(service.publish_one(self.db, CFG, ENV, None, m["channel"], m, None, "2026-10-20",
                                             log=lambda *_: None, now=dt.datetime(2026, 10, 20, 18)))
        self.assertFalse(ok)
        self.assertTrue(any("на русском" in e for e in service.ERRORS))


if __name__ == "__main__":
    unittest.main()
