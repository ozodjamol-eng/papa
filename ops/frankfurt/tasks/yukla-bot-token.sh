#!/usr/bin/env bash
# Франкфурт, ТОЛЬКО ВЛАДЕЛЕЦ В КОНСОЛИ: токен «Хўжаобод Юкла ⚡» (@XojaobodYuklaBot) — на экране не виден, в чат/репозиторий
# не попадает; + venv с yt-dlp, служба papa-yukla. Повтор безопасен (--keep — не спрашивать токен). Откат: systemctl disable --now papa-yukla
set -euo pipefail
install -d -m 750 /etc/papa-yukla
if [[ ! -s /etc/papa-yukla/bot.env || "${1:-}" != "--keep" ]]; then
  read -rsp "Вставьте токен бота XojaobodYuklaBot (из @BotFather) и нажмите Enter: " TOK; echo
  [[ "$TOK" =~ ^[0-9]{6,}:[A-Za-z0-9_-]{30,}$ ]] || { echo "Это не похоже на токен — скопируйте целиком из @BotFather"; exit 1; }
  OWN=$(grep -E '^OWNER_IDS=' /etc/papa-genplan/genplan.env | cut -d= -f2-)
  umask 077; printf 'YUKLA_BOT_TOKEN=%s\nOWNER_IDS=%s\nYUKLA_SUB_CHAT=@xojaobodcity24\n' "$TOK" "$OWN" > /etc/papa-yukla/bot.env; unset TOK
fi
set -a; . /etc/papa-yukla/bot.env; set +a
python3 - <<'PY'
import json, os, urllib.request, urllib.error
tok = os.environ["YUKLA_BOT_TOKEN"]
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
command -v ffmpeg >/dev/null || { apt-get update -qq && apt-get install -y -qq ffmpeg >/dev/null; }
[[ -x /opt/papa-venv/yukla/bin/pip ]] || python3 -m venv /opt/papa-venv/yukla
/opt/papa-venv/yukla/bin/pip install -q --upgrade yt-dlp
echo "yt-dlp: $(/opt/papa-venv/yukla/bin/yt-dlp --version) | ffmpeg: $(ffmpeg -version | head -1 | cut -d' ' -f3)"
id papa-yukla >/dev/null 2>&1 || useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin papa-yukla
chown -R root:papa-yukla /etc/papa-yukla; chmod 750 /etc/papa-yukla; chmod 640 /etc/papa-yukla/bot.env
( cd /opt/papa/modules/yukla && python3 -m unittest discover -q -s tests 2>&1 | tail -1 )
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-yukla.service /etc/systemd/system/
systemctl daemon-reload; systemctl enable -q papa-yukla; systemctl restart papa-yukla; sleep 4
echo "papa-yukla: $(systemctl is-active papa-yukla)"
journalctl -u papa-yukla -n 3 --no-pager -o cat
free -m | awk 'NR==2{print "память: занято " $3 " из " $2 " МБ"}'
echo "== YUKLA_BOT_INSTALLED"
