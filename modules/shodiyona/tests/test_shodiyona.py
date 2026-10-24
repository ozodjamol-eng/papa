import datetime as dt
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shodiyona import bot as B, texts as T  # noqa: E402

ADMIN, CLIENT = 1, 500
CFG = B.load_cfg()


class FakeApi:
    def __init__(self):
        self.calls, self.mid = [], 100

    def __call__(self, method, **p):
        self.calls.append((method, p))
        self.mid += 1
        return {"message_id": self.mid}

    def sent(self, chat=None, method="sendMessage"):
        return [p for m, p in self.calls if m == method and (chat is None or p.get("chat_id") == chat)]

    def last_text(self, chat):
        return self.sent(chat)[-1]["text"]


class Clock:
    def __init__(self):
        self.t = dt.datetime(2026, 10, 25, 10, 0, tzinfo=B.TZ)

    def __call__(self):
        return self.t


def msg(text="", uid=CLIENT, **kw):
    m = {"chat": {"id": uid, "type": "private"}, "from": {"id": uid, "first_name": "Алишер", "username": "alisher"}}
    if text:
        m["text"] = text
    m.update(kw)
    return {"message": m}


def cb(data, uid=CLIENT, message=None):
    return {"callback_query": {"id": "q", "from": {"id": uid, "first_name": "Менеджер"}, "data": data,
                               "message": message or {"chat": {"id": uid}, "message_id": 9}}}


PHOTO = [{"file_id": "small"}, {"file_id": "PHOTO1"}]


class Base(unittest.TestCase):
    def setUp(self):
        self.api, self.clock = FakeApi(), Clock()
        self.bot = B.Bot(self.api, B.connect(":memory:"), {ADMIN}, CFG, clock=self.clock)

    def tearDown(self):
        self.bot.db.close()

    def u(self, *updates):
        for x in updates:
            self.bot.handle(x)

    def lead(self, n=1):
        return self.bot.db.execute("SELECT * FROM leads WHERE n=?", (n,)).fetchone()


class TestStart(Base):
    def test_menu_has_all_eight_buttons_and_source(self):
        self.u(msg("/start instagram"))
        kb = self.api.sent(CLIENT)[-1]["reply_markup"]["keyboard"]
        flat = [b["text"] for row in kb for b in row]
        self.assertEqual(flat, [T.MENU_CATALOG, T.MENU_ORDER, T.MENU_CHEAPER, T.MENU_ROOM, T.MENU_MEASURE,
                                T.MENU_TRACK, T.MENU_PLACES, T.MENU_CONTACT])
        self.assertEqual(self.bot.user(CLIENT)["src"], "Instagram")
        self.assertIn("Алишер", self.api.last_text(CLIENT))

    def test_phone_normalize(self):
        self.assertEqual(B.norm_phone("90 123 45 67"), "+998901234567")
        self.assertEqual(B.norm_phone("+998 (90) 123-45-67"), "+998901234567")
        self.assertIsNone(B.norm_phone("123"))


