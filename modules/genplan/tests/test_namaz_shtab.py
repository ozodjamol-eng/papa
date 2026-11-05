"""05.11 владелец: «лучше перевести в PAPA ШТАБ, чтобы оттуда давал всем». Намоз вводится только в ШТАБе."""
import datetime as dt
import json
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import adsin, bots, fabrika, hub, menu, namaz, plan, store  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
ENV = {"OWNER_IDS": "42", "HUB_CHAT_ID": "-100777", "GENPLAN_BOT_TOKEN": "main", "SHTAB_BOT_TOKEN": "shtab"}
TXT = ("Намоз вақтлари: 06.11.2026 йил\n\n🕔 Бомдод   06:10\n🕑 Пешин     12:45\n🕔 Аср           15:30\n"
       "🕖 Шом         17:15\n🕘 Хуфтон     18:45")
THU = dt.date(2026, 11, 5)


class Bot:
    def __init__(self):
        self.calls = []

    def __call__(self, m, **p):
        self.calls.append((m, p))
        return {"message_id": 900 + len(self.calls)}


class TestShtabNamaz(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")
        namaz.setup(self.db)
        self.tmp = tempfile.TemporaryDirectory()
        self.old = (fabrika.STATE, hub._now, hub._oboi_render, adsin.upload)
        fabrika.STATE = Path(self.tmp.name)
        hub._now = lambda: plan.slot_time(THU, "18:30")
        self.ups = []

        def render(day, times, out):
            out.mkdir(parents=True, exist_ok=True)
            fs = []
            for i in range(5):
                f = out / f"{i}.jpg"; f.write_bytes(b"jpg"); fs.append(f)
            return fs, "<b>НАМОЗ</b>"
        hub._oboi_render = render
        adsin.upload = lambda token, method, fields, files: self.ups.append((token, method, len(files))) or [{}]
        self.shtab, self.pult = Bot(), Bot()
        bots.setup(CFG, {"GENPLAN_BOT_TOKEN": "main"}, lambda t: Bot())
        bots.SHTAB.update(bot=self.shtab, token="shtab")

    def tearDown(self):
        fabrika.STATE, hub._now, hub._oboi_render, adsin.upload = self.old
        bots.SHTAB.clear()
        self.tmp.cleanup()

    def upd(self, text):
        return {"message": {"message_id": 7, "chat": {"id": 42, "type": "private"}, "from": {"id": 42}, "text": text}}

    def test_text_in_shtab_preview_then_ok(self):
        self.assertEqual(hub.shtab_handle(self.shtab, self.db, CFG, ENV, self.upd(TXT)), "namaz_tdraft")
        self.assertEqual(self.ups[0], ("shtab", "sendMediaGroup", 5))           # обои — ключом ШТАБа, в чат ШТАБа
        self.assertIsNone(namaz.schedule_for(self.db, dt.date(2026, 11, 6)))   # до ✅ ничего
        d = json.loads(store.kv_get(self.db, "namaz_tdraft"))
        self.assertEqual(d["day"], "2026-11-05")                               # 06.11 (пт) → с четверга 05.11
        cq = {"callback_query": {"id": "q", "from": {"id": 42}, "data": "nzt:ok",
                                 "message": {"chat": {"id": 42}, "message_id": d["card"], "text": "x"}}}
        self.assertEqual(hub.shtab_handle(self.shtab, self.db, CFG, ENV, cq), "namaz_t_ok")
        s = namaz.schedule_for(self.db, dt.date(2026, 11, 6))
        self.assertEqual((s["bomdod"], s["xufton"]), ("06:10", "18:45"))

    def test_button_shows_current(self):
        self.assertEqual(hub.shtab_handle(self.shtab, self.db, CFG, ENV, self.upd(hub.B_SHTAB_NAMAZ)), "namaz_help")
        self.assertEqual(self.shtab.calls[-1][1]["reply_markup"], hub.SHTAB_KB)

    def test_other_text_still_overview(self):
        self.assertEqual(hub.shtab_handle(self.shtab, self.db, CFG, ENV, self.upd("салом")), "overview")

    def test_pult_sends_to_shtab_and_settings_has_no_namaz(self):
        self.assertIsNot(menu.panel_markup(CFG, "xojaobod", menu.P_SETTINGS), None)
        self.assertIs(menu.panel_markup(CFG, "xojaobod", menu.P_SETTINGS), menu.PANEL)
        self.assertEqual(bots.token_of(self.shtab, ENV), "shtab")


if __name__ == "__main__":
    unittest.main()
