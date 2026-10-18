"""18.10: правка поста в ХАБе канала подхватывается; PaparazziUZ без текста из запаса сам не выходит."""
import datetime as dt
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import bots, hub, plan, smart, store  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
ENV = {"OWNER_IDS": "42", "HUB_CHAT_ID": "-100777", "TEST_GROUP_ID": "-100111", "TEST_CHANNEL_ID": "-100222"}
PHUB = -100555


class Bot:
    def __init__(self):
        self.calls = []

    def __call__(self, method, **p):
        self.calls.append((method, p))
        return {"message_id": 900 + len(self.calls)}


def hubpost(mid, caption="", edited=False):
    p = {"message_id": mid, "chat": {"id": PHUB, "title": "PAPARAZZI · ХАБ"},
         "video": {"file_id": "v", "file_unique_id": f"u{mid}"}, "caption": caption}
    return {"edited_channel_post" if edited else "channel_post": p}


class HubEdit(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")
        self.bot = Bot()
        self._saved = (bots.channel_of, bots.key_of, bots.for_channel)
        bots.channel_of = lambda b: "paparazzi"      # бот-пульт PaparazziUZ
        bots.key_of = lambda b: "paparazzi"
        bots.for_channel = lambda c, b: b

    def tearDown(self):
        bots.channel_of, bots.key_of, bots.for_channel = self._saved

    def mat(self):
        return self.db.execute("SELECT * FROM materials ORDER BY id DESC LIMIT 1").fetchone()

    def test_no_text_waits_then_edit_fills(self):
        self.assertEqual(hub.handle(self.bot, self.db, CFG, ENV, hubpost(10)), "material")
        m = self.mat()
        self.assertEqual(m["stock"], 1)
        self.assertTrue(smart.waits_text(CFG, m))
        card, _ = hub.card(self.db, CFG, m["id"])
        self.assertIn("Без текста не выйдет", card)
        now = dt.datetime(2026, 10, 19, 7, 0, tzinfo=plan.TZ)
        self.assertEqual(smart.fill_from_stock(self.db, CFG, "paparazzi", now), [])
        txt = "ХОНАНДА АЛИ ОТАЖОНОВ ХОНАДОНИДА ҚЎШАЛОҚ ҚУВОНЧ!\nЭгизак — ўғил ва қиз фарзандли бўлди!"
        self.assertEqual(hub.handle(self.bot, self.db, CFG, ENV, hubpost(10, txt, edited=True)), "hub_edit")
        m = self.mat()
        self.assertEqual(m["text"], txt)
        self.assertFalse(smart.waits_text(CFG, m))
        self.assertTrue(any(c[0] == "editMessageText" and "Текст обновлён" in c[1]["text"] for c in self.bot.calls))

    def test_edit_after_publish_warns(self):
        hub.handle(self.bot, self.db, CFG, ENV, hubpost(11, "старый текст"))
        store.update(self.db, self.mat()["id"], status="published")
        self.assertEqual(hub.handle(self.bot, self.db, CFG, ENV, hubpost(11, "новый текст", edited=True)), "edit_late")
        self.assertEqual(self.mat()["text"], "старый текст")

    def test_unknown_chat_edit_ignored(self):
        e = hubpost(12, "x", edited=True)
        e["edited_channel_post"]["chat"] = {"id": -1009, "title": "чужой"}
        self.assertIsNone(hub.handle(self.bot, self.db, CFG, ENV, e))


if __name__ == "__main__":
    unittest.main()