class TestOrder(Base):
    def test_full_order_flow_lead_to_manager(self):
        self.u(msg("/start"), msg(T.MENU_ORDER), cb("o:wardrobe"),
               msg("Шкаф-купе 2,4 x 2,6 оқ"), msg(contact={"phone_number": "998901234567"}))
        r = self.lead()
        self.assertEqual((r["kind"], r["phone"], r["status"]), ("order", "+998901234567", "new"))
        self.assertIn("Шкафлар", r["details"])
        self.assertIn("Шкаф-купе", r["details"])
        card = self.api.sent(ADMIN)[-1]
        self.assertIn("Ариза №1", card["text"])
        self.assertIn("+998901234567", card["text"])
        self.assertIn("№1", self.api.last_text(CLIENT))
        self.assertIsNone(self.bot.user(CLIENT)["step"])

    def test_known_phone_one_tap_and_no_stale_data(self):
        self.u(msg(T.MENU_MEASURE), cb("m:d:2026-10-26"), cb("m:t:14:00"), msg("Хўжаобод, Бобур кўча 5"),
               msg("+998 90 111 22 33"))
        self.u(msg(T.MENU_CHEAPER), msg(photo=PHOTO, caption="OLX дан"), cb("p:yes"))
        r = self.lead(2)
        self.assertEqual((r["kind"], r["phone"]), ("cheaper", "+998901112233"))
        self.assertNotIn("Бобур", r["details"])                 # адрес замера не утёк в другую заявку
        self.assertEqual(json.loads(r["photos"]), ["PHOTO1"])
        self.assertTrue(self.api.sent(ADMIN, "sendPhoto"))      # фото пришло менеджеру

    def test_bad_phone_asks_again(self):
        self.u(msg(T.MENU_CHEAPER), msg(photo=PHOTO), msg("123"))
        self.assertIsNone(self.lead())
        self.assertIn("тўлиқ", self.api.last_text(CLIENT))


class TestMeasure(Base):
    def test_measure_with_location(self):
        self.u(msg(T.MENU_MEASURE))
        days = self.api.sent(CLIENT)[-1]["reply_markup"]["inline_keyboard"]
        self.assertEqual(sum(len(r) for r in days), 6)
        self.u(cb("m:d:2026-10-27"), cb("m:t:10:00"), msg(location={"latitude": 40.8, "longitude": 72.3}),
               msg("901234567"))
        r = self.lead()
        self.assertIn("10:00", r["details"])
        self.assertIn("maps.google.com/?q=40.8,72.3", r["details"])
        self.assertIn("Сешанба", self.api.last_text(CLIENT))


class TestRoom(Base):
    def test_room_without_ai_goes_to_manager(self):
        self.u(msg(T.MENU_ROOM), msg(photo=PHOTO), cb("r:living"), msg("+998901234567"))
        r = self.lead()
        self.assertEqual(r["kind"], "room")
        self.assertIn("тез кунда", self.api.last_text(CLIENT))

    def test_room_needs_photo(self):
        self.u(msg(T.MENU_ROOM), msg("салом"))
        self.assertIn("расмини", self.api.last_text(CLIENT))


class TestReminder(Base):
    def test_remind_once_after_15_min_daytime_only(self):
        self.u(msg(T.MENU_CHEAPER), msg(photo=PHOTO), msg("+998901234567"))
        self.assertEqual(self.bot.remind(), 0)
        self.clock.t += dt.timedelta(minutes=16)
        self.assertEqual(self.bot.remind(), 1)
        self.assertIn("16 дақиқадан", self.api.last_text(ADMIN))
        self.assertEqual(self.bot.remind(), 0)                    # без повторов

    def test_night_lead_reminded_in_morning(self):
        self.clock.t = dt.datetime(2026, 10, 25, 23, 0, tzinfo=B.TZ)
        self.u(msg(T.MENU_CHEAPER), msg(photo=PHOTO), msg("+998901234567"))
        self.clock.t += dt.timedelta(hours=1)
        self.assertEqual(self.bot.remind(), 0)                    # ночью не будим
        self.clock.t = dt.datetime(2026, 10, 26, 8, 1, tzinfo=B.TZ)
        self.assertEqual(self.bot.remind(), 1)

    def test_called_lead_not_reminded(self):
        self.u(msg(T.MENU_CHEAPER), msg(photo=PHOTO), msg("+998901234567"), cb("l:called:1", uid=ADMIN))
        self.clock.t += dt.timedelta(minutes=30)
        self.assertEqual(self.bot.remind(), 0)
        self.assertEqual(self.lead()["status"], "called")


