# Текущее состояние инфраструктуры

> Снимок фактов, а не планов. Обновляется при каждом изменении на серверах.
> Последнее обновление: 2026-10-14.

## Лондон — `xojaobodcity24bot`, 165.227.239.109, tailnet `nexus-core`

- 1 vCPU, ~1 ГБ RAM, диск 24 ГБ — **занято 54 %** (свободно 11 ГБ) после purge 2026-10-15 (+5 ГБ).
- PAPA подключён: `/opt/papa` (ключ только для чтения `/root/.ssh/papa_deploy`, порт 443), команда `papa-update [задача]`.
- **Ядро PAPA**: база PostgreSQL `papa` (владелец роль `papa`, NOLOGIN), схема v1, 11 таблиц, 3 пространства, 2 площадки; доступ пока только локальный. Установлено 2026-10-15.
- Память после остановки старого NEXUS: 597 МБ, swap 748 МБ (снижается). Апгрейд не нужен. Перезапущен 2026-10-15 10:33 (ядро 6.8.0-147): GENPLAN 5, боты, nginx, PostgreSQL, ozixon-mobile-api, агент — поднялись сами. В очереди GENPLAN висит один просроченный пост с 2026-10-13 22:00 (разобрать в фазе 3, сейчас не трогаем).
- 2026-10-22 22:57: ffmpeg задачи автопилота убит по нехватке памяти (swap после перезагрузки пропал → 0). Добавлен `/swapfile` 2 ГБ + строка в `/etc/fstab` (переживает перезагрузку). Шлюз, papa-genplan, автопилот перезапущены — active.
- Журналы ограничены 300 МБ: `/etc/systemd/journald.conf.d/papa-limit.conf`.
- Работает:
  - `xojaobod-genplan-v3.service` — **на самом деле GENPLAN 5** из `/opt/xojaobod-genplan-v5`, база `data/genplan_v3_production.db`. Публикует в группу Xo'jaobod City 24 через бота XOJAOBODCITYAVTOPOST24.
  - `xojaobodcity24bot.service`, `goldwater-bot.service`, nginx (goldwater.uz), PostgreSQL, `ozixon-mobile-api`.
  - **Старый NEXUS остановлен и выключен 2026-10-15** (23 работавших юнита из 41; список `/var/backups/papa-archive/old-nexus-units-*.state`, вернуть `papa-update nexus-old-restore`). Код `/opt/nexus` (903 МБ) пока на месте. Мёртвый маршрут Tailscale `nexus-core:443 → 8876` (старая панель) убрать.
  - Tailscale: `nexus-core:8443 → 8890` (ozixon-mobile-api) — работает, не трогать.
  - `nexus-london-agent.service` — агент NEXUS V2, только чтение (GENPLAN, службы, ресурсы). Без особых прав; файлы секретов ему недоступны.
- Крупное на диске:
  - Медиа NEXUS → GENPLAN очищены от старше 7 дней: `nexus_handoff` 313 МБ, `intelligence_media` 183 МБ.
  - `/root/.cache` (без pip), `/root/.local`, `/root/.claude-server-commander` — не трогаем (инструменты).
- Старое (V2 автопост, GENPLAN v3, gp2-заготовки, старые базы) — удалено, лежит в архиве `/var/backups/papa-archive/old-genplan-20261014_2249.tar.gz` (417 МБ).

## Франкфурт — `ubuntu-s-1vcpu-1gb-fra1`, 161.35.202.97, tailnet `nexus-frankfurt`

