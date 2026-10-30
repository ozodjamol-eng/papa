"""30.10: куратор выполняет заказ штаба; якорь — склад под скоро пустой час."""
import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from razvedka import curate, sklad  # noqa: E402

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 30, 7, 0, tzinfo=UTC)          # 12:00 Ташкент
NEEDS = {"channels": {"xojaobod": {"empty": [
    {"h": "13", "at": (NOW + dt.timedelta(hours=1)).isoformat(), "codes": ["useful"], "stash": ["ФОЙДАЛИК"]},
    {"h": "17", "at": (NOW + dt.timedelta(hours=5)).isoformat(), "codes": ["warn"], "stash": []},
    {"h": "21", "at": (NOW + dt.timedelta(hours=9)).isoformat(), "codes": ["humor"], "stash": ["РАЗВЛЕКАТЕЛЬНО"]}]}}}


class T(unittest.TestCase):
    def test_need_codes_near_first(self):
        self.assertEqual(curate.need_codes(NEEDS, "xojaobod", NOW), ["useful", "warn"])   # 21:00 — дальше 6 ч
        self.assertEqual(curate.need_codes({}, "xojaobod", NOW), [])

    def test_pick_prefers_needed(self):
        c = lambda k, rub, sc: {"key": k, "rub": rub, "score": sc, "text": f"матн {k} алоҳида сўзлар {k}x {k}y {k}z"}
        cands = [c("a", "humor", 9), c("b", "warn", 1), c("d", "useful", 2)]
        got = [x["key"] for x in curate.pick(cands, 2, [], ["warn", "useful"])]
        self.assertEqual(got, ["b", "d"])

    def test_anchor_plan(self):
        self.assertEqual(sklad.anchor_plan(NEEDS, NOW), {"xojaobod": ["ФОЙДАЛИК"]})   # 13:00 — скоро, есть склад
