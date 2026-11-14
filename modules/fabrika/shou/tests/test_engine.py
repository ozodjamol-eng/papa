import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import engine as E  # noqa: E402

JOB = {"src": "a.mp4", "quiet_until": 22.0, "song_from": 22.0,
       "titles": [{"lines": ["МОҲИМ"], "at": 27.97}, {"lines": ["ЯНГИ", "КЛИП"], "at": 29.03}],
       "caption": {"lines": ["КУТЯПСИЗМИ?", "ИЗОҲДА ЁЗИНГ"], "from": 43.0, "to": 47.2},
       "window": {"from": 51.4, "to": 53.9},
       "voice": [{"file": "m01.mp3", "at": 26.6}, {"file": "m02.mp3", "at": 32.1}]}
LEN = {"m01.mp3": 4.0, "m02.mp3": 4.5}


class T(unittest.TestCase):
    def test_etalon_ok(self):
        self.assertEqual(E.check(JOB, 106.0, LEN), [])

    def test_voice_rules(self):
        early = {**JOB, "voice": [{"file": "m01.mp3", "at": 24.0}]}                 # раньше 4 с чистой песни
        self.assertTrue(any("чистой песни" in b for b in E.check(early, 106.0, LEN)))
        late = {**JOB, "voice": [{"file": "m01.mp3", "at": 101.0}]}                 # в конце песня должна звучать одна
        self.assertTrue(any("звучать одна" in b for b in E.check(late, 106.0, LEN)))
        clash = {**JOB, "voice": [{"file": "m01.mp3", "at": 30.0}, {"file": "m02.mp3", "at": 32.0}]}
        self.assertTrue(any("раньше, чем кончился" in b for b in E.check(clash, 106.0, LEN)))
        self.assertTrue(any("нет файла" in b for b in E.check(JOB, 106.0, {})))
        nosong = {k: v for k, v in JOB.items() if k != "song_from"}
        self.assertTrue(any("song_from" in b for b in E.check(nosong, 106.0, LEN)))

    def test_titles_rules(self):
        over = {**JOB, "titles": [{"lines": ["A"], "at": 30.0 + i} for i in range(6)]}
        self.assertTrue(any("не больше 5" in b for b in E.check(over, 106.0, LEN)))
        on_words = {**JOB, "titles": [{"lines": ["A"], "at": 10.0}]}                # поверх слов артиста — нельзя
        self.assertTrue(any("слов артиста" in b for b in E.check(on_words, 106.0, LEN)))
        self.assertTrue(any("концовка" in b for b in E.check({**JOB, "outro": "green"}, 106.0, LEN)))

    def test_duck(self):
        self.assertEqual(E.duck_expr([]), "1")
        e = E.duck_expr([(28.1, 32.1)])

        def vol(t):
            clip = lambda x, a, b: max(a, min(b, x))  # noqa: E731
            return eval(e, {"t": t, "clip": clip, "min": min})
        self.assertAlmostEqual(vol(20.0), 1.0)                                       # до диктора — музыка как есть
        self.assertAlmostEqual(vol(30.0), 10 ** (-5 / 20), places=3)                 # под диктором −5 дБ
        self.assertTrue(10 ** (-5 / 20) < vol(27.85) < 1.0)                          # плавный спуск 0,5 с
        self.assertAlmostEqual(vol(33.0), 1.0)                                       # после — назад

    def test_audio_filter(self):
        fc, n = E.audio_filter(JOB, LEN, 106.0, True)
        self.assertEqual(n, 2)
        self.assertIn("adelay=1500", fc)                                             # интро 1,5 с — без звука
        self.assertIn(f"adelay={int((1.5 + 26.6) * 1000)}", fc)                      # голос — по секунде исходника + интро
        self.assertIn("loudnorm=I=-13", fc)
        self.assertEqual(fc.count("loudnorm"), 2)                                    # loudnorm только на голосе, не на музыке
        self.assertIn("concat=n=2:v=0:a=1[a]", fc)                                   # звук концовки OZOD JAMOL — всегда


if __name__ == "__main__":
    unittest.main()
