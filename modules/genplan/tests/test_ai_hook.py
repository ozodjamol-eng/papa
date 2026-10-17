"""17.10: хук по смыслу от ИИ — под юзернеймом; «ЙЎҚ» или мусор → без хука."""
import json
import os
import unittest
from unittest import mock

from genplan import ai, store
from genplan.text import finalize


def fake(answer):
    return lambda req: {"content": [{"type": "text", "text": answer}]}


class AiHook(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")
        self.env = mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "x", "AI_PRIMARY": "claude"}, clear=False)
        self.env.start()
        os.environ.pop("GEMINI_API_KEY", None)

    def tearDown(self):
        self.env.stop()

    def test_meaning_hook(self):
        h = ai.hook(self.db, "Жуда чиройли шеър", "XO'JAOBOD CITY 24", http=fake("📖 Шеър ёққан бўлса, яқинларингизга ҳам юборинг!"))
        self.assertTrue(h.startswith("📖"))

    def test_no_hook(self):
        self.assertEqual(ai.hook(self.db, "Вафот этди", "X", http=fake("ЙЎҚ")), "")
        self.assertEqual(ai.hook(self.db, "Матн", "X", http=fake("Обуна бўлинг @kanal")), "")

    def test_order_username_above_hook(self):
        out = finalize("Жуда чиройли шеър", "📍 Хўжаободдаги энг тезкор хабарлар 👉 @XOJAOBODCITY24",
                       hook="📖 Шеър ёққан бўлса, яқинларингизга ҳам юборинг!")
        lines = out.splitlines()
        self.assertIn("@XOJAOBODCITY24", lines[-2])
        self.assertTrue(lines[-1].startswith("📖"))


if __name__ == "__main__":
    unittest.main()
