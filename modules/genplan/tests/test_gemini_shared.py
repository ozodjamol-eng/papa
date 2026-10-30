"""30.10 полный аудит: GENPLAN пишет общий счётчик Gemini, читает общий флаг экономии, кадры — на flash-lite."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import ai, store  # noqa: E402

TODAY = dt.datetime.now(dt.timezone(dt.timedelta(hours=5))).date().isoformat()


class T(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        os.environ["PAPA_GEMINI_DIR"] = self.d.name
        os.environ["GEMINI_API_KEY"] = "g-test"
        self.saver = ai.SAVER
        ai.SAVER = os.path.join(self.d.name, "nope")

    def tearDown(self):
        ai.SAVER = self.saver
        os.environ.pop("PAPA_GEMINI_DIR", None)
        os.environ.pop("GEMINI_API_KEY", None)
        self.d.cleanup()

    def count(self):
        return (Path(self.d.name) / "gemini-count").read_text().split()

    def test_spend_counts_per_day(self):
        ai.shared_spend()
        ai.shared_spend(2)
        self.assertEqual(self.count(), [TODAY, "3"])

    def test_shared_saver_flag(self):
        self.assertFalse(ai.saver_on())
        (Path(self.d.name) / "gemini-saver").write_text(TODAY)
        self.assertTrue(ai.saver_on())

    def test_vision_uses_lite_and_counts(self):
        seen = []

        def http(req):
            seen.append(req.full_url)
            return {"candidates": [{"content": {"parts": [{"text": json.dumps({"ok": True})}]}}]}
        db = store.connect(":memory:")
        out = ai.vision(db, "смотри", [b"\xff\xd8x"], http=http)
        self.assertEqual(out, {"ok": True})
        self.assertIn("gemini-flash-lite-latest", seen[0])
        self.assertEqual(self.count(), [TODAY, "1"])


if __name__ == "__main__":
    unittest.main()
