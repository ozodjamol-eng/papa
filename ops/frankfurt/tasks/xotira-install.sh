#!/usr/bin/env bash
# 🕊 Бот ХОТИРА МАРКАЗИ (@XotiraMarkaziBot): владелец вводит токен (на экране не виден, в чат/репозиторий не попадает),
# проверка «бот — админ канала @XOTIRAXOJAOBOD», установка службы papa-xotira. Откат: systemctl disable --now papa-xotira
set -euo pipefail
CH=@XOTIRAXOJAOBOD
install -d -m 750 /etc/papa-xotira
if [[ ! -s /etc/papa-xotira/xotira.env || "${1:-}" == "--token" ]]; then
  read -rsp "Вставьте токен @XotiraMarkaziBot (из @BotFather) и нажмите Enter: " TOK; echo
  [[ "$TOK" =~ ^[0-9]{6,}:[A-Za-z0-9_-]{30,}$ ]] || { echo "Это не похоже на токен — скопируйте целиком из @BotFather"; exit 1; }
  OWN=$(grep -E '^OWNER_IDS=' /etc/papa-genplan/genplan.env | cut -d= -f2-)
  umask 077
  printf 'XOTIRA_BOT_TOKEN=%s\nOWNER_IDS=%s\nXOTIRA_CHANNEL=%s\n' "$TOK" "$OWN" "$CH" > /etc/papa-xotira/xotira.env
  unset TOK
fi
set -a; . /etc/papa-xotira/xotira.env; set +a
python3 - <<'PY'
import json, os, urllib.request, urllib.parse, urllib.error
tok, ch = os.environ["XOTIRA_BOT_TOKEN"], os.environ["XOTIRA_CHANNEL"]
def tg(m, **p):
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/{m}?" + urllib.parse.urlencode(p), timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}")
me = tg("getMe")
if not me.get("ok"):
    raise SystemExit(f"❌ Токен не принят Telegram: {me.get('description')}")
me = me["result"]; print(f"✅ бот @{me['username']} ({me['first_name']})")
tg("deleteWebhook")      # если старый бот работал через вебхук — переводим на опрос
r = tg("getChatMember", chat_id=ch, user_id=me["id"]).get("result") or {}
ok = r.get("status") == "administrator" and r.get("can_post_messages")
print(("✅" if ok else "❌") + f" админ в {ch}: {r.get('status', 'нет')}" + ("" if ok else "  ← добавьте бота админом канала с правом «Публикация»"))
PY
id papa-xotira >/dev/null 2>&1 || useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin papa-xotira
chown -R root:papa-xotira /etc/papa-xotira; chmod 750 /etc/papa-xotira; chmod 640 /etc/papa-xotira/xotira.env
( cd /opt/papa/modules/xotira && python3 -m unittest discover -q -s tests 2>&1 | tail -1 )
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-xotira.service /etc/systemd/system/
systemctl daemon-reload; systemctl enable -q papa-xotira; systemctl restart papa-xotira; sleep 5
echo "papa-xotira: $(systemctl is-active papa-xotira) · память свободно $(free -m | awk '/Mem/{print $7}') МБ"
journalctl -u papa-xotira -n 3 --no-pager -o cat
echo "== XOTIRA_INSTALLED"
