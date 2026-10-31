#!/usr/bin/env bash
# Франкфурт, ТОЛЬКО ВЛАДЕЛЕЦ В КОНСОЛИ: токен бота заявок «уй ва таъмир» (из @BotFather; на экране не виден, в чат/репозиторий
# не попадает) + установка/перезапуск службы papa-usta. Эксперимент 31.10 (1 неделя). Откат: systemctl disable --now papa-usta
set -euo pipefail
install -d -m 750 /etc/papa-usta
if [[ ! -s /etc/papa-usta/bot.env || "${1:-}" != "--keep" ]]; then
  read -rsp "Вставьте токен нового бота (из @BotFather) и нажмите Enter: " TOK; echo
  [[ "$TOK" =~ ^[0-9]{6,}:[A-Za-z0-9_-]{30,}$ ]] || { echo "Это не похоже на токен — скопируйте целиком из @BotFather"; exit 1; }
  OWN=$(grep -E '^OWNER_IDS=' /etc/papa-genplan/genplan.env | cut -d= -f2-)
  umask 077; printf 'USTA_BOT_TOKEN=%s\nOWNER_IDS=%s\n' "$TOK" "$OWN" > /etc/papa-usta/bot.env; unset TOK
fi
set -a; . /etc/papa-usta/bot.env; set +a
python3 - <<'PY'
import json, os, urllib.request, urllib.error
tok = os.environ["USTA_BOT_TOKEN"]
def tg(m):
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/{m}", timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}")
me = tg("getMe")
if not me.get("ok"):
    raise SystemExit(f"❌ Токен не принят Telegram: {me.get('description')}")
print(f"✅ бот @{me['result']['username']} ({me['result']['first_name']})")
tg("deleteWebhook")
PY
id papa-usta >/dev/null 2>&1 || useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin papa-usta
chown -R root:papa-usta /etc/papa-usta; chmod 750 /etc/papa-usta; chmod 640 /etc/papa-usta/bot.env
( cd /opt/papa/modules/usta && python3 -m unittest discover -q -s tests 2>&1 | tail -1 )
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-usta.service /etc/systemd/system/
systemctl daemon-reload; systemctl enable -q papa-usta; systemctl restart papa-usta; sleep 4
echo "papa-usta: $(systemctl is-active papa-usta)"
journalctl -u papa-usta -n 3 --no-pager -o cat
echo "== USTA_BOT_INSTALLED"
