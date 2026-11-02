#!/usr/bin/env bash
# Франкфурт, ТОЛЬКО ВЛАДЕЛЕЦ В КОНСОЛИ: токен бота VOLIDAM (из @BotFather; на экране не виден, в чат/репозиторий
# не попадает) + установка/перезапуск службы papa-volidam. Повторный запуск с --keep — только перезапуск.
# Откат: systemctl disable --now papa-volidam
set -euo pipefail
install -d -m 750 /etc/papa-volidam
if [[ ! -s /etc/papa-volidam/bot.env || "${1:-}" != "--keep" ]]; then
  read -rsp "Вставьте токен бота VOLIDAM (из @BotFather) и нажмите Enter: " TOK; echo
  [[ "$TOK" =~ ^[0-9]{6,}:[A-Za-z0-9_-]{30,}$ ]] || { echo "Это не похоже на токен — скопируйте целиком из @BotFather"; exit 1; }
  OWN=$(grep -E '^OWNER_IDS=' /etc/papa-genplan/genplan.env | cut -d= -f2-)
  CODE=$(grep -E '^MANAGER_CODE=' /etc/papa-volidam/bot.env 2>/dev/null | cut -d= -f2- || true)
  [[ -n "$CODE" ]] || CODE=$(head -c 9 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 10)
  umask 077
  printf 'VOLIDAM_BOT_TOKEN=%s\nOWNER_IDS=%s\nMANAGER_CODE=%s\n' "$TOK" "$OWN" "$CODE" > /etc/papa-volidam/bot.env
  unset TOK
fi
set -a; . /etc/papa-volidam/bot.env; set +a
python3 - <<'PY'
import json, os, urllib.request, urllib.error
tok = os.environ["VOLIDAM_BOT_TOKEN"]
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
tg("deleteWebhook")
print(f"\n👤 Ссылка для Нодирбека и филиала (по ней они станут менеджерами и будут получать заявки):\n"
      f"   https://t.me/{u}?start=mgr_{os.environ['MANAGER_CODE']}\n")
PY
id papa-volidam >/dev/null 2>&1 || useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin papa-volidam
chown -R root:papa-volidam /etc/papa-volidam; chmod 750 /etc/papa-volidam; chmod 640 /etc/papa-volidam/bot.env
( cd /opt/papa/modules/volidam && python3 -m unittest discover -q -s tests 2>&1 | tail -1 )
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-volidam.service /etc/systemd/system/
systemctl daemon-reload; systemctl enable -q papa-volidam; systemctl restart papa-volidam; sleep 5
echo "papa-volidam: $(systemctl is-active papa-volidam)"
journalctl -u papa-volidam -n 3 --no-pager -o cat
echo "== VOLIDAM_BOT_INSTALLED"
