# Текущее состояние инфраструктуры

> Снимок фактов, а не планов. Обновляется при каждом изменении на серверах.
> Последнее обновление: 2026-10-14.

## Лондон — `xojaobodcity24bot`, 165.227.239.109, tailnet `nexus-core`

- 1 vCPU, ~1 ГБ RAM, диск 24 ГБ — **занято 73 %** (свободно 6,5 ГБ) после уборки 2026-10-14 (+2,1 ГБ).
- PAPA подключён: `/opt/papa` (ключ только для чтения `/root/.ssh/papa_deploy`, порт 443), команда `papa-update [задача]`.
- **Ядро PAPA**: база PostgreSQL `papa` (владелец роль `papa`, NOLOGIN), схема v1, 11 таблиц, 3 пространства, 2 площадки; доступ пока только локальный. Установлено 2026-10-15.
- Память: 56 % занято, **swap 47 %** (2026-10-15 08:31) — следить; кандидат на +1 ГБ RAM (+6 $/мес) по замерам. Ожидает перезапуска для обновлений безопасности.
- Журналы ограничены 300 МБ: `/etc/systemd/journald.conf.d/papa-limit.conf`.
- Работает:
  - `xojaobod-genplan-v3.service` — **на самом деле GENPLAN 5** из `/opt/xojaobod-genplan-v5`, база `data/genplan_v3_production.db`. Публикует в группу Xo'jaobod City 24 через бота XOJAOBODCITYAVTOPOST24.
  - `xojaobodcity24bot.service`, `goldwater-bot.service`, nginx (goldwater.uz), PostgreSQL, `ozixon-mobile-api`.
  - Старый NEXUS: `nexus-mcp`, `nexus-taskd`, `nexus-tunnel` (туннель OpenAI), `nexus-control-center`, `ozod-nexus-*`, `nexus-media-director` и др.; ~30 служб `nexus-*`, большинство выключены.
  - `nexus-london-agent.service` — агент NEXUS V2, только чтение (GENPLAN, службы, ресурсы). Без особых прав; файлы секретов ему недоступны.
- Крупное на диске:
  - `/opt/xojaobod-genplan-v5/data/nexus_handoff` — 2,8 ГБ, `intelligence_media` — 1,7 ГБ (медиа NEXUS → GENPLAN).
  - `/root/.cache` (без pip), `/root/.local`, `/root/.claude-server-commander` — не трогаем (инструменты).
  - `/root/gp2_*_stage` 330 МБ — в архив.
- Старое (кандидаты в архив): `/opt/xojaobod-autopost` (V2, служба остановлена; `xojaobod-maintenance` работает только с ним), `/opt/xojaobod-genplan-v3` (99 МБ, на неё ссылается только комментарий в unit-файле), старые копии баз в `v5/backups` и `/opt/nexus/backups`.

## Франкфурт — `ubuntu-s-1vcpu-1gb-fra1`, 161.35.202.97, tailnet `nexus-frankfurt`

- `nexus-private-control-v2` (127.0.0.1:8788) — **из репозитория**, релиз `releases/papa-<коммит>` (`papa-update pult-deploy`, тесты + автооткат; прежний `r4-london` сохранён). Панель: `https://nexus-frankfurt.tail83fe5c.ts.net:8443/` (только tailnet).
- `nexus-connect` (127.0.0.1:8789) — **из репозитория**, `releases/papa-<коммит>` (прежний `r3` сохранён), OAuth + MCP для ChatGPT и Claude. Публично через Tailscale Funnel: `https://nexus-frankfurt.tail83fe5c.ts.net/mcp`.
- Инструменты MCP: `nexus_status`, `nexus_tasks`, `nexus_audit`, `nexus_devices`, `nexus_run_check`, `nexus_genplan`, `nexus_razvedka` (отчёт из `/var/lib/papa-razvedka-pub/latest.json`, читает только шлюз).
- Ожидает перезапуска для обновлений безопасности ядра (System restart required) — согласовать время с владельцем.
- PAPA подключён: `/opt/papa`, `papa-update`. **Razvedka** установлена: пользователь `papa-razvedka`, venv `/opt/papa-venv/razvedka` (telethon 1.45), база `/var/lib/papa-razvedka/razvedka.sqlite3`, сессия `/etc/papa-razvedka/telegram.env` (0600). Вход — **временно основной профиль владельца** (устройство «PAPA Razvedka»), заменить отдельным профилем. Первый сбор 2026-10-14: 38 каналов, 5 758 постов, 0 ошибок, пик памяти 51 МБ. Ежедневный таймер `papa-razvedka-daily.timer` включён (06:10 Ташкент, отчёт в «Избранное»).
- Watchdog каждые 2 мин (шлюз, Connect, Разведка, диск, память) → Healthchecks → Telegram. Шифрованная резервная копия ночью (02:17 UTC): база шлюза + база Разведки, по 14 копий. Скрипты ставятся из репозитория: `papa-update monitoring`.

## Отложено владельцем (делаем в конце)

- Смена всех паролей и токенов (Google, DigitalOcean, GitHub, Telegram, токен агента London).
- Перевод 2FA Instagram/YouTube с SMS на приложение-аутентификатор.
