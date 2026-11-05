"""⚡ 05.11 владелец: срочное полезное без политики. Пост, который Разведка переслала как МУҲИМ, не выходит сам,
не режется новостным запретом и не встаёт в сетку — только 🆘 владельца."""
import json
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import hub, muhim, store  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
TEXT = "Эртага 09:00 дан 17:00 гача Хўжаобод туманининг бир қатор маҳаллаларида электр энергияси ўчирилади"


class Bot:
    def __init__(self):
        self.calls = []

    def __call__(self, method, **p):
        self.calls.append((method, p))
        return {"message_id": 900 + len(self.calls)}


def fwd(mid, src_mid, text=TEXT):
    chat = {"id": -1005551, "title": "Андижон Тезкор", "type": "channel", "username": "andijon_tezkor"}
    return {"message_id": mid, "from": {"id": 42}, "chat": {"id": 42, "type": "private"},
            "photo": [{"file_id": f"f{mid}", "file_unique_id": f"u{mid}"}], "caption": text,
            "forward_origin": {"type": "channel", "chat": chat, "message_id": src_mid}}


class T(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")
        self.cfg = {**CFG, "channels": {k: dict(v) for k, v in CFG["channels"].items()}}
        self.tmp = tempfile.TemporaryDirectory()
        self.f = Path(self.tmp.name) / "muhim.json"
        self.f.write_text(json.dumps({"keys": {"-1005551:77": {"channel": "xojaobod", "ts": "2026-11-05T14:00:00+00:00"}}}))
        self.old, muhim.FILE = muhim.FILE, self.f

    def tearDown(self):
        muhim.FILE = self.old
        self.tmp.cleanup()

    def test_key_and_hit(self):
        self.assertEqual(muhim.key_of(fwd(1, 77)), "-1005551:77")
        self.assertTrue(muhim.hit([fwd(1, 77)]))
        self.assertFalse(muhim.hit([fwd(1, 78)]))
        self.assertFalse(muhim.hit([{"message_id": 1, "text": "x"}]))

    def test_muhim_card_waits_for_owner(self):
        bot = Bot()
        hub.intake(bot, self.db, self.cfg, {42}, 42, [10], [fwd(10, 77)], reply_chat=42, channel="xojaobod")
        r = store.get(self.db, 1)
        self.assertEqual((r["status"], r["auto"], r["stock"]), ("draft", 0, 0))     # не в сетке, сам не выйдет
        txt = bot.calls[-1][1]["text"]
        self.assertIn("⚡ МУҲИМ", txt)
        self.assertNotIn("⛔ Новость", txt)                                           # новостной запрет не режет
        kb = json.dumps(bot.calls[-1][1]["reply_markup"], ensure_ascii=False)
        self.assertIn("🆘", kb)
        self.assertIn("🗑 Не нужно", kb)
        self.assertNotIn("📣 Реклама", kb)                                          # без лишних кнопок

    def test_other_forward_unchanged(self):
        bot = Bot()
        hub.intake(bot, self.db, self.cfg, {42}, 42, [11], [fwd(11, 78)], reply_chat=42, channel="xojaobod")
        self.assertNotIn("⚡ МУҲИМ", bot.calls[-1][1]["text"])


if __name__ == "__main__":
    unittest.main()
