import asyncio
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from razvedka import retro, retrouz


def msg(i, text, video=True):
    return types.SimpleNamespace(id=i, message=text, video=object() if video else None, media=object(), grouped_id=None, action=None)


class TestRetroUz(unittest.TestCase):
    def test_parse_and_todo(self):
        self.assertEqual(retrouz.parse({"yes": [1, "3", 9, "x"]}, 3), {1, 3})
        items = [{"id": 3, "msgs": [msg(3, "a")], "text": "a"}, {"id": 1, "msgs": [msg(1, "b")], "text": "b"},
                 {"id": 2, "msgs": [msg(2, "", True)], "text": ""}, {"id": 4, "msgs": [msg(4, "c", False)], "text": "c"}]
        self.assertEqual([x["id"] for x in retrouz.todo(items, {3})], [1])

    def test_copies_only_yes_and_never_deletes(self):
        items = [{"id": i, "msgs": [msg(i, t)], "text": t} for i, t in ((1, "ШЕРАЛИ ЖЎРАЕВ — Карвон"), (2, "Янги клип 2026"))]
        client = mock.Mock()
        put = mock.AsyncMock(return_value=True)
        with tempfile.TemporaryDirectory() as d, mock.patch.object(retrouz.hubs, "entity", mock.AsyncMock(side_effect=lambda c, name, cache: "DST" if name == retrouz.DST else "SRC")), \
                mock.patch.object(retrouz.tozalash, "scan", mock.AsyncMock(return_value=items)), \
                mock.patch.object(retrouz.hubs, "put", put), mock.patch.object(retrouz.asyncio, "sleep", mock.AsyncMock()):
            r = asyncio.run(retrouz.run(client, Path(d), log=lambda s: None, ask=lambda p: {"yes": [1]}))
            self.assertEqual((r["просмотрено"], r["в узбекский банк"]), (2, 1))
            self.assertEqual(put.await_args.args[1], "DST")
            self.assertFalse(put.await_args.kwargs["check"])
            client.delete_messages.assert_not_called()
            r2 = asyncio.run(retrouz.run(client, Path(d), log=lambda s: None, ask=lambda p: {"yes": [1]}))   # второй проход — уже смотрели
        self.assertEqual(r2["просмотрено"], 0)

    def test_scout_has_two_banks(self):
        self.assertEqual(set(retro.GROUPS), {"РЕТРО КЛИПЛАР", "ЎЗБЕК РЕТРО"})
        low = [{"id": "u", "title": "Ялла", "viewCount": 300_000, "duration": "3:30"}]
        self.assertEqual(retro.pick(low, set()), [])
        self.assertEqual(len(retro.pick(low, set(), min_views=100_000)), 1)


if __name__ == "__main__":
    unittest.main()
