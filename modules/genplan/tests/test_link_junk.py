"""17.10 (А): чужие ссылки, спрятанные в слово, — строка-хвост уходит; наша подпись и обычный текст остаются."""
import unittest

from genplan.text import drop_lines, finalize, link_junk


def ent(text, word, typ="text_link", url="https://t.me/x"):
    off = len(text[:text.index(word)].encode("utf-16-le")) // 2
    e = {"type": typ, "offset": off, "length": len(word.encode("utf-16-le")) // 2}
    if typ == "text_link":
        e["url"] = url
    return e


class LinkJunk(unittest.TestCase):
    def test_tezkor(self):
        t = ("‼️ 9 йиллик қамоқдан фронтга\n\nРоссияда гиёҳвандлик воситалари савдоси учун қамалган фуқаро ...\n\n"
             "⬇️ Yuklovchibot - Musiqa topuvchi!\n\nБатафсил 👉🏻 Тезкор24")
        j = link_junk(t, [ent(t, "Yuklovchibot", url="https://t.me/Yuklovchibot"), ent(t, "Тезкор24", url="https://t.me/tezkor24")])
        out = finalize(t, "🎉 @kattadavrauz", junk=j)
        self.assertNotIn("Yuklovchibot", out)
        self.assertNotIn("Тезкор24", out)
        self.assertIn("Россияда гиёҳвандлик", out)
        self.assertTrue(out.rstrip().endswith("@kattadavrauz"))

    def test_bozor(self):
        t = ("⚡️ Ўзбекистонда яна ёз ҳавоси\n\nДам олиш кунлари ҳаво +30 даражагача кўтарилиши кутилмоқда.\n\n"
             "📷 Инстаграм\n\n👉 @Uzb1000xilbozor обуна бўлинг!")
        j = link_junk(t, [ent(t, "Инстаграм", url="https://instagram.com/x"), ent(t, "@Uzb1000xilbozor", "mention")])
        out = drop_lines(t, j)
        self.assertNotIn("Инстаграм", out)
        self.assertNotIn("обуна", out)
        self.assertIn("+30 даражагача", out)

    def test_link_inside_sentence_keeps_text(self):
        t = "Президент фармонига кўра, 1 ноябрдан бошлаб янги тартиб жорий этилади ва барча ҳудудларда қўлланилади."
        self.assertEqual(link_junk(t, [ent(t, "фармонига", url="https://lex.uz/1")]), [])

    def test_own_channel_link_stays(self):
        t = "Видео\n\nБатафсил 👉 КАТТА ДАВРА"
        self.assertEqual(link_junk(t, [ent(t, "КАТТА ДАВРА", url="https://t.me/kattadavrauz")], ("@kattadavrauz",)), [])

    def test_ad_untouched(self):
        t = "Чегирма!\n\n📷 Инстаграм"
        j = link_junk(t, [ent(t, "Инстаграм", url="https://instagram.com/shop")])
        self.assertIn("Инстаграм", finalize(t, "", is_ad=True, junk=j))

    def test_batafsil_without_entity(self):
        self.assertNotIn("Тезкор", finalize("Матн бу ерда.\n\nБатафсил 👉 Тезкор24", ""))

    def test_signature_variants_not_duplicated(self):
        a, b = "📍 Хўжаободнинг энг тезкор хабарлари 👉 @XOJAOBODCITY24", "❤️ Қўшниларингиз ҳам билсин 👉 @XOJAOBODCITY24"
        out = finalize(f"Матн.\n\n{b}", a, signatures=(a, b), own=("@XOJAOBODCITY24",))
        self.assertEqual(out.count("@XOJAOBODCITY24"), 1)


if __name__ == "__main__":
    unittest.main()
