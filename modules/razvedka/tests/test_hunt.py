import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from razvedka import hunt  # noqa: E402


class TestHunt(unittest.TestCase):
    def test_weekday(self):
        self.assertEqual(hunt.weekday_of("🕌 ЖУМА ТОНГИ МУБОРАК"), "Жума")
        self.assertEqual(hunt.weekday_of("Xayrli tong! Shanba kuni"), "Шанба")
        self.assertEqual(hunt.weekday_of("Якшанба тонги"), "Якшанба")
        self.assertEqual(hunt.weekday_of("Душанба"), "Душанба")
        self.assertIsNone(hunt.weekday_of("Хайрли тонг, азизлар"))

    def test_pick_limits_and_dedupe(self):
        c = [{"key": str(i), "views": i, "size": 1000 + i, "duration": 10, "weekday": "Жума"} for i in range(30)]
        c.append({"key": "dup", "views": 99, "size": 1029, "duration": 10, "weekday": None})
        out = hunt.pick(c)
        self.assertEqual(len([x for x in out if x["weekday"] == "Жума"]), hunt.PER_DAY)
        self.assertNotIn("29", [x["key"] for x in out])
        self.assertEqual(out[0]["key"], "dup")                 # самый просматриваемый — первым, его дубль отброшен


if __name__ == "__main__":
    unittest.main()
