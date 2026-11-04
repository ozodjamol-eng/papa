---
name: earth-zoom
description: «EARTH ZOOM» — один непрерывный полёт камеры из космоса прямо к фасаду/святыне (по образцу @aiwithchad, Nano Banana Pro + Omni 1.1 Flash в Google Flow, 16:9). Использовать, когда владелец просит «зум из космоса», «как в ролике с Samsung/Ferrari», «Земля → витрина», заставку-полёт для клиента (Умра/VOLIDAM, магазин, офис).
---

# EARTH ZOOM — из космоса к объекту одной камерой

Образец: ролик @aiwithchad «EARTH ZOOM — Flagship brand reveals» + его PDF-гайд (присланы 04.11.2026).
Работа = повторить образец 1:1, меняется ТОЛЬКО место. Ничего «от себя» (урок 04.11: подмена модели и своя камера сожгли ~40 бонусов).

## Настройки (строго)
- Всё в Google Flow, проект владельца, Chrome владельца.
- **Формат — 9:16** (ролики для Reels/Telegram). В гайде автора 16:9 — у нас вертикаль: и кадры, и видео 9:16. Цена Omni 9:16, 8 с, x1 — те же 12 бонусов.
- Кадры: **Nano Banana Pro**, **16:9**, **x1** (0 бонусов).
- Видео: **Omni 1.1 Flash**, режим **«Кадры»** (первый + последний), **16:9**, 720p, **8 с**, **x1** = **12 бонусов**. НЕ Veo: Veo не доводит камеру до конца — конечный кадр «проявляется пузырём».
- Перед тратой — сверка «образец → у нас» (модель, кадры, движение, цена) и прямое «да» владельца.

## Шаг 1. Первый кадр — Земля (Nano Banana Pro, 16:9)
Шаблон (меняется регион):
```
Ultra-photorealistic cinematic view of planet Earth from outer space, seen from a dramatic orbital perspective above <РЕГИОН> with <СТРАНА/ГОРОД> positioned near the center of the frame. A brilliant sunrise breaks across Earth's curved horizon with realistic atmospheric glow, detailed cloud systems, visible <БЕРЕГА/МОРЯ>, subtle city lights on the night side, deep black space filled with natural stars, realistic sunlight scattering, enormous sense of scale, premium IMAX space-documentary photography, NASA-inspired realism, highly detailed textures, natural color science, no text, no logos. Compose horizontally for a 16:9 cinematic video with <МЕСТО> visually centered for a forward dive.
```

## Шаг 2. Последний кадр — объект анфас (Nano Banana Pro, 16:9)
- Если объект реальный и святой/узнаваемый (Кааба, Набави, офис клиента) — прикрепить НАСТОЯЩЕЕ фото как образец и писать «keep … exactly as in the reference». Каабу без фото-образца ИИ не рисуем.
- Анфас, по центру, ничто не загораживает вход, вечерний кинематографичный свет, «Compose horizontally for a 16:9 cinematic video and keep the <объект> centered so the camera can finish directly in front of it».
- ⚠️ ГЛАВНОЕ (урок 04.11, v2 провалилась): последний кадр должен быть ДОСТИЖИМ камерой с неба — вид чуть сверху, над объектом открытое небо, ничего на пути (витрина на открытой улице, Кааба с верхней галереи). Кадр с уровня глаз внутри закрытого двора → модель не может влететь и подставляет кадр наплывом («появляется другой кадр»).
- ⚠️ Урок Макки 04.11: свет последнего кадра подбирать под дневной полёт (золотой час), иначе в конце ~0,4 с виден переход «день → вечер» наплывом.

## Шаг 3. Видео (Omni 1.1 Flash) — промпт автора, меняются место и направление
Добавлять всегда: «vertical 9:16», «The same warm golden-hour sunlight for the whole flight, one time of day, consistent lighting», «no cross-dissolve, no fade, no scene transitions», и описать спуск «descends from the open sky over <объект> … settles in front of …».
```
Create one seamless ultra-photorealistic cinematic Earth-to-destination reveal. Begin exactly from the uploaded Earth opening frame in outer space above <РЕГИОН> with <СТРАНА> centered below. The camera suddenly accelerates forward toward planet Earth with strong forward momentum and blockbuster-scale speed, diving in from the <НАПРАВЛЕНИЕ> toward <ГОРОД> in one uninterrupted shot. Pass through realistic atmospheric haze and volumetric clouds with natural motion blur, subtle camera vibration, dynamic exposure changes and believable sunlight scattering. Continue the same forward camera move toward <ГОРОД>, rapidly transitioning from orbital scale to aerial scale and then toward street level without cuts, teleportation, melting or obvious morphing. <ЛАНДШАФТ И ГОРОД> should resolve naturally as the camera gets closer. Sweep into <ГОРОД> with <НАСТРОЕНИЕ> energy, then smoothly decelerate as the camera approaches the <ОБЪЕКТ> shown in the uploaded reference. Finish directly in front of the <ОБЪЕКТ> with the architecture, signage, lighting, proportions and overall visual identity closely matching the reference image. End on a clean, stable hero shot of the <ОБЪЕКТ>. Ultra-photorealistic, premium commercial realism, Hollywood VFX quality, realistic physics, seamless scale transition, cinematic motion blur, volumetric light, believable cloud movement, natural camera behavior, one uninterrupted continuous shot, absolutely no cuts, no warped buildings, no melting, no surreal morphing, no extra logos, no random scene changes.
```
Если что-то не так — добавить строку из гайда: медленно → «Extremely rapid acceleration from orbit…»; режет → «One uninterrupted continuous shot, absolutely no cuts…»; не похоже → «Final architecture … must closely match the uploaded reference»; гнутся здания → «Rigid realistic architecture, straight lines remain straight…».

## Шаг 4. Проверка (до показа владельцу)
- В редакторе Flow запустить ▶ (иначе <video> не появляется), потом в странице собрать раскадровку 12 кадров через canvas и смотреть 5,5–7,5 с плотно (там бывает наплыв).
- Забрать файл: скачать из Flow в «Загрузки» владельца (его «да» на скачивание) → device_stage_files → монтаж → outbox/deliver (Telegram, оригиналом). base64 через javascript_tool блокируется — не путь.

## Сделано
- 04.11.2026 Макка v3 ✅ (9:16): Земля в золотом свете → облака → Хиджаз → Макка с башней → над крышей Харама → Кааба с верхней галереи, одна камера без наплыва, свет один. Минус: ИИ дорисовал вторую «часовую башню» на переднем плане (4,4–5,6 с).
- 04.11.2026 Макка v2 ✗ (16:9): Земля над Аравией → облака → горы Хиджаза → Макка → Харам → Кааба анфас с башней, 8 с, одна камера. Минус: 6,5–6,9 с наплыв день→вечер (см. урок в шаге 2).
