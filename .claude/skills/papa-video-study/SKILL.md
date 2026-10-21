---
name: papa-video-study
description: Полное изучение видео, которое прислал владелец, — кадры И речь через «Уши» (Франкфурт), потом честный вердикт и запись в Копилку фишек. Использовать ВСЕГДА, когда владелец присылает видео/рилс/урок/ролик (mp4, mov, ссылку на файл), даже если он просто пишет «посмотри» или «внедри это».
---

# Изучить видео владельца (кадры + речь)

Правило владельца: видео изучается полностью, включая речь. Вывод только по картинке — запрещён.
Говорить «не могу услышать» — нельзя: для этого есть «Уши».

## 1. Подготовка (в рабочей папке, исходник не трогать)
Прислана ссылка, а не файл (Instagram/YouTube), — скачать отсюда сеть не даёт: попросить владельца прислать файл.
```bash
V="/mnt/user-data/uploads/<файл>.mp4"; W=/home/claude/vs; rm -rf $W; mkdir -p $W/frames $W/mp3
ffprobe -v error -show_entries format=duration -of csv=p=0 "$V"
# кадры: листы 3×3, шаг 20 с (короткий рилс < 2 мин — шаг 3–5 с)
ffmpeg -v error -i "$V" -vf "fps=1/20,scale=480:-1,tile=3x3" $W/frames/f_%02d.jpg   # рилс < 2 мин: fps=1/4
# есть ли звук? пусто = звука нет → речь не расшифровывать, так и сказать владельцу
ffprobe -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 "$V"
# звук: куски по 2 мин (Gemini блокирует длинные куски целиком; короткие проходят)
ffmpeg -v error -i "$V" -vn -ac 1 -ar 16000 -b:a 32k -f segment -segment_time 120 $W/mp3/c%02d.mp3
```
Все листы кадров просмотреть (Read). Текст на экране, слайды, ссылки, QR — выписать.

## 2. «Уши» — партиями НЕ БОЛЬШЕ 6 кусков
Вывод задачи `hear` обрезается сначала (проверено 21.10: из 18 кусков вернулись только последние 6).
Поэтому: ≤ 6 кусков (≈12 мин речи) на один заход; ролик 36 мин = 3 захода по ~8–13 мин.

Каждый заход:
```bash
cd /home/claude/papa && git worktree prune; rm -rf /home/claude/ew
git fetch -q origin ears 2>/dev/null && git worktree add -q /home/claude/ew FETCH_HEAD \
  || git worktree add -q --orphan -b ears-tmp-$$ /home/claude/ew   # ветки ears ещё нет
cd /home/claude/ew && git rm -rq --ignore-unmatch ears; mkdir -p ears
cp /home/claude/vs/mp3/c0[0-5].mp3 ears/        # следующая партия: c0[6-9] c1[01] и т.д.
git add -A && git commit -qm "ears: <ролик>, часть N" && git push -q origin HEAD:ears
cd /home/claude/papa && git worktree remove --force /home/claude/ew
```
Затем `mcp__NEXUS__nexus_papa_task` task=`hear` (reason — по-русски, владелец видит в Telegram),
ждать (Bash `until`-пауза по 5 мин, не `sleep`), результат — `nexus_papa_result`.
Не запускать новую `hear`, пока прошлая не закончилась: исполнитель один, задачи стоят в очереди.

## 3. Очистка ветки `ears` (обязательно)
Удаление ветки прокси не пропускает — пушить пустой коммит:
```bash
cd /home/claude/papa && git worktree prune; rm -rf /home/claude/ew
git fetch -q origin ears && git worktree add -q /home/claude/ew FETCH_HEAD && cd /home/claude/ew && git rm -rq ears && git commit -qm "ears: очищено после расшифровки" && git push -q origin HEAD:ears
cd /home/claude/papa && git worktree remove --force /home/claude/ew
```

## 4. Вердикт владельцу (коротко, по-русски)
- Что в ролике (суть в 3–7 пунктах), кто автор и что он продаёт (курс/сервис/партнёрка).
- Что из этого УЖЕ есть в PAPA (сверить с `docs/STATE.md`, `docs/FISHKI.md`, `.claude/skills`).
- Что берём / дорабатываем / не берём — с причиной и расходом в $.
- Совет партнёра: делать / не делать, плюсы, минусы, риски. Цифры автора — «не проверено», если не сверены.
- Ничего не строить до ответа владельца (кроме записи в FISHKI).

## 5. Копилка фишек — автоматически, без просьбы
Строка в `docs/FISHKI.md`: дата | материал (+«расшифрован Ушами») | вердикт | что взяли/куда | статус.
Коммит в main с подписью Co-Authored-By.
