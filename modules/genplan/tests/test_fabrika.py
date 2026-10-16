import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import ai, fabrika, hub, media, store  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
CFG["auto_place"] = False          # эти тесты проверяют ручной выбор рубрики
CFG["auto_channels"] = ["davra"]   # и канал по умолчанию
ENV = {"OWNER_IDS": "42", "HUB_CHAT_ID": "-100777", "GENPLAN_BOT_TOKEN": "t"}


class Bot:
    def __init__(self):
        self.calls = []

    def __call__(self, method, **p):
        self.calls.append((method, p))
        return {"message_id": 500 + len(self.calls)}


class TestLinks(unittest.TestCase):
    def test_find_link(self):
        self.assertEqual(fabrika.find_link("зўр видео https://www.instagram.com/reel/ABC123/?igsh=x"),
                         "https://www.instagram.com/reel/ABC123/?igsh=x")
        self.assertTrue(fabrika.find_link("https://vt.tiktok.com/ZS123/"))
        self.assertTrue(fabrika.find_link("https://youtube.com/shorts/xyz"))
        self.assertIsNone(fabrika.find_link("https://t.me/kattadavrauz"))
        self.assertIsNone(fabrika.find_link("оддий матн"))

    def test_link_message_creates_job(self):
        db, bot = store.connect(":memory:"), Bot()
        u = {"message": {"message_id": 7, "from": {"id": 42}, "chat": {"id": 42, "type": "private"},
                         "text": "https://www.instagram.com/reel/ABC/"}}
        self.assertEqual(hub.handle(bot, db, CFG, ENV, u), "link")
        j = store.job_take(db)
        self.assertEqual((j["kind"], json.loads(j["payload"])["url"]), ("link", "https://www.instagram.com/reel/ABC/"))


class TestEditText(unittest.TestCase):
    def test_edit_flow(self):
        db, bot = store.connect(":memory:"), Bot()
        dm = lambda mid, **k: {"message": {"message_id": mid, "from": {"id": 42}, "chat": {"id": 42, "type": "private"}, **k}}
        hub.handle(bot, db, CFG, ENV, dm(1, photo=[{"file_id": "f", "file_unique_id": "u"}], caption="Эски матн"))
        hub.callback(bot, db, CFG, {42}, {"id": "q", "from": {"id": 42}, "data": "ed:1", "message": {"chat": {"id": 42}, "message_id": 9}})
        self.assertEqual(hub.handle(bot, db, CFG, ENV, dm(2, text="Янги чиройли матн")), "edited")
        self.assertEqual(store.get(db, 1)["text"], "Янги чиройли матн")
        self.assertEqual(hub.handle(bot, db, CFG, ENV, dm(3, text="Бу энди янги пост")), "material")   # ожидание снято


class TestGemini(unittest.TestCase):
    def setUp(self):
        os.environ["GEMINI_API_KEY"] = "g"

    def tearDown(self):
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("ANTHROPIC_API_KEY", None)

    def test_gemini_and_fallback(self):
        db = store.connect(":memory:")
        g = lambda req: {"candidates": [{"content": {"parts": [{"text": "🌧 Ёмғирли жаннат"}]}}]}
        self.assertEqual(ai.rewrite(db, "Rainy paradise", "КАТТА ДАВРА", http=g), "🌧 Ёмғирли жаннат")
        import urllib.error
        def limited(req):
            if "googleapis" in req.full_url:
                raise urllib.error.HTTPError(req.full_url, 429, "limit", {}, None)
            return {"content": [{"type": "text", "text": "Claude матни"}]}
        with self.assertRaises(ai.AIError) as e:
            ai.rewrite(db, "x text", "КАТТА ДАВРА", http=limited)
        self.assertIn("лимит", str(e.exception))                                  # без Claude — понятная ошибка
        os.environ["ANTHROPIC_API_KEY"] = "a"
        self.assertEqual(ai.rewrite(db, "x text", "КАТТА ДАВРА", http=limited), "Claude матни")   # запасной


