# Моушн «Об-ҳаво Хўжаобод» — каждый день в 07:00 (утверждено владельцем 20.10.2026)

Вертикаль 1080×1920, 60 fps, 15 с, H.264 + AAC. Canvas-сцена (скилл vizavi-motion) + Playwright + FFmpeg, музыка/звуки — numpy.
Варианты по погоде: clear / partly / cloudy / fog / rain / snow; минус для зимы; «ҲОЗИР» = прогноз на 07:00.

Как работает:
1. GitHub Actions `motion-weather` в 05:15 (повтор 06:05) по Ташкенту: прогноз open-meteo → `make.py` → MP4 в ветку `motion`.
   Франкфурт (1 ГБ ОЗУ) браузер не тянет (замер: 570–1400 МБ) — поэтому рендер на GitHub (бесплатно).
2. GENPLAN (Франкфурт) в 07:00: `channels.xojaobod.info.video = true` → скачивает
   `https://raw.githubusercontent.com/ozodjamol-eng/papa/motion/xojaobod-weather-ДАТА.mp4` и публикует видео с прежней подписью
   (погода + курс). Нет файла/ошибка → прежний текстовый пост + сообщение владельцу.
Откат: `info = { at = "07:00" }` без `video` и `papa-update genplan-restart`.

Ручной тест: `git push origin HEAD:motion-test` → рендер; локально: `python3 make.py out` (или `python3 make.py out данные.json`).
