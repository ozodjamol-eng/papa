"""21.10: Anthropic отключил организацию (organization_on_hold) — ИИ сразу идёт на Gemini, Claude не дёргаем 6 часов."""
import io, os, sys, tempfile, unittest, urllib.error
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from genplan import ai, store  # noqa: E402


class T(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(str(Path(tempfile.mkdtemp()) / "g.db"))
        ai._DOWN.clear()
        self.env = dict(os.environ)
        os.environ.update({"AI_PRIMARY": "claude", "ANTHROPIC_API_KEY": "k", "GEMINI_API_KEY": "g"})
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.env), ai._DOWN.clear()))
        self.calls = []
        self.orig = (ai._claude, ai._gemini)
        self.addCleanup(lambda: (setattr(ai, "_claude", self.orig[0]), setattr(ai, "_gemini", self.orig[1])))

        def claude(s, u, http=None):
            self.calls.append("claude")
            raise urllib.error.HTTPError("u", 400, "bad", {}, io.BytesIO(b'{"error":{"type":"organization_on_hold"}}'))

        def gemini(s, u, http=None):
            self.calls.append("gemini"); return "хук"
        ai._claude, ai._gemini = claude, gemini

    def test_on_hold_then_gemini_first(self):
        self.assertEqual(ai.generate(self.db, "s", "u"), "хук")
        self.assertEqual(self.calls, ["claude", "gemini"])
        self.calls.clear()
        self.assertEqual(ai.generate(self.db, "s", "u"), "хук")
        self.assertEqual(self.calls, ["gemini"])          # отключённый Claude больше не пробуем
