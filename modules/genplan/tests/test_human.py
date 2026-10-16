import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import human, text  # noqa: E402


class Clean(unittest.TestCase):
    def test_invisible_removed_emoji_kept(self):
        self.assertEqual(human.clean("Ян​ги﻿ хабар­ 👨‍👩‍👧 ❤️"), "Янги хабар 👨‍👩‍👧 ❤️")

    def test_nbsp_and_repeats(self):
        self.assertEqual(human.clean("Зўр видео!!!! Нима???  Кейин...."), "Зўр видео! Нима?  Кейин…")
        self.assertEqual(human.clean("Ростми?!"), "Ростми?!")

    def test_dash_untouched(self):
        self.assertEqual(human.clean("Бугун — Ота-оналар куни"), "Бугун — Ота-оналар куни")

    def test_finalize_cleans_but_ads_untouched(self):
        self.assertNotIn("​", text.finalize("ЯНГИ​ ХАБАР", "@kattadavrauz"))
        self.assertIn("​", text.finalize("РЕКЛАМА​", "", is_ad=True))


class Headline(unittest.TestCase):
    def test_greeting(self):
        self.assertIn("приветствия", human.headline_note("#ЯНГИЛИК\nАссалому алайкум азиз обуначилар!\nМатн"))

    def test_cliche(self):
        self.assertIn("ИИ", human.headline_note("🔥 ЯНГИ МАШИНА\nХулоса қилиб айтганда, зўр."))

    def test_long(self):
        self.assertIn("длинная", human.headline_note("а" * 120))

    def test_good_headline_silent(self):
        self.assertEqual(human.headline_note("🔥 ТОШКЕНТДА ЯНГИ МЕТРО ОЧИЛДИ\n\nБатафсил…"), "")
        self.assertEqual(human.headline_note(""), "")


if __name__ == "__main__":
    unittest.main()
