---
name: earth-zoom
description: «EARTH ZOOM» — один непрерывный полёт камеры из космоса прямо к объекту (Кааба, магазин, офис клиента), вертикаль 9:16, Nano Banana Pro + Omni 1.1 Flash в Google Flow (по образцу @aiwithchad). Использовать, когда владелец просит «зум из космоса», «полёт с Земли к …», «как в ролике с Samsung/Ferrari», заставку-полёт для клиента (Умра/VOLIDAM и др.).
---

# EARTH ZOOM — из космоса к объекту одной камерой (9:16)

Образец: ролик @aiwithchad «EARTH ZOOM — Flagship brand reveals» + его PDF-гайд (присланы владельцем 04.11.2026).
Метод автора 1:1, меняется только МЕСТО, и формат у нас вертикальный. Ничего «от себя».
Рабочая версия: Макка v3, 04.11.2026 (владелец: «можешь же, когда захочешь»).

## Настройки — строго
| Что | Значение |
|---|---|
| Где | Google Flow, проект владельца, его Chrome |
| Формат | **9:16** везде — оба кадра и видео |
| Кадры | **Nano Banana Pro**, x1 — 0 бонусов |
| Видео | **Omni 1.1 Flash**, режим **«Кадры»** (первый + последний), 720p, **8 с**, **x1** — **12 бонусов** |
| Нельзя | Veo (не доводит камеру — финал «проявляется пузырём»), x2, 16:9 |

Перед тратой бонусов — сверка «образец → у нас» (модель, формат, кадры, свет, цена) и прямое «да» владельца.

## Три правила, без которых не работает (уроки 04.11)
1. **Последний кадр должен быть достижим с неба.** Вид чуть сверху, над объектом открытое небо, на пути камеры ничего нет (Кааба — с верхней галереи; магазин — с открытой улицы). Кадр «с уровня глаз внутри закрытого двора» → модель не может влететь и подставляет кадр наплывом.
2. **Один свет на весь полёт.** Земля и объект — в одном времени суток (золотой час). День → вечер = наплыв в конце.
3. **Реальные святыни и фасады — только по настоящему фото-образцу**, прикреплённому к Nano Banana («keep … exactly as in the reference»). Каабу без фото ИИ не рисуем.

## Шаг 1. Первый кадр — Земля (Nano Banana Pro, 9:16)
```
Ultra-photorealistic cinematic view of planet Earth from outer space, seen from a dramatic orbital perspective above <РЕГИОН> with <СТРАНА/ГОРОД> positioned near the center of the frame. A warm late-afternoon golden sun glows at Earth's curved horizon at the top of the frame with realistic atmospheric glow, the whole planet lit by warm golden daylight, detailed cloud systems, visible <БЕРЕГА/МОРЯ>, deep black space filled with natural stars, realistic sunlight scattering, enormous sense of scale, premium IMAX space-documentary photography, NASA-inspired realism, highly detailed textures, natural color science, no text, no logos. Compose vertically for a 9:16 cinematic video with <МЕСТО> centered in the middle of the frame for a forward dive.
```

## Шаг 2. Последний кадр — объект (Nano Banana Pro, 9:16, с фото-образцом)
Загрузка фото во Flow без окна выбора файлов: положить фото в репо → в странице перехватить `HTMLInputElement.prototype.click`, подставить файл (fetch с raw.githubusercontent.com) через DataTransfer + `change` → нажать «Загрузить».
```
Using the attached photo as the exact reference for the real architecture and camera angle: ultra-photorealistic elevated view from high above <МЕСТО>, looking at <ОБЪЕКТ> <ДЕТАЛИ ОБЪЕКТА>, with <ФОН/ОРИЕНТИР> rising directly behind it. Open sky above, nothing between the camera and the <ОБЪЕКТ>, the camera floats in the air above <МЕСТО>. Warm late-afternoon golden-hour sunlight, soft haze, sharp architectural detail, symmetrical front-facing composition, natural perspective, keep <ОБЪЕКТ И ФОН> exactly as in the reference, no text, no logos. Compose vertically for a 9:16 cinematic video with the <ОБЪЕКТ> centered in the lower part of the frame and <ФОН> above it, so the camera can descend from the sky and finish directly in front of the <ОБЪЕКТ>.
```

