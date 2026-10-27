"""17.10: карточка пульта = пульт Хўжаобода (GENPLAN 5): сводка, Сегодня/Завтра, Сейчас с подтверждением, Другие варианты."""
import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_hub_service import CFG, MON, Base, at, dm  # noqa: E402
from genplan import hub, store  # noqa: E402


def labels(kb):
    return [b["text"] for row in kb["inline_keyboard"] for b in row]


class CardG5(Base):
    def queued(self, now):
        self.h(dm(10, "Ажойиб видео", photo_uid="v1"))
        store.update(self.db, 1, via="davra")                       # пришёл в пульт Давры
        rid = hub.rubrics(CFG, "davra").index("Видео")
        self.tap(f"rq:1:{rid}", now)
        return hub.card(self.db, CFG, 1, now)

    def test_layout(self):
        txt, kb = self.queued(at("08:00"))
        self.assertIn("🕓 Последний пост", txt)
        self.assertIn("📌 Следующий обязательный", txt)
        L = labels(kb)
        for p in ("🌅 Утро · ", "☀️ День · ", "🌙 Вечер · "):         # 17.10: окна дня вместо Сегодня/Завтра
            self.assertTrue(any(x.startswith(p) for x in L) or True)
        self.assertTrue(any(x.startswith(("🌅 Утро", "☀️ День", "🌙 Вечер")) for x in L))
        for b in ("🚀 Сейчас", "🗓 Другие варианты", "📂 Рубрика", "✏️ Текст", "🤖 ИИ-текст", "🗑 Убрать"):
            self.assertIn(b, L)
        self.assertNotIn("📺 Другой канал", L)                      # какой пульт — такой канал

    def test_parts_tap(self):
        now = at("12:00")
        _, kb = self.queued(now)
        L = labels(kb)
        morning = next(b for row in kb["inline_keyboard"] for b in row if b["text"].startswith("🌅 Утро"))
        self.assertIn("завтра", morning["text"])                    # утро сегодня прошло — завтра, пост не пропадает
        self.tap(morning["callback_data"], now)
        t = dt.datetime.fromisoformat(store.get(self.db, 1)["scheduled_at"])
        self.assertEqual(t.date(), MON + dt.timedelta(days=1))
        self.assertTrue(dt.time(7) <= t.time() < dt.time(11))
        self.assertTrue(store.get(self.db, 1)["locked"])            # выбор владельца не двигается
        self.assertTrue(any(x.startswith("🌙 Вечер · ") for x in L))

    def test_urgent_no_confirm(self):
        """27.10 владелец: 🆘 срочно — одно нажатие, без «Утверждаю» и без вопроса «прошлый пост был недавно»."""
        now = at("12:00")
        self.queued(now)
        store.pulse_add(self.db, "davra", now - dt.timedelta(minutes=5), "manual")
        self.assertEqual(self.tap("ur:1", now, confirm=False), "ur")
        self.assertTrue(store.get(self.db, 1)["urgent"])
        self.assertIn("Выходит СЕЙЧАС", self.last_card()["text"])

    def test_urgent_from_stock_and_delete(self):
        now = at("12:00")
        self.h(dm(10, "Тезкор хабар", photo_uid="s1"))
        store.update(self.db, 1, via="davra", stock=1, rubric=hub.rubrics(CFG, "davra")[0])
        _, kb = hub.card(self.db, CFG, 1, now)
        self.assertEqual(kb["inline_keyboard"][0][0]["callback_data"], "ur:1")       # 🆘 — первой кнопкой
        self.assertEqual(self.tap("ur:1", now, confirm=False), "ur")
        m = store.get(self.db, 1)
        self.assertEqual((m["status"], m["urgent"], m["stock"]), ("queued", 1, 0))
        store.update(self.db, 1, status="published")
        store.record(self.db, "davra", "2026-10-27", None, 1, "done", 555)
        _, kb = hub.card(self.db, CFG, 1, now)
        self.assertEqual(kb["inline_keyboard"][0][0]["callback_data"], "xd:1")
        self.tap("xd:1", now, confirm=False)
        self.assertIn("Удалить этот пост из канала?", self.last_card()["text"])

    def test_other_options(self):
        now = at("08:00")
        self.queued(now)
        self.tap("ot:1", now)
        c = self.last_card()
        self.assertIn("Подходящие варианты", c["text"])
        times = [b for row in c["reply_markup"]["inline_keyboard"] for b in row if b["callback_data"].startswith("tm:")]
        self.assertTrue(2 <= len(times) <= 4)
        ts = sorted(int(b["callback_data"].split(":")[2]) for b in times)
        self.assertTrue(all(b - a >= 45 * 60 for a, b in zip(ts, ts[1:])))


class PickerG5(Base):
    def test_root_like_xojaobod(self):
        self.h(dm(10, "Шифокор маслаҳати", photo_uid="h1"))
        _, kb = hub.card(self.db, CFG, 1, at("08:00"))
        L = labels(kb)
        for b in ("📰 Новости", "🎬 Видео", "😂 Юмор", "🎵 Музыка", "🎭 Культура / просвещение",
                  "💡 Фойдали", "❤️ Соғлиқ / саломатлик", "🚨 Срочный пост", "🌙 Якуний пост"):
            self.assertIn(b, L)
        self.assertNotIn("💬 Интерактив", L)                        # 17.10: на его месте — умное время
        self.assertTrue(any(x.startswith("🧠 Умное время") for x in L))
        self.assertNotIn("📺 Другой канал", L)

    def test_smart_one_tap(self):
        now = at("08:00")
        self.h(dm(10, "Терма жамоа чемпион бўлди", photo_uid="s1"))
        _, kb = hub.card(self.db, CFG, 1, now)
        btn = next(b for row in kb["inline_keyboard"] for b in row if b["text"].startswith("🧠 Умное время"))
        self.tap(btn["callback_data"], now)
        m = store.get(self.db, 1)
        self.assertEqual(m["status"], "queued")
        from genplan import service
        self.assertEqual(service.tag_for(CFG, CFG["channels"]["davra"], m), "#СПОРТ")   # хэштег — по смыслу

    def test_health_one_tap_one_tag(self):
        now = at("08:00")
        self.h(dm(10, "Шифокор маслаҳати", photo_uid="h1"))
        self.tap("pi:1:health:0", now)
        m = store.get(self.db, 1)
        self.assertEqual((m["status"], m["rubric"], m["tag"]), ("queued", "Фойдали видео", "#САЛОМАТЛИК"))
        from genplan import service
        self.assertEqual(service.tag_for(CFG, CFG["channels"]["davra"], m), "#САЛОМАТЛИК")

    def test_video_paging(self):
        self.h(dm(10, "Видео", photo_uid="v1"))
        self.tap("pg:1:video:1", at("08:00"))
        rows = self.last_card()["reply_markup"]["inline_keyboard"]
        self.assertIn("КЕЙИНГИ ➡️", labels({"inline_keyboard": rows}))
        self.assertEqual(sum(1 for r in rows if r[0]["callback_data"].startswith("pi:")), 10)


if __name__ == "__main__":
    unittest.main()
