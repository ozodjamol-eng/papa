"""31.10 этап 2: заказ ИИ-ассистента (✅) → реклама в пульте Хўжаобода с экраном «когда выпустить?»."""
import json
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import adsin, bots, store  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))


class Bot:
    def __init__(self):
        self.calls = []

    def __call__(self, method, **p):
        self.calls.append((method, p))
        return {"message_id": 900 + len(self.calls)}


class AdsIn(unittest.TestCase):
    def setUp(self):
        self.inbox = Path(tempfile.mkdtemp())
        self.db = store.connect(":memory:")
        self.bot = Bot()
        bots.REG.clear(); bots.REG["xojaobod"] = self.bot
        self.ups = []

        def up(token, method, fields, files):
            self.ups.append((method, fields, files))
            return {"message_id": 50, "chat": {"id": 42, "type": "private"}, "from": {"id": 1, "is_bot": True},
                    "photo": [{"file_id": "X", "file_unique_id": "ux"}], "caption": fields.get("caption", "")}
        self.up = up

    def pack(self, n=1, media=True):
        d = self.inbox / f"order-{n}"
        d.mkdir()
        if media:
            (d / "0.jpg").write_bytes(b"IMG")
        (d / "meta.json").write_text(json.dumps({"id": n, "client_chat": 555, "bc": "BC", "client": "Ali", "text": "Дўкон очилди!",
                                                  "media": [{"kind": "photo", "file": "0.jpg"}] if media else [],
                                                  "days": 3, "evening": True, "pin": False, "what": "дўкон"}), encoding="utf-8")
        return d

    def test_order_becomes_ad_card(self):
        d = self.pack()
        self.assertEqual(adsin.scan(self.bot, "T", self.db, CFG, [42], inbox=self.inbox, up=self.up, log=lambda s: None), 1)
        self.assertEqual(self.ups[0][0], "sendPhoto")
        self.assertFalse(d.exists())
        m = self.db.execute("SELECT * FROM materials ORDER BY id DESC LIMIT 1").fetchone()
        self.assertEqual((m["channel"], m["rubric"], m["status"]), ("xojaobod", "Реклама", "draft"))
        edits = [p for meth, p in self.bot.calls if meth == "editMessageText"]
        self.assertTrue(edits and "когда выпустить" in edits[-1]["text"] and "3 кун" in edits[-1]["text"])
        self.assertEqual(json.loads(store.kv_get(self.db, f"ad_order_{m['id']}"))["client_chat"], 555)

    def test_half_written_waits(self):
        d = self.pack()
        (d / "meta.json").unlink()
        self.assertEqual(adsin.scan(self.bot, "T", self.db, CFG, [42], inbox=self.inbox, up=self.up, log=lambda s: None), 0)
        self.assertTrue(d.exists())

    def test_upload_error_marks_bad(self):
        self.pack()
        def boom(*a):
            raise RuntimeError("sendPhoto: too big")
        adsin.scan(self.bot, "T", self.db, CFG, [42], inbox=self.inbox, up=boom, log=lambda s: None)
        self.assertTrue((self.inbox / "bad-1").exists())

    def test_text_only(self):
        self.pack(media=False)
        adsin.scan(self.bot, "T", self.db, CFG, [42], inbox=self.inbox, up=self.up, log=lambda s: None)
        self.assertEqual(self.ups[0][0], "sendMessage")


if __name__ == "__main__":
    unittest.main()
