import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from genplan import marker  # noqa: E402

CH = {"username": "kattadavrauz", "title": "КАТТА ДАВРА"}


def row(**kw):
    base = {"has_media": 1, "rubric": "Ҳажвия", "source": "РАЗВЛЕКАТЕЛЬНО",
            "media": json.dumps([{"type": "video", "file_id": "x"}])}
    base.update(kw)
    return base


class MarkerTest(unittest.TestCase):
    def test_marks_single_video(self):
        assert marker.decide(CH, row())[0] == "video"


    def test_marks_photo(self):
        assert marker.decide(CH, row(media=json.dumps([{"type": "photo", "file_id": "x"}])))[0] == "photo"


    def test_never_ads_and_muftiy(self):
        assert marker.decide(CH, row(rubric="Реклама"))[0] is None
        assert marker.decide(CH, row(rubric="Муфтий минбари"))[0] is None


    def test_not_twice_and_not_text_and_not_album(self):
        assert marker.decide(CH, row(source="fabrika"))[0] is None
        assert marker.decide(CH, row(has_media=0))[0] is None
        two = json.dumps([{"type": "photo", "file_id": "a"}, {"type": "photo", "file_id": "b"}])
        assert marker.decide(CH, row(media=two))[0] is None


    def test_mark_text(self):
        assert marker.mark_text(CH) == "@kattadavrauz"
        assert marker.mark_text({**CH, "watermark": "@KATTADAVRAUZ"}) == "@KATTADAVRAUZ"
