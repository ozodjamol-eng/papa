"""🧹 06.11: поздравления по времени уходят из вечных хабов в «ТАБРИКЛАР»."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as N

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from razvedka import hubs, timing, tozalash  # noqa: E402


class T(unittest.TestCase):
    def test_kind(self):
        self.assertEqual(timing.kind("🕌 ЖУМА МУБОРАК Масжидда"), "juma")
        self.assertEqual(timing.kind("#Хайрли_тонг азизлар"), "morning")
        self.assertEqual(timing.kind("Xayrli tun"), "night")
        self.assertIsNone(timing.kind("🤲 ҲАЁТИЙ ПАНД-НАСИҲАТЛАР"))
        self.assertIsNone(timing.kind("Кечаси совуқ"))

    def test_pick_album(self):
        a = {"id": 1, "text": "", "msgs": [N(message=""), N(message="Жумангиз муборак бўлсин")]}
        b = {"id": 2, "text": "Ош рецепти", "msgs": [N(message="Ош рецепти")]}
        self.assertEqual([x["id"] for x in tozalash.pick([a, b])], [1])

    def test_hub_exists(self):
        self.assertIn(timing.HUB, hubs.HUBS)
        self.assertTrue(hubs.HUBS[timing.HUB]["create"])
        self.assertIsNone(hubs.hub_for_code("faith") == timing.HUB or None)


if __name__ == "__main__":
    unittest.main()
