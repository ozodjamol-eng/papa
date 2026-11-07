"""07.11 владелец: один и тот же пост из складов не чаще раза в 30 дней; убранное — никогда."""
import datetime as dt
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import smart, store  # noqa: E402

NOW = dt.datetime(2026, 11, 7, 9, tzinfo=dt.timezone.utc)
LONG = "Уйда осон тайёрланадиган фойдали таом рецепти ва унинг сирлари ҳақида батафсил маълумот беришимиз мумкин"


class Repeat(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")
        self.n = 0

    def add(self, fp, text="", channel="davra", status="draft", days=0, rubric="Фойдали"):
        self.n += 1
        mid = store.add_material(self.db, -1, self.n, text, True, fp=fp)
        store.update(self.db, mid, channel=channel, status=status, rubric=rubric,
                     scheduled_at=(NOW - dt.timedelta(days=days)).isoformat())
        return store.get(self.db, mid)

    def test_same_video_within_30_days(self):
        self.add("m:a", status="published", days=10)
        self.assertTrue(smart.repeat_block(self.db, "davra", self.add("m:a"), NOW))

    def test_after_30_days_ok(self):
        self.add("m:a", status="published", days=40)
        self.assertEqual(smart.repeat_block(self.db, "davra", self.add("m:a"), NOW), "")

    def test_other_channel_ok(self):
        self.add("m:a", channel="xojaobod", status="published", days=3)
        self.assertEqual(smart.repeat_block(self.db, "davra", self.add("m:a"), NOW), "")

    def test_removed_never(self):
        self.add("m:a", status="rejected", days=200)
        self.assertTrue(smart.repeat_block(self.db, "davra", self.add("m:a"), NOW))

    def test_deleted_from_channel_never(self):
        x = self.add("m:a", status="published", days=90)
        store.kv_set(self.db, f"xd_{x['id']}", "1")
        self.assertTrue(smart.repeat_block(self.db, "davra", self.add("m:a"), NOW))

    def test_same_long_text_new_upload(self):
        self.add("m:a", text=LONG, status="published", days=5)
        self.assertTrue(smart.repeat_block(self.db, "davra", self.add("m:b", text=LONG), NOW))

    def test_short_text_not_compared(self):
        self.add("m:a", text="Фойдали видео 👇", status="published", days=1)
        self.assertEqual(smart.repeat_block(self.db, "davra", self.add("m:b", text="Фойдали видео 👇"), NOW), "")

    def test_minbar_untouched(self):
        self.add("m:a", status="published", days=1, rubric=smart.MINBAR)
        self.assertEqual(smart.repeat_block(self.db, "davra", self.add("m:a", rubric=smart.MINBAR), NOW), "")


    def test_music_photo(self):
        m = self.add("m:p", rubric="Қўшиқ")
        store.update(self.db, m["id"], media='[{"type": "photo", "uid": "p"}]')
        self.assertTrue(smart.music_no_video(store.get(self.db, m["id"])))
        store.update(self.db, m["id"], media='[{"type": "video", "uid": "v"}]')
        self.assertFalse(smart.music_no_video(store.get(self.db, m["id"])))


if __name__ == "__main__":
    unittest.main()
