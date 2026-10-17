"""17.10: хэштег по смыслу — пост дня #БУГУН, «совуқчилик» не погода, непонятый текст — без хэштега."""
import tomllib
import unittest
from pathlib import Path

from genplan import service, text as T

CFG = tomllib.loads((Path(__file__).resolve().parents[1] / "config.toml").read_text(encoding="utf-8"))
DAY = ("💥 Бугун, 17-октябр - Ўтмишдаги хафагарчиликларни кечириш куни\n\n"
       "🤝 Бугун эски дўстларингиз билан ОРАДАГИ СОВУҚЧИЛИКНИ БАРТАРАФ ЭТИБ, ярашув СМСини юборинг\n"
       "👊Унутманг кечирганни Аллоҳ кечиради!")


def row(text, rubric, guessed):
    return {"text": text, "rubric": rubric, "guessed": guessed}


class HashtagRule(unittest.TestCase):
    def test_day_post_gets_bugun_in_all_live_channels(self):
        for c in ("davra", "paparazzi"):
            self.assertEqual(service.tag_for(CFG, CFG["channels"][c], row(DAY, "Янгиликлар", 1)), "#БУГУН")

    def test_latin_day_post(self):
        s = "Bugun, 17-oktabr - kechirish kuni"
        self.assertEqual(service.tag_for(CFG, CFG["channels"]["davra"], row(s, "Видео", 1)), "#БУГУН")

    def test_sovuqchilik_is_not_weather(self):
        t = T.topic_of("Ораларидаги совуқчиликни унутишди", CFG["topics"])
        self.assertTrue(t is None or t["name"] != "Об-ҳаво")
        self.assertEqual(T.topic_of("Эртага совуқ бўлади", CFG["topics"])["name"], "Об-ҳаво")

    def test_dua_is_dua_not_qiziqarli(self):
        dua = ("🤲Гўзал дуо\n\n\"Аллоҳим, фарзандларимни келажакларини гўзал қил. Ризқларини кенг, умрларини баракали қил.\"")
        for g in (0, 1):
            self.assertEqual(service.tag_for(CFG, CFG["channels"]["davra"], row(dua, "Қизиқарли", g)), "#ДУО")

    def test_vague_rubric_no_tag(self):
        self.assertEqual(service.tag_for(CFG, CFG["channels"]["davra"], row("Ажойиб лаҳза", "Қизиқарли", 0)), "")

    def test_meaning_tag(self):
        self.assertEqual(service.tag_for(CFG, CFG["channels"]["davra"], row("Терма жамоа чемпион бўлди", "Видео", 1)), "#СПОРТ")

    def test_unknown_text_no_tag(self):
        self.assertEqual(service.tag_for(CFG, CFG["channels"]["davra"], row("Ажойиб лаҳза", "Видео", 1)), "")

    def test_owner_choice_keeps_tag(self):
        self.assertEqual(service.tag_for(CFG, CFG["channels"]["davra"], row("Ажойиб лаҳза", "Ҳажвия", 0)), "#ҲАЖВИЯ")

    def test_greeting(self):
        self.assertEqual(service.tag_for(CFG, CFG["channels"]["davra"], row("☀️ Хайрли тонг, азизлар!", "Видео", 1)), "#ХАЙРЛИ_ТОНГ")

    def test_day_hook_not_weather(self):
        h = T.pick_hook(CFG["channels"]["davra"], "Янгиликлар", 0, DAY, CFG["topics"])
        self.assertNotIn("Об-ҳаво", h)

    def test_news_mid_text_bugun_not_day(self):
        s = "Тошкентда янги метро бекати очилди.\nБугун йўловчилар учун бепул."
        self.assertNotEqual(service.tag_for(CFG, CFG["channels"]["davra"], row(s, "Янгиликлар", 0)), "#БУГУН")


if __name__ == "__main__":
    unittest.main()
