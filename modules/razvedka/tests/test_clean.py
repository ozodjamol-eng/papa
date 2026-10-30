"""31.10 самоочистка источников: мёртвые/закрытые/с лого — убрать и больше не подключать."""
import asyncio
import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from razvedka import clean  # noqa: E402

NOW = dt.datetime(2026, 10, 31, 10, tzinfo=dt.timezone.utc)
CHOICE = {"channels": {"davra": {"humor": [{"id": 1, "title": "Живой", "username": "alive"},
                                          {"id": 2, "title": "Мёртвый", "username": "dead"},
                                          {"id": 3, "title": "Лого", "username": "logo"}],
                                 "music": [{"id": 4, "title": "Без юзернейма"}, {"id": 5, "title": "Удалён", "username": "gone"}]}}}


class UsernameNotOccupiedError(Exception):
    pass


class Msg:
    def __init__(self, days):
        self.date = NOW - dt.timedelta(days=days)


class Client:
    async def get_entity(self, p):
        if p == "gone":
            raise UsernameNotOccupiedError()
        if not isinstance(p, str):
            raise ValueError("Could not find the input entity")
        return p

    async def get_messages(self, ent, limit=1):
        return [Msg(40 if ent == "dead" else 1)]


class Clean(unittest.TestCase):
    def test_check_and_remove(self):
        from unittest import mock
        async def nap(s):
            return None
        with mock.patch.object(clean.asyncio, "sleep", nap):
            bad = asyncio.run(clean.check(Client(), CHOICE, {"@logo"}, NOW, log=lambda s: None))
        self.assertEqual(set(bad), {2, 3, 5})                      # без @ и «не в кэше» — не трогаем
        data, lines = clean.remove(CHOICE, bad, NOW)
        self.assertEqual([x["id"] for x in data["channels"]["davra"]["humor"]], [1])
        self.assertEqual([x["id"] for x in data["channels"]["davra"]["music"]], [4])
        self.assertEqual(set(data["auto_seen"]["davra"]), {2, 3, 5})
        self.assertEqual(len(lines), 3)
        self.assertEqual(len(CHOICE["channels"]["davra"]["humor"]), 3)   # исходный не испорчен