- `nexus-private-control-v2` (127.0.0.1:8788) — **из репозитория**, релиз `releases/papa-<коммит>` (`papa-update pult-deploy`, тесты + автооткат; прежний `r4-london` сохранён). Панель: `https://nexus-frankfurt.tail83fe5c.ts.net:8443/` (только tailnet).
- `nexus-connect` (127.0.0.1:8789) — **из репозитория**, `releases/papa-<коммит>` (прежний `r3` сохранён), OAuth + MCP для ChatGPT и Claude. Публично через Tailscale Funnel: `https://nexus-frankfurt.tail83fe5c.ts.net/mcp`.
- `papa-autopilot` (root, с 2026-10-16) — выполняет `papa-update <задача>` по заявке ИИ (`nexus_papa_task`): allow.json auto — сразу, остальное — кнопка владельца в пульте КАТТА ДАВРА, секреты — запрещены. Выключить: `systemctl disable --now papa-autopilot`.
- Куратор: `papa-curator.timer` 08:00/12:30/17:00 → `papa-razvedka@curate` (папки PAPA·Давра/Спорт → пульт КАТТА ДАВРА, PAPA·Музыка → пульт PaparazziUZ; без Gemini кадры не берёт). Вечерний отчёт куратора 21:30 в главном пульте. Папки 16.10 рассортированы по ключевым словам (Давра 100, Музыка 67, Шаҳар 90) — пересортировать с ИИ.
- Инструменты MCP: `nexus_papa_task`, `nexus_papa_result`, `nexus_status`, `nexus_tasks`, `nexus_audit`, `nexus_devices`, `nexus_run_check`, `nexus_genplan`, `nexus_razvedka` (отчёт из `/var/lib/papa-razvedka-pub/latest.json`, читает только шлюз).
- Перезапущен 2026-10-15 (ядро 6.8.0-147): все службы поднялись сами (шлюз, Connect, Tailscale, таймер Разведки). Диск 30 %, память 448/961 МБ.
- PAPA подключён: `/opt/papa`, `papa-update`. **Razvedka** установлена: пользователь `papa-razvedka`, venv `/opt/papa-venv/razvedka` (telethon 1.45), база `/var/lib/papa-razvedka/razvedka.sqlite3`, сессия `/etc/papa-razvedka/telegram.env` (0600). Вход — **временно основной профиль владельца** (устройство «PAPA Razvedka»), заменить отдельным профилем. Первый сбор 2026-10-14: 38 каналов, 5 758 постов, 0 ошибок, пик памяти 51 МБ. Ежедневный таймер `papa-razvedka-daily.timer` включён (06:10 Ташкент, отчёт в «Избранное»).
- **Voronka** (2026-10-15): приложение Meta «PAPA Voronka» (ID 911121901931568, **опубликовано (Live) 2026-10-15**, политика/удаление данных на papa-site, категория «Бизнес и страницы», иконки пока нет, без бизнес-портфолио, сценарий Instagram API со входом через Instagram). Instagram @paparazzi.uz (MEDIA_CREATOR, 238 735 подписчиков, id 17841400735314190) — тестировщик, токен (60 дней) в `/etc/papa-voronka/instagram.env` (0600). Проверка: `papa-update voronka-check`. Вебхуки выключены (опрос API). Служба `papa-voronka.service` (пользователь papa-voronka, опрос раз в 2 мин, до 120 МБ) установлена 2026-10-15; **в РАБОТЕ с 12:04** на последнем посте для всех (фильтр спама, ≤30/час), директ ведёт на визитку (HTTP 200). Бот заявок — тестовый (PAPA TEST); боевые каналы — отдельным шагом. Задачи: `voronka-install`, `voronka-status`, `voronka-invite`.
- **Сайт PAPA** (публичный репозиторий `ozodjamol-eng/papa-site`, GitHub Pages): визитка с двумя каналами (`links.json` — ссылки по источнику `?s=`), `privacy.html`, `data-deletion.html`, `icon.png` (1024). Адрес: https://ozodjamol-eng.github.io/papa-site/
- **Бот PAPA** @PapaUzBot (2026-10-15): токен `/etc/papa-voronka/bot.env` (0600), админ в обоих каналах (только приглашения); ссылки-заявки «panel» на панели: PaparazziUZ t.me/+HnzA67d2QvlhMzky, Хўжаобод t.me/+cFzm8zxxQYA2YTli (старая t.me/+t9ljKVMfWOkzNGYy тоже действует). Описания обоих каналов обновлены. Voronka приветствует и одобряет заявки по ссылкам бота.
- **Рабочий аккаунт Telegram «PAPA»** @papa_admin_uz (id 8904756361, новая SIM владельца, облачный пароль, номер скрыт) — вход на сервер по QR 2026-10-15, сессия `/etc/papa-tg/publisher.env` (0600). Тест ANON_OK; 2026-10-15 — анонимный админ Хўжаобод Сити 24 (права: анонимность, удаление сообщений), пока ничего не публикует. Затем — Разведка.
- **КАТТА ДАВРА** @kattadavrauz (бывший @XOJAOBODLIKLARIMIZ, ~3,4 тыс.) — главный канал (переименован владельцем 2026-10-15). В GENPLAN PAPA (11 слотов, бот), Voronka (приветствие), панели (первая карточка).
- **GENPLAN PAPA** (2026-10-15): служба `papa-genplan` (Франкфурт, пользователь papa-genplan, до 180 МБ), режим **shadow** — публикации только в PAPA TEST GROUP / PAPA TEST. Хаб «PAPA HUB» (-1004451211656), бот @PapaGenplanBot (админ хаба и PAPA TEST), аккаунт PAPA — участник хаба. Настройки `/etc/papa-genplan/genplan.env` (0600), база `/var/lib/papa-genplan/genplan.sqlite3`. Намоз/дуо/реклама — пока GENPLAN 5.
- **Тестовый контур** (2026-10-15): закрытый канал «PAPA TEST» (id -1004318108675), бот `@papa_test_88fb84_bot` — админ канала; токен `/etc/papa-test/bot.env` (0600). Проверка: `papa-update test-setup`.
- Watchdog каждые 2 мин (шлюз, Connect, Разведка, диск, память) → Healthchecks → Telegram. Шифрованная резервная копия ночью (02:17 UTC): база шлюза + база Разведки, по 14 копий. Скрипты ставятся из репозитория: `papa-update monitoring`.

