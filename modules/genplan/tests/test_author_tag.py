"""24.10 владелец: хэштег автора сверху (#ТЕЗКОР) не убирать — чистим только низ."""
import unittest

from genplan.text import author_tag, finalize

SIG = "📍 Хўжаобод · Янгиликлар 👉 @XOJAOBODCITY24"
POST = ("#ТЕЗКОР\n⚡️АНДИЖОНДА ЧЕГАРАДАН ОЛИБ ЧИҚИЛАЁТГАН 20 МИНГ ДОЛЛАР АНИҚЛАНДИ\n\n"
        "Хонобод чегара божхона пости орқали қўшни давлатга чиқиб кетаётган автомобиль текширилганда, "
        "20 минг доллар нақд пул топилган.\n\n👉 @tezkor_xabarlar_uz\n#tezkor #news")


class AuthorTag(unittest.TestCase):
    def test_tezkor_kept_bottom_cleaned(self):
        out = finalize(POST, SIG, own=("XOJAOBODCITY24",), tag="#ЯНГИЛИК", author_first=True)
        self.assertTrue(out.startswith("#ТЕЗКОР\n⚡️АНДИЖОНДА"), out)
        self.assertEqual(out.count("#"), 1, out)             # один хэштег, бот свой не добавил
        self.assertNotIn("tezkor_xabarlar", out)
        self.assertNotIn("#news", out)
        self.assertTrue(out.endswith(SIG))

    def test_tag_on_headline_line(self):
        out = finalize("#ТЕЗКОР ⚡️ ЗАГОЛОВОК\n\nМатн.", SIG, author_first=True)
        self.assertTrue(out.startswith("#ТЕЗКОР\n⚡️ ЗАГОЛОВОК"), out)

    def test_latin_tag_to_cyrillic(self):
        self.assertEqual(author_tag("#tezkor\nМатн")[0], "#ТЕЗКОР")

    def test_ad_tag_not_kept(self):
        out = finalize("#reklama\nМатн бу ерда.", SIG, author_first=True)
        self.assertNotIn("#", out.replace("@", ""))

    def test_no_author_tag_bot_tag_used(self):
        out = finalize("Матн бу ерда.", SIG, tag="#ЮМОР", author_first=True)
        self.assertTrue(out.startswith("#ЮМОР\nМатн"))

    def test_old_paths_unchanged(self):                      # утро/прочее — без author_first, как раньше
        out = finalize("#tezkor_tong\nХайрли тонг!", SIG, tag="#ХАЙРЛИ_ТОНГ")
        self.assertTrue(out.startswith("#ХАЙРЛИ_ТОНГ\n"), out)
        self.assertEqual(out.count("#"), 1, out)


if __name__ == "__main__":
    unittest.main()
