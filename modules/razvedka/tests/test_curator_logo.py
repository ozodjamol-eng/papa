"""20.10: Куратор проверяет настоящие кадры видео (сетка 2×2), источник с чужим лого — в стоп-лист."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from razvedka import curate  # noqa: E402


class T(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ffmpeg"), "нет ffmpeg")
    def test_frames_grid(self):
        d = Path(tempfile.mkdtemp())
        v = d / "v.mp4"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=320x240:d=4", str(v)], check=True)
        g = curate.frames_grid(v.read_bytes(), 4.0)
        self.assertIsNotNone(g)
        self.assertTrue(g[:2] == b"\xff\xd8")                # JPEG

    def test_known_logo_source(self):
        self.assertIn("@shohonakulgu", curate.LOGO_SOURCES)


if __name__ == "__main__":
    unittest.main()
