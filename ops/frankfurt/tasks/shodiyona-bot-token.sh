#!/usr/bin/env bash
# Франкфурт, ТОЛЬКО ВЛАДЕЛЕЦ В КОНСОЛИ: токен @ShodiyonaMebelUzBot (из @BotFather; на экране не виден, в чат/репозиторий
# не попадает) + установка/перезапуск службы papa-shodiyona. Откат: systemctl disable --now papa-shodiyona
set -euo pipefail
install -d -m 750 /etc/papa-shodiyona
if [[ ! -s /etc/papa-shodiyona/bot.env || "${1:-}" != "--keep" ]]; then
  read -rsp "Вставьте токен @ShodiyonaMebelUzBot (из @BotFather) и нажмите Enter: " TOK; echo
  [[ "$TOK" =~ ^[0-9]{6,}:[A-Za-z0-9_-]{30,}$ ]] || { echo "Это не похоже на токен — скопируйте целиком из @BotFather"; exit 1; }
  OWN=$(grep -E '^OWNER_IDS=' /etc/papa-genplan/genplan.env | cut -d= -f2-)
  MAN=$(grep -E '^MANAGER_IDS=' /etc/papa-shodiyona/bot.env 2>/dev/null | cut -d= -f2- || true)
  umask 077
  printf 'SHODIYONA_BOT_TOKEN=%s\nOWNER_IDS=%s\nMANAGER_IDS=%s\n' "$TOK" "$OWN" "$MAN" > /etc/papa-shodiyona/bot.env
  unset TOK
fi
set -a; . /etc/papa-shodiyona/bot.env; set +a
python3 - <<'PY'
import json, os, urllib.request, urllib.error
tok = os.environ["SHODIYONA_BOT_TOKEN"]
def tg(m):
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/{m}", timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}")
me = tg("getMe")
if not me.get("ok"):
    raise SystemExit(f"❌ Токен не принят Telegram: {me.get('description')}")
u = me["result"]["username"]
print(f"✅ бот @{u} ({me['result']['first_name']})")
if u.lower() != "shodiyonamebeluzbot":
    print("⚠️ Это НЕ @ShodiyonaMebelUzBot — проверьте, чей токен вставлен")
tg("deleteWebhook")
PY
id papa-shodiyona >/dev/null 2>&1 || useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin papa-shodiyona
chown -R root:papa-shodiyona /etc/papa-shodiyona; chmod 750 /etc/papa-shodiyona; chmod 640 /etc/papa-shodiyona/bot.env
( cd /opt/papa/modules/shodiyona && python3 -m unittest discover -q -s tests 2>&1 | tail -1 )
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-shodiyona.service /etc/systemd/system/
systemctl daemon-reload; systemctl enable -q papa-shodiyona; systemctl restart papa-shodiyona; sleep 5
echo "papa-shodiyona: $(systemctl is-active papa-shodiyona) · менеджеров: $(echo "$OWNER_IDS,$MANAGER_IDS" | tr ',' '\n' | grep -c .)"
journalctl -u papa-shodiyona -n 3 --no-pager -o cat
echo "== SHODIYONA_BOT_INSTALLED"
