"""07.11 владелец: копии в хабах — удалять (самый старый остаётся); короткие общие подписи — не копия."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from razvedka import hubaudit, hubgate  # noqa: E402

LONG = "Ҳаётда ҳеч қачон таслим бўлманг, ҳар бир қийинчилик сизни янада кучли қилади ва мақсадга яқинлаштиради, олға!"


class T(unittest.TestCase):
    def test_same_file_dup(self):
        g = hubaudit.dup_groups([{"id": 5, "media": ["d1"], "text": ""}, {"id": 2, "media": ["d1"], "text": ""},
                                 {"id": 3, "media": ["d2"], "text": ""}])
        self.assertEqual(g, [[2, 5]])

    def test_long_text_dup(self):
        g = hubaudit.dup_groups([{"id": 1, "media": ["d1"], "text": LONG}, {"id": 2, "media": ["d9"], "text": LONG}])
        self.assertEqual(g, [[1, 2]])

    def test_short_caption_not_dup(self):
        t = "😂 КУЛГИЛИ ВИДЕО\nКайфиятингизни кўтаринг!"
        self.assertEqual(hubaudit.dup_groups([{"id": 1, "media": ["d1"], "text": t}, {"id": 2, "media": ["d2"], "text": t}]), [])

    def test_keys(self):
        m = NS(document=NS(id=7), photo=None, message="")
        self.assertIn("d7", hubgate.keys_of([m], LONG))
        self.assertEqual(hubgate.text_key("коротко"), "")


if __name__ == "__main__":
    unittest.main()
