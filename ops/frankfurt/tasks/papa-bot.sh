# Боевой бот PAPA: создание (через профиль владельца), права в каналах, описания каналов, ссылки-заявки для панели.
# Затем Voronka переключается с тестового бота на боевой и приветствует вступивших в оба канала.
set -Eeuo pipefail
[[ -s /etc/papa-razvedka/telegram.env ]] || { echo "NO_LOGIN"; exit 1; }
( set -a; . /etc/papa-razvedka/telegram.env; set +a; /opt/papa-venv/razvedka/bin/python /opt/papa/ops/frankfurt/papa_bot_setup.py )
if id papa-voronka >/dev/null 2>&1 && [[ -s /etc/papa-voronka/bot.env ]]; then
  chown -R papa-voronka:papa-voronka /etc/papa-voronka
  install -m 644 /opt/papa/ops/frankfurt/systemd/papa-voronka.service /etc/systemd/system/
  systemctl daemon-reload; systemctl restart papa-voronka; sleep 5
  echo "papa-voronka: $(systemctl is-active papa-voronka)"
  journalctl -u papa-voronka -n 5 -o cat --no-pager
fi
echo "== PAPA_BOT_DONE"
