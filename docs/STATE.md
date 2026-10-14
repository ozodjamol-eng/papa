# Текущее состояние инфраструктуры

> Снимок фактов, а не планов. Обновляется при каждом изменении на серверах.
> Последнее обновление: 2026-10-14.

## Лондон — `xojaobodcity24bot`, 165.227.239.109, tailnet `nexus-core`

- 1 vCPU, ~1 ГБ RAM, диск 24 ГБ — **занято 82 %** (свободно 4,4 ГБ).
- Работает:
  - `xojaobod-genplan-v3.service` — **на самом деле GENPLAN 5** из `/opt/xojaobod-genplan-v5`, база `data/genplan_v3_production.db`. Публикует в группу Xo'jaobod City 24 через бота XOJAOBODCITYAVTOPOST24.
  - `xojaobodcity24bot.service`, `goldwater-bot.service`, nginx (goldwater.uz), PostgreSQL, `ozixon-mobile-api`.
  - Старый NEXUS: `nexus-mcp`, `nexus-taskd`, `nexus-tunnel` (туннель OpenAI), `nexus-control-center`, `ozod-nexus-*`, `nexus-media-director` и др.; ~30 служб `nexus-*`, большинство выключены.
  - `nexus-london-agent.service` — агент NEXUS V2, только чтение (GENPLAN, службы, ресурсы). Без особых прав; файлы секретов ему недоступны.
- Крупное на диске:
  - `/opt/xojaobod-genplan-v5/data/nexus_handoff` — 2,8 ГБ, `intelligence_media` — 1,7 ГБ (медиа NEXUS → GENPLAN).
  - `/var/log/journal` — 2,1 ГБ.
  - `/root/.cache` 743 МБ, `/root/.npm` 436 МБ, `/root/gp2_*_stage` 330 МБ.
- Старое (кандидаты в архив): `/opt/xojaobod-autopost` (V2, служба остановлена; `xojaobod-maintenance` работает только с ним), `/opt/xojaobod-genplan-v3` (99 МБ, на неё ссылается только комментарий в unit-файле), старые копии баз в `v5/backups` и `/opt/nexus/backups`.

## Франкфурт — `ubuntu-s-1vcpu-1gb-fra1`, 161.35.202.97, tailnet `nexus-frankfurt`

- `nexus-private-control-v2` (127.0.0.1:8788) — релиз `r4-london`. Панель: `https://nexus-frankfurt.tail83fe5c.ts.net:8443/` (только tailnet).
- `nexus-connect` (127.0.0.1:8789) — релиз `r3`, OAuth + MCP для ChatGPT и Claude. Публично через Tailscale Funnel: `https://nexus-frankfurt.tail83fe5c.ts.net/mcp`.
- Инструменты MCP: `nexus_status`, `nexus_tasks`, `nexus_audit`, `nexus_devices`, `nexus_run_check`, `nexus_genplan`.
- Watchdog каждые 2 мин → Healthchecks → Telegram. Шифрованная резервная копия ночью (02:17 UTC), откат `rollback.sh`.

## Отложено владельцем (делаем в конце)

- Смена всех паролей и токенов (Google, DigitalOcean, GitHub, Telegram, токен агента London).
- Перевод 2FA Instagram/YouTube с SMS на приложение-аутентификатор.
