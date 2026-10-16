# PAPA Voronka

Комментарий в Instagram → личный ответ в директ со ссылкой → заявка в Telegram-канал → приветствие бота → одобрение.
Официальные API Meta и Telegram, без вебхуков (опрос раз в 2 минуты). Только стандартная библиотека Python.

- `config.toml` — режим (всем / по словам), посты, тексты (Instagram-директ — узбекская латиница; Telegram — кириллица), каналы. Секретов нет.
- Токен Instagram: `/etc/papa-voronka/instagram.env` (`papa-update voronka-token`), продлевается сам раз в 7 дней.
- Бот: пока тестовый (`/etc/papa-test/bot.env`), канал PAPA TEST.
- Защита: только посты из списка; старые комментарии не трогает; один директ человеку на пост; предел в час; пауза при лимите Meta; `dry_run = true` — ничего не отправляет.

Команды на сервере: `papa-update voronka-install`, `papa-update voronka-status`.