## Шаг 3. Видео (Omni 1.1 Flash, «Кадры», 9:16, 8 с, x1)
Первый кадр = Земля, последний = объект. Промпт автора + наши обязательные строки (вертикаль, один свет, без наплывов, спуск с открытого неба):
```
Create one seamless ultra-photorealistic cinematic Earth-to-destination reveal, vertical 9:16. Begin exactly from the uploaded Earth opening frame in outer space above <РЕГИОН> with <СТРАНА> centered below. The camera suddenly accelerates forward toward planet Earth with strong forward momentum and blockbuster-scale speed, diving in from the <НАПРАВЛЕНИЕ> toward <ГОРОД> in one uninterrupted shot. Pass through realistic atmospheric haze and volumetric clouds with natural motion blur, subtle camera vibration, dynamic exposure changes and believable sunlight scattering. Continue the same forward camera move toward <ГОРОД>, rapidly transitioning from orbital scale to aerial scale and then down toward the <ОБЪЕКТ/МЕСТО> without cuts, teleportation, melting or obvious morphing. <ЛАНДШАФТ И ГОРОД С ОРИЕНТИРАМИ> should resolve naturally as the camera gets closer. The camera descends from the open sky over <МЕСТО> into the final view, then smoothly decelerates and settles in the air in front of the <ОБЪЕКТ> exactly as in the uploaded reference, with <ФОН> behind it. The same warm golden-hour late-afternoon sunlight for the whole flight, one time of day, consistent lighting from space to the <ОБЪЕКТ>. End on a clean, stable hero shot of the <ОБЪЕКТ>. Ultra-photorealistic, premium commercial realism, Hollywood VFX quality, realistic physics, seamless scale transition, cinematic motion blur, volumetric light, believable cloud movement, natural camera behavior, one uninterrupted continuous shot, absolutely no cuts, no cross-dissolve, no fade, no scene transitions, rigid realistic architecture, straight lines remain straight, no warped buildings, no melting, no surreal morphing, no extra logos.
```
Если что-то не так — строки из гайда автора: медленно → «Extremely rapid acceleration from orbit, strong forward momentum, dramatic scale compression»; не похоже → «Final architecture and signage must closely match the uploaded reference»; гнётся → «Rigid realistic architecture, straight lines remain straight, no bending, no melting».

## Шаг 4. Проверка до показа владельцу
- Открыть видео в редакторе Flow, нажать ▶ (без этого <video> нет), в странице собрать раскадровку 16 кадров через canvas (оверлей на весь экран → скриншот).
- Плотно (по 0,3 с) смотреть отрезок, где камера входит в объект: нет ли наплыва/подмены кадра, лишних зданий.
- Честно назвать владельцу минусы.

## Шаг 5. Доставка
Скачать из Flow в «Загрузки» владельца (его «да» на скачивание + доступ к папке) → device_stage_files → монтаж (концовка OZOD JAMOL) → outbox/deliver в Telegram оригиналом. base64 через javascript_tool блокируется — не путь.

## Готовая подстановка — Макка (v3 ✅)
РЕГИОН = the Middle East; СТРАНА = western Saudi Arabia (the Mecca region); БЕРЕГА = Red Sea and Arabian Peninsula coastlines; НАПРАВЛЕНИЕ = northeast; ГОРОД = Mecca; ЛАНДШАФТ = Desert, the mountains of the Hejaz and the Mecca city layout with the Makkah Clock Tower; ОБЪЕКТ = the Kaaba (black kiswa, golden band, thousands of pilgrims in white); МЕСТО = the courtyard of Masjid al-Haram / the mosque; ФОН = the Makkah Royal Clock Tower and Abraj Al Bait towers.
Фото-образец: `docs/brand/volidam/zastavka/kaaba_tower_elevated_day.jpg`.

## История
- 04.11 v1 ✗ Veo, вид строго сверху — финал «пузырём».
- 04.11 v2 ✗ Omni, 16:9, Кааба с уровня глаз вечером — наплыв «появляется другой кадр».
- 04.11 v3 ✅ Omni, 9:16, Кааба с верхней галереи, золотой час везде — одна камера до конца. Минус: ИИ дорисовал вторую «башню» на переднем плане (4,4–5,6 с).

## Режим «болванка» (Earth Studio → ИИ одевает), 04.11.2026
- Файл: `docs/brand/volidam/zastavka/earth_zoom_blockout.esp` (9:16, 180 кадров = 6 с, темп образца: 0–1 с Земля, 1–3 с пике, 3–5 с Харам сверху, 5–6 с наклон к Каабе).
- Импорт: в Earth Studio **Ctrl+I** (меню «Файл» глючит); файл подставляется перехватом `HTMLInputElement.prototype.click`, текст .esp — инлайном (CSP режет fetch).
- Высоты в .esp — над уровнем моря (Мекка ≈ 277 м): ниже ~450 м камера уходит под землю.
- 3D Мекки в Earth Studio грубое (Кааба — коробка, часовой башни нет) → болванка задаёт ТОЛЬКО движение и геометрию, облик даёт конечный кадр-фото.

## Темп как в оригинале («плавная посадка»), 04.11.2026 — бесплатно, после генерации
Замер образца (@aiwithchad, сцена 1): полёт ≈ 4,5 с, скорость ровная (провал только в облаках), в конце короткое торможение, потом стоп-кадр ≈ 1 с. Omni отдаёт 8 с: середина «вязнет», в конце рывок и резкий стоп.
1. `ffmpeg -i v.mp4 -an -vf "minterpolate=fps=120:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1" v_120.mp4`
2. `python3 tools/remap.py 5.0` (кладёт `remap_raw.mp4`: разгон 0,5 с → ровно → мягкое торможение 1,1 с → стоп 1 с; итог 6 с)
3. Сверка кривой: `python3 tools/curve.py remap.mp4 0,320,720,640 0 6` рядом с образцом. Потом 1080×1920 и концовка OZOD JAMOL.