class TestAI(unittest.TestCase):
    def setUp(self):
        os.environ["ANTHROPIC_API_KEY"] = "test"

    def tearDown(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)

    def test_rewrite_and_reject(self):
        db = store.connect(":memory:")
        ok = lambda req: {"content": [{"type": "text", "text": "🎵 Янги клип\n\nМатн."}]}
        self.assertEqual(ai.rewrite(db, "Yangi klip @kanal", "КАТТА ДАВРА", http=ok), "🎵 Янги клип\n\nМатн.")
        with self.assertRaises(ai.AIError):
            ai.rewrite(db, "ёмон матн", "КАТТА ДАВРА", http=lambda r: {"content": [{"type": "text", "text": "РАД"}]})
        with self.assertRaises(ai.AIError):
            ai.rewrite(db, "", "КАТТА ДАВРА", http=ok)


@unittest.skipUnless(shutil.which("ffmpeg"), "нет ffmpeg")
class TestMediaAndPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        from PIL import Image, ImageDraw
        im = Image.new("RGB", (300, 300), "white")
        ImageDraw.Draw(im).ellipse((5, 5, 295, 295), fill=(200, 20, 30))
        im.save(self.tmp / "logo.jpg")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=360x640:rate=25:duration=3",
                        "-c:v", "libx264", str(self.tmp / "in.mp4")], check=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_text_watermark_rise(self):
        lg = media.text_logo("@kattadavrauz", self.tmp / "wm.png")
        out = media.watermark_video(self.tmp / "in.mp4", lg, self.tmp / "o.mp4")
        self.assertAlmostEqual(media.probe(out)["dur"], 3, delta=0.3)

    def test_logo_circle_and_watermark(self):
        lg = media.prepare_logo(self.tmp / "logo.jpg", self.tmp / "logo.png")
        from PIL import Image
        self.assertEqual(Image.open(lg).getpixel((0, 0))[3], 0)                 # угол прозрачный — круг вырезан
        out = media.watermark_video(self.tmp / "in.mp4", lg, self.tmp / "out.mp4", style="classic")
        self.assertAlmostEqual(media.probe(out)["dur"], 3, delta=0.3)

    def test_pipeline_with_fake_download(self):
        db, bot = store.connect(":memory:"), Bot()
        orig_dl, orig_up, orig_logo = fabrika.download, fabrika.upload_video, fabrika.logo_path
        fabrika.download = lambda url, work: (work.mkdir(parents=True, exist_ok=True) or shutil.copy(self.tmp / "in.mp4", work / "src.mp4")
                                              and (work / "src.mp4", "Yangi klip chiqdi! @boshqa_kanal"))
        fabrika.upload_video = lambda token, chat, path, caption: {"message_id": 77, "video": {"file_id": "V", "file_unique_id": "VU"}}
        fabrika.logo_path = lambda ch, root=None: self.tmp / f"logo-{ch}.png"
        try:
            self.assertEqual(fabrika.process_link(bot, db, CFG, ENV, {"url": "u", "owner_chat": 42}, work_root=self.tmp / "w"), "ok")
        finally:
            fabrika.download, fabrika.upload_video, fabrika.logo_path = orig_dl, orig_up, orig_logo
        m = store.get(db, 1)
        self.assertEqual((m["hub_msg"], m["channel"], m["status"]), (77, "davra", "draft"))
        self.assertEqual(bot.calls[0][0], "copyMessage")                         # владелец видит готовое видео
        self.assertIn("Мусиқа", bot.calls[1][1]["text"])                          # карточка: рубрика угадана по тексту
        self.assertFalse((self.tmp / "w").exists() and any((self.tmp / "w").iterdir()))   # рабочие файлы убраны


if __name__ == "__main__":
    unittest.main()