class TestOrders(Base):
    def test_won_creates_order_stages_and_photo_reach_client(self):
        self.u(msg(T.MENU_ORDER), cb("o:kitchen"), msg("Ошхона 3 м"), msg("+998901234567"),
               cb("l:called:1", uid=ADMIN), cb("l:won:1", uid=ADMIN))
        self.assertEqual(self.lead()["status"], "won")
        self.assertIn("рўйхатга олинди", self.api.sent(CLIENT)[-1]["text"])
        self.u(cb("s:1:1", uid=ADMIN, message={"chat": {"id": ADMIN}, "message_id": 5}))
        self.assertIn("Ишлаб чиқарилмоқда", self.api.last_text(CLIENT))
        self.u(cb("s:1:1", uid=ADMIN))                           # повторное нажатие — ничего
        self.assertEqual(len([t for t in self.api.sent(CLIENT) if "Ишлаб" in t["text"]]), 1)
        self.u(cb("s:1:ph", uid=ADMIN), msg(photo=PHOTO, uid=ADMIN))
        ph = self.api.sent(CLIENT, "sendPhoto")[-1]
        self.assertEqual(ph["photo"], "PHOTO1")
        self.assertIn("цехдан", ph["caption"])
        self.u(msg(T.MENU_TRACK))
        self.assertIn("Ишлаб чиқарилмоқда", self.api.last_text(CLIENT))
        self.u(cb("l:lost:1", uid=ADMIN))                         # закрытую заявку не переоткрыть
        self.assertEqual(self.lead()["status"], "won")

    def test_client_cannot_press_admin_buttons(self):
        self.u(msg(T.MENU_CHEAPER), msg(photo=PHOTO), msg("+998901234567"), cb("l:won:1"))
        self.assertEqual(self.lead()["status"], "new")

    def test_track_empty(self):
        self.u(msg(T.MENU_TRACK))
        self.assertIn("фаол буюртма йўқ", self.api.last_text(CLIENT))


class TestCatalog(Base):
    def test_empty_catalog_offers_order(self):
        self.u(msg(T.MENU_CATALOG))
        self.assertIn("тез кунда", self.api.last_text(CLIENT))

    def test_admin_adds_product_client_views_and_orders(self):
        self.u(msg("/admin", uid=ADMIN), cb("a:add", uid=ADMIN), cb("a:cat:bed", uid=ADMIN),
               msg(photo=PHOTO, uid=ADMIN), msg("Ётоқхона «Венеция»\n2,0 × 1,6 м\nМДФ, оқ\n6 500 000 сўмдан", uid=ADMIN))
        self.assertIn("№1", self.api.last_text(ADMIN))
        self.u(msg(T.MENU_CATALOG))
        kb = self.api.sent(CLIENT)[-1]["reply_markup"]["inline_keyboard"]
        self.assertEqual(kb[0][0]["text"], "🛏 Ётоқхона (1)")
        self.u(cb("c:bed"))
        card = self.api.sent(CLIENT, "sendPhoto")[-1]
        self.assertIn("Венеция", card["caption"])
        self.assertIn("6 500 000", card["caption"])
        self.u(cb("b:1"), msg("+998901234567"))
        r = self.lead()
        self.assertEqual(r["kind"], "product")
        self.assertIn("Венеция", r["details"])

    def test_hide_product_admin_only(self):
        self.bot.db.execute("INSERT INTO products (cat,title,info,photo,created) VALUES ('bed','A','','X','t')")
        self.u(cb("h:1"))
        self.assertEqual(self.bot.counts(), {"bed": 1})
        self.u(cb("h:1", uid=ADMIN))
        self.assertEqual(self.bot.counts(), {})


class TestPlaces(Base):
    def test_two_venues_and_contact(self):
        self.u(msg(T.MENU_PLACES))
        self.assertEqual(len(self.api.sent(CLIENT, "sendVenue")), 2)
        self.u(msg(T.MENU_CONTACT))
        self.assertIn("+998 70 167 37 77", self.api.last_text(CLIENT))


if __name__ == "__main__":
    unittest.main()