## Автопилот Лондона — 2026-10-16 (код готов, ждёт установки владельцем)
- Код: `ops/london/runner/` (papa-runner), `ops/london/autopilot/allow.json`, шлюз `/api/runner/*`, `nexus_papa_task` с `server=london`.
- Установка: Франкфурт `papa-update london-runner-token` (шлюз + пропуск, токен показывается один раз) → Лондон `papa-update runner-install` (вставить токен).
- Новые задачи Лондона: `london-diagnose` (только чтение: упавшие юниты и почему, просроченные посты), `genplan5-overdue-skip` (старые просрочки >6 ч → skipped, с копией базы).
- Открыто на 16.10: `xojaobod-evening-digest.service` в состоянии failed (причину покажет `london-diagnose`); 1 просроченный пост GENPLAN 5 с 13.10 22:00.

## Отложено владельцем (делаем в конце)

- Смена всех паролей и токенов (Google, DigitalOcean, GitHub, Telegram, токен агента London).
- Перевод 2FA Instagram/YouTube с SMS на приложение-аутентификатор.

## 2026-10-15 18:07 — КАТТА ДАВРА в работе
- Франкфурт переименован: hostname `papa-frankfurt` (метка DO `papa-frankfurt`); papa-update понимает оба имени. Лондон — имя `xojaobodcity24bot` оставлено (GENPLAN 5).
- GENPLAN PAPA: КАТТА ДАВРА и PaparazziUZ (с 16.10) — 🟢 работа, Хўжаобод — 🧪 тест (тест-группа). Владелец бросает посты прямо в бот; PAPA HUB — склад. Постоянная панель владельца (сворачивается). 🌅 Утренний блок (с 16.10): Давра и PaparazziUZ — в каналы 05:00 «Хайрли тонг» / 06:30 «Бугун — … куни» (с 17.10), Хўжаобод — в тестовую группу от Бомдода; задача `morning-deploy`, обзор в боте — /morning.

