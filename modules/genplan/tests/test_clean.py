"""🧼 13.11: пошлое в каналы не выходит (случай: твит «мужчины дрочат перед свиданиями» под #ҲАЖВИЯ)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from genplan import clean  # noqa: E402


class R(dict):
    pass


def row(**kw):
    d = {"id": 1, "has_media": 1, "rubric": "Ҳажвия", "text": "😂 КУЛГИЛИ МАЗМУН", "media": "[]", "urgent": 0,
         "auto": 1, "source": "РАЗВЛЕКАТЕЛЬНО"}
    d.update(kw)
    return R(d)


class Words(unittest.TestCase):
    def test_bad(self):
        for t in ("Мужчины дрочат перед свиданиями", "секс ҳақида", "Shahvoniy video", "18+ ҳазил", "ах ты сука"):
            self.assertTrue(clean.bad_words(t), t)

    def test_clean(self):
        for t in ("😂 КУЛГИЛИ МАЗМУН\nКайфиятингизни кўтарадиган қизиқарли лаҳзалар", "Спорт секцияси очилди",
                  "Хўжаобод янгиликлари", "Намоз вақтлари", "Интернет тезлиги ошди", "Амир Темур хиёбони",
                  "Сиз кулдингизми?", "Бугун ҳаво +18 даража"):
            self.assertFalse(clean.bad_words(t), t)


class Gate(unittest.TestCase):
    def test_applies(self):
        self.assertTrue(clean.applies({}, row()))
        self.assertFalse(clean.applies({}, row(rubric="Реклама")))
        self.assertFalse(clean.applies({}, row(urgent=1)))
        self.assertFalse(clean.applies({"clean": False}, row()))

    def test_strict(self):
        self.assertTrue(clean.strict(row()))
        self.assertFalse(clean.strict(row(auto=0, source=None)))          # бросил владелец
        self.assertFalse(clean.strict(row(rubric="Янгиликлар")))

    def test_video_only(self):
        ph = '[{"type": "photo", "file_id": "a"}]'
        vd = '[{"type": "video", "file_id": "a"}]'
        self.assertEqual(clean.check(None, None, row(media=ph))[0], "bad")
        self.assertFalse(clean.photo_only(row(media=vd)))
        self.assertFalse(clean.photo_only(row(media=ph, auto=0, source=None)))                       # бросил владелец
        self.assertTrue(clean.photo_only(row(media=ph, rubric="Фойдали видео", source="БАНК · ФОЙДАЛИ")))
        self.assertTrue(clean.photo_only(row(media=ph, rubric="Маънавият", source="МАЪНАВИЯТ")))
        self.assertFalse(clean.photo_only(row(media=ph, rubric="Янгиликлар", source="СРОЧНО НОВОСТИ")))
        self.assertFalse(clean.photo_only(row(media=ph, rubric="Муфтий минбари", source="@shayx_nuriddinxoliqnazar")))
        self.assertTrue(clean.photo_only(row(media=ph, source="@AbduraxmonQiziq")))                  # юмор — любой источник

    def test_religion(self):
        vd = '[{"type": "video", "file_id": "a"}]'
        self.assertEqual(clean.check(None, None, row(media=vd, rubric="Маънавият", source="БАНК · МАЪНАВИЯТ"))[0], "bad")
        self.assertTrue(clean.religious_source(row(rubric="Маънавият", source="@someone")))
        self.assertFalse(clean.religious_source(row(rubric="Муфтий минбари", source="@shayx_nuriddinxoliqnazar")))
        self.assertFalse(clean.religious_source(row(rubric="Маънавият", auto=0, source=None)))       # бросил владелец
        seen = []
        orig = clean.images
        clean.images = lambda pub, m: [b"jpg"]
        try:
            clean.check(None, None, row(media=vd, rubric="Ибрат", source="БАНК · ИБРАТ"), look=lambda p, i: seen.append(p) or {"ok": True})
            clean.check(None, None, row(media=vd, rubric="Муфтий минбари", source="@shayx_nuriddinxoliqnazar"),
                        look=lambda p, i: seen.append(p) or {"ok": True})
        finally:
            clean.images = orig
        self.assertIn("диний материал", seen[0])
        self.assertNotIn("диний материал", seen[1])

    def test_text_bad_without_ai(self):
        self.assertEqual(clean.check(None, None, row(text="секс ҳазил"))[0], "bad")

    def test_no_file_unknown(self):
        self.assertEqual(clean.check(None, None, row())[0], "unknown")

    def test_vision(self):
        orig = clean.images
        clean.images = lambda pub, m: [b"jpg"]
        try:
            self.assertEqual(clean.check(None, None, row(), look=lambda p, i: {"ok": False, "why": "пошлая шутка"}),
                             ("bad", "пошлая шутка"))
            self.assertEqual(clean.check(None, None, row(), look=lambda p, i: {"ok": True})[0], "ok")
            self.assertEqual(clean.check(None, None, row(), look=lambda p, i: {})[0], "unknown")

            def boom(p, i):
                raise RuntimeError("лимит")
            self.assertEqual(clean.check(None, None, row(), look=boom)[0], "unknown")
        finally:
            clean.images = orig


if __name__ == "__main__":
    unittest.main()
