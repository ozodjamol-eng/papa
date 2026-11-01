import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from genplan import caption  # noqa: E402


def row(**kw):
    d = {"id": 1, "has_media": 1, "rubric": "Ҳажвия", "text": "", "media": "[]"}
    d.update(kw)

    class R(dict):
        def keys(self):
            return super().keys()
    return R(d)


class CaptionRule(unittest.TestCase):
    def test_needs(self):
        self.assertTrue(caption.needs_caption(row(text="")))
        self.assertTrue(caption.needs_caption(row(text="👉 @kattadavrauz")))
        self.assertFalse(caption.needs_caption(row(text="😂 КУЛГИЛИ ҲОЛАТ\nДўстларга юборинг.")))
        self.assertFalse(caption.needs_caption(row(rubric="Реклама", text="")))
        self.assertFalse(caption.needs_caption(row(has_media=0, text="")))

    def test_ours(self):
        self.assertFalse(caption.is_ours("Reklam değil yazılı tekte"))
        self.assertTrue(caption.is_ours("😂 КУЛГИЛИ ҲОЛАТ Дўстларга юборинг"))

    def test_no_media_waits(self):
        self.assertFalse(caption.ensure(None, None, "КАТТА ДАВРА", row(text=""), log=lambda s: None))


if __name__ == "__main__":
    unittest.main()
