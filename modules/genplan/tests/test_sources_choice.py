"""26.10: карточка выбора источников в PAPA ШТАБ — галочки, «✅ Утверждаю», choice.json."""
import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import hub, sources_choice  # noqa: E402

KB = {"inline_keyboard": [
    [{"text": "☑ 1. BUGUNGI GAP", "callback_data": "sw:t:davra:news:111"}],
    [{"text": "⬜ 2. Tezkor Yangiliklar ⚡", "callback_data": "sw:t:davra:news:-222"}],
    [{"text": "☑ 3. Kulgi", "callback_data": "sw:t:davra:humor:333"}],
    [{"text": "✅ Утверждаю", "callback_data": "sw:ok:davra"}]]}


class Bot:
    def __init__(self):
        self.calls = []

    def __call__(self, method, **p):
        self.calls.append((method, p))
        return {}


def cq(data, kb=KB):
    return {"id": "1", "from": {"id": 7}, "data": data,
            "message": {"chat": {"id": 7}, "message_id": 5, "text": "📡 КАТТА ДАВРА · ВЫБОР", "reply_markup": kb}}


class TestSourcesChoice(unittest.TestCase):
    def test_toggle(self):
        kb = sources_choice.toggle(KB, "sw:t:davra:news:-222")
        self.assertTrue(kb["inline_keyboard"][1][0]["text"].startswith("☑ 2."))
        kb = sources_choice.toggle(kb, "sw:t:davra:news:111")
        self.assertTrue(kb["inline_keyboard"][0][0]["text"].startswith("⬜ 1."))
        self.assertTrue(KB["inline_keyboard"][0][0]["text"].startswith("☑"))          # исходник не портим

    def test_selected(self):
        self.assertEqual(sources_choice.selected(KB, "davra"),
                         {"news": [{"id": 111, "title": "BUGUNGI GAP"}], "humor": [{"id": 333, "title": "Kulgi"}]})
        self.assertEqual(sources_choice.selected(KB, "paparazzi"), {})

    def test_ok_saves_and_keeps_other_channels(self):
        d = Path(tempfile.mkdtemp())
        f = d / "choice.json"
        f.write_text(json.dumps({"version": 2, "channels": {"paparazzi": {"music": [{"id": 9, "title": "X"}]}}}))
        bot = Bot()
        self.assertEqual(sources_choice.callback(bot, cq("sw:ok:davra"), f), "sw_ok")
        data = json.loads(f.read_text())
        self.assertEqual([x["id"] for x in data["channels"]["davra"]["news"]], [111])
        self.assertEqual(data["channels"]["paparazzi"]["music"][0]["id"], 9)          # чужой выбор не затёрт
        self.assertEqual(stat.S_IMODE(f.stat().st_mode), 0o640)                       # куратор Разведки читает
        edit = [p for m, p in bot.calls if m == "editMessageText"][0]
        self.assertIn("✅ УТВЕРЖДЕНО", edit["text"])                                   # итог — постоянной строкой
        self.assertIn("источников: 2", edit["text"])
        self.assertIsInstance(edit["reply_markup"], dict)

    def test_reapprove_replaces_stamp(self):
        d = Path(tempfile.mkdtemp())
        bot = Bot()
        c = cq("sw:ok:davra")
        c["message"]["text"] += "\n\n✅ УТВЕРЖДЕНО 26.10 08:40 · источников: 5\nстарое"
        sources_choice.callback(bot, c, d / "choice.json")
        edit = [p for m, p in bot.calls if m == "editMessageText"][0]
        self.assertEqual(edit["text"].count("✅ УТВЕРЖДЕНО"), 1)

    def test_toggle_callback_and_bad(self):
        bot = Bot()
        self.assertEqual(sources_choice.callback(bot, cq("sw:t:davra:news:-222"), Path(tempfile.mkdtemp()) / "c.json"),
                         "sw_toggle")
        self.assertEqual(bot.calls[0][0], "editMessageReplyMarkup")
        self.assertEqual(sources_choice.callback(Bot(), cq("sw:ok:evil"), Path("/nonexistent/x.json")), "bad")

    def test_channel_pult_routes_sw(self):
        bot = Bot()
        self.assertEqual(hub.callback(bot, None, {}, {7}, cq("sw:t:davra:news:111")), "sw_toggle")   # пульт канала
        self.assertEqual(hub.callback(Bot(), None, {}, {8}, cq("sw:t:davra:news:111")), "denied")

    def test_shtab_routes_sw(self):
        bot = Bot()
        upd = {"callback_query": cq("sw:t:davra:news:111")}
        self.assertEqual(hub.shtab_handle(bot, None, {}, {"OWNER_IDS": "7"}, upd), "sw_toggle")
        self.assertEqual(hub.shtab_handle(Bot(), None, {}, {"OWNER_IDS": "8"}, upd), "denied")  # чужой — нельзя


if __name__ == "__main__":
    unittest.main()


class RubricCodeTest(unittest.TestCase):
    def test_rubric_code(self):
        import json
        import tempfile
        from pathlib import Path
        from genplan import sources_choice as S
        p = Path(tempfile.mkdtemp()) / "c.json"
        p.write_text(json.dumps({"channels": {"xojaobod": {"humor": [{"id": 777}], "warn": [{"id": 888}]}}}))
        self.assertEqual(S.rubric_code("xojaobod", -1000000000777, p), "humor")
        self.assertEqual(S.rubric_code("xojaobod", 888, p), "warn")
        self.assertIsNone(S.rubric_code("davra", 777, p))
