import importlib.util, unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("talaffuz", Path(__file__).parents[1] / "talaffuz.py")
t = importlib.util.module_from_spec(spec); spec.loader.exec_module(t)


class T(unittest.TestCase):
    def test_birinchi(self):
        self.assertEqual(t.tayyorla("Биринчи қадам.")[0], "Бирнчи қадам.")
        self.assertEqual(t.tayyorla("бу биринчидан муҳим")[0], "бу бирнчидан муҳим")
        self.assertEqual(t.tayyorla("BIRINCHI kun")[0], "BIRNCHI kun")
        self.assertEqual(t.tayyorla("Birinchi kun")[0], "Birnchi kun")

    def test_word_middle_untouched(self):
        self.assertEqual(t.tayyorla("кабиринчи")[0], "кабиринчи")

    def test_undov(self):
        s, o = t.tayyorla("Келинг!")
        self.assertEqual(s, "Келинг.")
        self.assertEqual(t.tayyorla("Келинг!", undov=False)[0], "Келинг!")

    def test_asosiy(self):
        st = t.asosiy_qadam({"do": "tts", "text": "x"})
        self.assertEqual(st["voice_id"], "ph7cEBlVHFfCY5GiGvA2")
        self.assertEqual(st["model"], "eleven_v4")
        st2 = t.asosiy_qadam({"voice_id": "abc"})
        self.assertNotIn("model", st2)


if __name__ == "__main__":
    unittest.main()
