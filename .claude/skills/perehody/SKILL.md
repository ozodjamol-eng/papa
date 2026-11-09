---
name: perehody
description: Библиотека переходов и эффектов PAPA для репортажей и роликов из живых кадров — строб-очередь, белый силуэт, ч/б удар, зум-блюр «влёт», светящийся титр над предметом, рваная бумага, слова по одному, whip, speed-ramp, кольцо логотипа. Использовать при любом монтаже живых кадров (открытия, репортажи, анонсы), когда владелец просит «переходы», «фишки как в рефе», «как PUMA/Starbucks/Amazon».
---

# Переходы PAPA (собрано 09.11.2026 по 4 рефам владельца)
Код: `modules/fabrika/motion/perehody/perehody.py` (+ демо `demo_per.py` на кадрах LOVE GO). Движок кадров — `modules/fabrika/orders/lovego/otkrytie/eng.py`.

| Приём | Функция | Реф | Когда |
|---|---|---|---|
| Слова по одному крупно | `word_card` | TEN x YOU | крючок в начале, речь ведущего |
| Зум-блюр «влёт» A→B | `zoom_through`, `zoom_blur` | Amazon | вход в магазин, финал в логотип, «сердце» руками |
| Строб-очередь 2 кадра | `strobe_pick` (+ `bw_hit` каждый 3-й) | PUMA | пик музыки, открытие дверей |
| Ч/б удар | `bw_hit` | PUMA | акцент на бит |
| Белый силуэт | `person_mask` (rembg u2net_human_seg, 1 раз на кадр) + `white_silhouette` | PUMA | хозяева, ведущий, ключевой человек |
| Светящийся титр над предметом | `glow_title` (тёмный ореол — читаемость) | Starbucks | акция над товаром |
| Рваная бумага | `paper_strip` + вырезанный человек `sticker` + плашка имени | Starbucks | представить людей (хозяева по именам) |
| Whip + speed-ramp | `eng.whip`, `src()` из lv_minut | все | смена сцен |
| Кольцо | начало и конец одним кадром (вывеска/логотип) | Amazon | структура ролика |

Правила: люди без цветофильтров (ч/б удар и силуэт — короткие акценты 0,2–0,4 с, не грейд). Слово не шире 960 px. Структура репортажа — FISHKI 09.11 (Amazon: детали → приход → пик → общее фото → финал).
Съёмка под приёмы: телефон 0.5×, снизу; вещь/пакет в объектив; каждый человек отдельно на чистом фоне (для коллажа); «сердце» руками в объектив; вывеска в начале и конце.

## v2 (09.11): разведка → gl-transitions + бит
- `glt.py` — запуск **gl-transitions** (MIT, 213 переходов, github.com/gl-transitions/gl-transitions) через moderngl EGL без экрана (~0.1–0.7 с/кадр). Клон: `git clone --depth 1 https://github.com/gl-transitions/gl-transitions /home/claude/ext/gl-transitions` (skill-check пройден). Лучшие для репортажа: WhipPan, WhipSpin, WhipTilt, CrossZoom, TangentMotionBlur, LightStreaks, Overexposure, FlashFade, GlitchFlicker, CameraShake. ZoomInOut — криво (не брать).
- Бит: `librosa.beat.beat_track` (идея из ZiadAbdelkarim/beat-synced-edit, MIT, skill-check пройден) — склейка на каждые 2 бита, строб — 1 бит, переход 0,22 с центром на бите, жёсткая склейка + микро-вспышка 0,05 с.
- `beat_edit.py` — образец (проба №2 LOVE GO).
