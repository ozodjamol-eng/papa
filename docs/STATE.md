# Текущее состояние инфраструктуры

> Снимок фактов, а не планов. Обновляется при каждом изменении на серверах.
> Последнее обновление: 2026-10-14.

## Лондон — `xojaobodcity24bot`, 165.227.239.109, tailnet `nexus-core`

- 1 vCPU, ~1 ГБ RAM, диск 24 ГБ — **занято 54 %** (свободно 11 ГБ) после purge 2026-10-15 (+5 ГБ).
- PAPA подключён: `/opt/papa` (ключ только для чтения `/root/.ssh/papa_deploy`, порт 443), команда `papa-update [задача]`.
- **Ядро PAPA**: база PostgreSQL `papa` (владелец роль `papa`, NOLOGIN), схема v1, 11 таблиц, 3 пространства, 2 площадки; доступ пока только локальный. Установлено 2026-10-15.
- Память после остановки старого NEXUS: 597 МБ, swap 748 МБ (снижается). Апгрейд не нужен. Перезапущен 2026-10-15 10:33 (ядро 6.8.0-147): GENPLAN 5, боты, nginx, PostgreSQL, ozixon-mobile-api, агент — поднялись сами. В очереди GENPLAN висит один просроченный пост с 2026-10-13 22:00 (разобрать в фазе 3, сейчас не трогаем).
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
- Инструменты MCP: `nexus_status`, `nexus_tasks`, `nexus_audit`, `nexus_devices`, `nexus_run_check`, `nexus_genplan`, `nexus_razvedka` (отчёт из `/var/lib/papa-razvedka-pub/latest.json`, читает только шлюз).
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

## Отложено владельцем (делаем в конце)

- Смена всех паролей и токенов (Google, DigitalOcean, GitHub, Telegram, токен агента London).
- Перевод 2FA Instagram/YouTube с SMS на приложение-аутентификатор.

## 2026-10-15 18:07 — КАТТА ДАВРА в работе
- Франкфурт переименован: hostname `papa-frankfurt` (метка DO `papa-frankfurt`); papa-update понимает оба имени. Лондон — имя `xojaobodcity24bot` оставлено (GENPLAN 5).
- GENPLAN PAPA: КАТТА ДАВРА — 🟢 работа (посты в @kattadavrauz), Хўжаобод и PaparazziUZ — 🧪 тест. Владелец бросает посты прямо в бот; PAPA HUB — склад. Постоянная панель владельца (сворачивается). 🌅 Утренний блок (с 16.10): Давра и PaparazziUZ — в каналы 06:00/06:30, Хўжаобод — в тестовую группу от Бомдода; задача `morning-deploy`, обзор в боте — /morning.