## Передача дел — 2026-10-15 23:45 (утренний блок)
- Утренний блок включён с 16.10: Давра и PaparazziUZ — в каналы 05:00 «Хайрли тонг» (видео сезона + текст из 12 вариантов владельца), 06:30 «Бугун — … куни»; Хўжаобод — в PAPA TEST GROUP от Бомдода (+20/+45). Код: `modules/genplan/genplan/morning.py`, календарь `genplan/days.json`.
- Предпросмотр приходит владельцу в @PapaGenplanBot с кнопками «✅ Одобрить» и «🗑 Не публиковать»: выходит только одобренное; в 22:00 напоминание о неодобренных. Обзор и повтор предпросмотров: `/morning`.
- Видео «Хайрли тонг»: готовые чистые видео пересылаются профилем Разведки в NEXUS MORNING POOL (`papa-update morning-hunt`), бот берёт из пула, Gemini проверяет кадры; запасной — Pixabay с надписью. Текст — ИИ (Gemini) в стиле владельца.
- Задачи: `morning-deploy` (проверка прав/ключей), `morning-hunt` (охота + пересборка завтра), `morning-refresh` (пересборка без охоты), `morning-pool-clear` (очистить непроверенное).
- Если что-то пошло не так утром: бот сам пишет владельцу причину; откат — убрать `morning = {...}` у канала в config.toml и `papa-update genplan-restart`.
- Следующие шаги (ждут): PAPA СКЛАД + полки владельца для дневных постов (карта полок не подтверждена); баннер погоды Хўжаобода; хэштеги (карта ждёт «утверждаю»); автопилот с вето; ротация ключей в конце (в т.ч. Pixabay).
- 2026-10-17 14:36: **ИИ-текст — Anthropic Claude подключён** (Франкфурт, `genplan-ai-key` → AI_KEY_OK). Основной — `claude-haiku-5-5` (AI_PRIMARY=claude), запасной — Gemini; vision — Gemini. Баланс Anthropic 5 $, автопополнение выключено (потратить больше баланса нельзя). papa-genplan, papa-fabrika — active.
- 2026-10-17 17:15: **Voronka GOLD WATER** в РАБОТЕ — служба `papa-voronka-goldwater` (Франкфурт), @goldwaterandijon (BUSINESS, 2266), токен `/etc/papa-voronka/goldwater.env`, тестировщик приложения «PAPA Voronka» принят. Директ = текст ChatPlace → t.me/GoldWaterAndijonBot?start=instagram. ChatPlace остановлен 16.10 (неоплата), подписку не продлевать; доступ «ChatPlace-IG» в Instagram убрать после проверки.
- 2026-10-18 10:02: **Бот ХОТИРА МАРКАЗИ** (@XotiraMarkaziBot) — служба `papa-xotira` (Франкфурт), админ @XOTIRAXOJAOBOD, токен `/etc/papa-xotira/xotira.env`, база `/var/lib/papa-xotira/xotira.sqlite3`. Публикация только после «✅ Жойлаш» владельца. Проверено владельцем 10:06 (предпросмотр работает). Обновление: `papa-update xotira-restart`.

