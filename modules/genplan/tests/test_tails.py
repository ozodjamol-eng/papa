"""18.10: бот сам учит подписи источника и кнопка «🧹 Мусор»."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from genplan import store, tails, text  # noqa: E402

FOOT = "🔖 Batafsil kanalimizda: Tarix olami\n✅ Bizga qo'shiling — har kuni yangi tarix"


def post(i):
    return f"Sarlavha {i}\nBu {i}-chi postning asosiy matni, har safar boshqacha.\n\n{FOOT}"


class TailsTest(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")

    def test_learns_after_three(self):
        self.assertEqual(tails.observe(self.db, "@tarix", post(1)), [])
        self.assertEqual(tails.observe(self.db, "@tarix", post(2)), [])
        self.assertEqual(len(tails.observe(self.db, "@tarix", post(3))), 2)
        junk = tails.junk_for(self.db, "@tarix", post(4))
        out = text.finalize(text.drop_lines(post(4), junk), "@kattadavrauz")
        self.assertIn("4-чи", out)
        self.assertNotIn("Tarix olami", out)
        self.assertNotIn("Bizga", out)
        self.assertEqual(tails.junk_for(self.db, "@boshqa", post(4)), [])     # другой источник — не трогаем

    def test_no_source_does_not_self_learn(self):
        for i in range(5):
            tails.observe(self.db, None, post(i))
        self.assertEqual(tails.junk_for(self.db, None, post(9)), [])

    def test_own_signature_never_learned(self):
        t = "Sarlavha\nMatn\n\n@kattadavrauz\nДўстларга ҳам улашинг"
        for _ in range(4):
            tails.observe(self.db, "@x", t, own=("kattadavrauz",))
        self.assertNotIn("@kattadavrauz", tails.junk_for(self.db, "@x", t))

    def test_first_line_kept(self):
        tails.learn(self.db, "@x", "Ассалому алайкум")
        self.assertEqual(tails.junk_for(self.db, "@x", "Ассалому алайкум\nМатн"), [])
        self.assertEqual(tails.junk_for(self.db, "@x", "Сарлавҳа\nМатн\nАссалому алайкум"), ["Ассалому алайкум"])

    def test_merged_and_button(self):
        mid = store.add_material(self.db, 1, 10, post(1), False)
        store.update(self.db, mid, source="@tarix", junk=json.dumps(["x"]))
        tails.learn(self.db, "@tarix", "✅ Bizga qo'shiling — har kuni yangi tarix")
        m = store.get(self.db, mid)
        self.assertIn("✅ Bizga qo'shiling — har kuni yangi tarix", tails.merged(self.db, m))
        self.assertIn("x", tails.merged(self.db, m))

    def test_clean_lines_for_button(self):
        from genplan import hub
        mid = store.add_material(self.db, 1, 11, "Sarlavha\nMatn\n\nMANBA — izohlarda\nReklama: @bot_x\nOxirgi qator", False)
        cands = [ln for _, ln in hub.clean_lines(self.db, store.get(self.db, mid))]
        self.assertNotIn("Sarlavha", cands)
        self.assertNotIn("MANBA — izohlarda", cands)      # уже убирается правилом
        self.assertIn("Oxirgi qator", cands)


if __name__ == "__main__":
    unittest.main()


class ButtonFlowTest(unittest.TestCase):
    def test_cl_cj_callbacks(self):
        import tomllib
        from genplan import hub
        cfg = tomllib.loads((Path(__file__).resolve().parent.parent / "config.toml").read_text(encoding="utf-8"))
        db = store.connect(":memory:")
        ch = next(iter(cfg["channels"]))
        mid = store.add_material(db, 1, 12, "Sarlavha\nMatn birinchi\n\nOxirgi reklama qatori", False)
        store.update(db, mid, channel=ch, source="@src", status="draft")
        calls = []

        def bot(method, **kw):
            calls.append((method, kw))
            return {"message_id": 1}
        cq = {"id": "1", "from": {"id": 7}, "message": {"chat": {"id": 7}, "message_id": 5}, "data": f"cl:{mid}"}
        hub.callback(bot, db, cfg, {7}, cq)
        kb = [c for c in calls if c[0] == "editMessageText"][-1][1]["reply_markup"]["inline_keyboard"]
        btn = next(b[0] for b in kb if "Oxirgi" in b[0]["text"])
        hub.callback(bot, db, cfg, {7}, dict(cq, data=btn["callback_data"]))
        self.assertEqual(tails.junk_for(db, "@src", "X\nY\nOxirgi reklama qatori"), ["Oxirgi reklama qatori"])
        t, _ = hub.card(db, cfg, mid)
        self.assertNotIn("Oxirgi", t)
