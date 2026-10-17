"""Схема хуков владельца 17.10: новости — без хука; музыка — наша реклама; полезное — ИИ; дуо — готовый хук."""
import tomllib
import unittest
from unittest import mock

from genplan import service, store


class Row(dict):
    def keys(self):
        return super().keys()


def mat(i, rubric, text):
    return Row(id=i, rubric=rubric, text=text, junk=None, hook_ai=None)


class Scheme(unittest.TestCase):
    def setUp(self):
        self.cfg = tomllib.load(open("config.toml", "rb"))
        self.db = store.connect(":memory:")

    def hook(self, ch, rubric, text, ai_answer="📌 Сақлаб қўйинг — асқотади!"):
        with mock.patch("genplan.ai.available", return_value=True), \
             mock.patch("genplan.ai.hook", return_value=ai_answer) as h:
            out = service.hook_for(self.cfg, self.cfg["channels"][ch], mat(7, rubric, text), self.db)
            return out, h.called

    def test_news_no_hook(self):
        self.assertEqual(self.hook("davra", "Янгиликлар", "Тошкентда янги кўприк очилди.")[0], "")
        self.assertEqual(self.hook("paparazzi", "Шоу-бизнес янгилик", "Хонанда янги альбом тайёрлаётганини айтди.")[0], "")

    def test_music_promo(self):
        out, ai = self.hook("paparazzi", "Клип/премьера", "Янги клип премьераси!")
        self.assertIn(out, self.cfg["channels"]["paparazzi"]["promo_hooks"])
        self.assertFalse(ai)

    def test_useful_ai(self):
        out, ai = self.hook("davra", "Фойдали видео", "Бош оғриғининг сабаблари ва нима қилиш керак.")
        self.assertTrue(ai)
        self.assertEqual(out, "📌 Сақлаб қўйинг — асқотади!")

    def test_dua_fixed(self):
        out, ai = self.hook("davra", "Фойдали видео", "Аллоҳим, фарзандларимга гўзал келажак бер. Дуо")
        self.assertFalse(ai)
        self.assertTrue(out.startswith("🤲") or out.startswith("🕌"))

    def test_humor_fixed(self):
        out, ai = self.hook("davra", "Ҳажвия", "Кулгили латифа 😂")
        self.assertFalse(ai)
        self.assertTrue(out)

    def test_sad_none(self):
        self.assertEqual(self.hook("davra", "Фойдали видео", "Таниқли шифокор вафот этди.")[0], "")


if __name__ == "__main__":
    unittest.main()