## 2026-10-18 — Резерв баз
- Франкфурт: `nexus-v2-backup` каждую ночь (02:17 UTC) копирует базы control, razvedka, genplan → AES-256 → 3 копии в /var/backups/nexus-v2 → копия в закрытый канал «PAPA РЕЗЕРВ» (id в /etc/papa-backup.env, шлёт @papa_test_88fb84_bot). Первая копия 18.10 11:53: control 100K, razvedka 1.8M, genplan 48K — все три в Telegram.
- 2026-10-18 17:37: **ИИ-ассистент** личного Telegram в РАБОТЕ — служба `papa-assistant` (Франкфурт), бот @ozodjamol_ai_bot («Озоджамол ИИ-ЁРДАМЧИСИ»), Business (Secretary) Mode включён, токен `/etc/papa-assistant/bot.env`. Осталось: подключить в Telegram (Telegram для бизнеса → Чат-боты, исключить «Контакты»).
- 2026-10-18 17:15: ключ шифрования копий заменён (`backup-rotate-key`): новые копии проверены расшифровкой, старый ключ и старые копии на сервере удалены.
- 2026-10-19 20:38: **ХОТИРА — обрезка фото** в РАБОТЕ: venv `/opt/papa-venv/xotira` (OpenCV 5.0.0, детектор лиц YuNet), служба `papa-xotira` из venv, до 160 МБ; тесты OK. Скриншоты обрезаются автоматически, кнопки владельца ✂️/👤/↩️/📎. Откат: `rm -rf /opt/papa-venv/xotira && papa-update xotira-restart`. Свободно памяти после установки 264 МБ.
- 2026-10-20 14:43: **🎬 Ролик «Об-ҳаво Хўжаобод»** включён: GitHub Actions `motion-weather` (05:15 + повтор 06:05 Ташкент) → ветка `motion`; GENPLAN Франкфурт (код 75abfdb, тесты OK) в 07:00 публикует видео в Хўжаобод Сити 24, нет ролика — текст. Проверка `motion-check`: Франкфурт скачивает ролик (8,1 МБ, ftyp), telethon 1.45, `video = true`. Первый выход — 21.10 07:00.
- 2026-10-20 22:07: **🎬 Кечки дайжест роликом** — Хўжаобод + КАТТА ДАВРА. Deploy-key `/etc/papa-motion/deploy_key` добавлен владельцем в GitHub (motion-key: доступ ЕСТЬ). Пробный рендер Actions `motion-digest` — OK (оба ролика 25 с, 1080×1920, 60 fps). GENPLAN обновлён (1e02b98, тесты OK). Первый выход — 21.10 20:30 (данные 19:50 → ролики ~20:00).
- 2026-10-21: **ХОТИРА — кнопка «🙏 Уже есть в канале — вежливо отказать»**: появляется на карточке, когда бот нашёл похожий пост (🔎/⚠️ со ссылкой); человеку уходит вежливый текст со ссылкой на опубликованный пост, заявка закрывается. Нажимает только владелец. Обновление: `papa-update xotira-restart`.
- 2026-10-21: **ХОТИРА — защита от обхода проверки повторов**: (А) отпечатки фото канала (ORB+RANSAC, OpenCV, таблица `prints`) — бот узнаёт то же фото даже после скриншота/обрезки/пересъёмки, в отчёте «📸 ЭТО ФОТО уже было»; новые посты канала и публикации бота добавляются сами; история — `papa-update xotira-scan` (качает фото → отпечатки → файлы удаляются, отчёт о повторах уже в канале). (Б) похожие имена ищутся при любых годах, имя/фамилия местами, другое написание. Решает владелец, бот сам не отказывает. Расход $0.
- 2026-10-21: **ХОТИРА — узнавание по лицу**: модель SFace int8 (OpenCV Zoo, sha256 2b0e94…, `/var/lib/papa-xotira/models/`, качает `xotira-scan`), таблицы `faces`/`faced`; на карточке «👤 ТОТ ЖЕ ЧЕЛОВЕК по лицу» (≥0.70) / «👤 Лицо похоже» (0.58–0.70), пороги по реальному каналу (630 лиц). Служба papa-xotira: MemoryMax 160→220M. Подсказка — решает владелец. Расход $0.
- 🏛 23.10: **PAPA ШТАБ** (@papa_shtab_bot, ключ `SHTAB_BOT_TOKEN` в /etc/papa-genplan/bots.env, админ PAPA HUB) — главный пульт: разрешения автопилота, тревоги, аудит, видео, отчёты, обзор. Пульты каналов: @PapaGenplanBot — КАТТА ДАВРА, @PaparazziUZ_PultBot — PaparazziUZ, @XOJAOBODCITYAVTOPOSTBOT — Хўжаобод. PAPA HUB — только склад утренних видео.
- 📣 23.10: **Реклама Хўжаобода — кампании с № и названием** (как в GENPLAN 5): 📣 РЕКЛАМА → список «📢 Мои кампании» (📂 / ➕ день / ⏸ Стоп через «✅ Утверждаю»); нумерация с №13 (kv `ad_seq`), названия — kv `ad_name_<id>`. Откат: `git revert` коммитов 27a41c7, e86f768 → `papa-update genplan-restart`.
