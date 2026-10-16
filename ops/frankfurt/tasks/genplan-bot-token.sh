#!/usr/bin/env bash
# 🤖 Токен бота-пульта канала (сейчас — «⭐ PaparazziUZ Пульт»). Токен вводит владелец, на экране не виден,
# в чат и репозиторий не попадает. Проверка: бот живой, админ в канале и в PAPA HUB → службы перезапускаются.
set -euo pipefail
VAR=PAPARAZZI_BOT_TOKEN; CH=@ozodjamoll
PY=/opt/papa-venv/razvedka/bin/python
read -rsp "Вставьте токен нового бота (из @BotFather) и нажмите Enter: " TOK; echo
[[ "$TOK" =~ ^[0-9]{6,}:[A-Za-z0-9_-]{30,}$ ]] || { echo "Это не похоже на токен — скопируйте целиком из @BotFather"; exit 1; }
set -a; . /etc/papa-genplan/genplan.env; set +a
rc=0
TOK="$TOK" CH="$CH" $PY - <<'PY' || rc=$?
import json, os, sys, urllib.request, urllib.parse, urllib.error
tok, ch, hub = os.environ["TOK"], os.environ["CH"], os.environ["HUB_CHAT_ID"]
def tg(m, **p):
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/{m}?" + urllib.parse.urlencode(p), timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}")
me = tg("getMe")
if not me.get("ok"):
    sys.exit(f"❌ Токен не принят Telegram: {me.get('description')}")
me = me["result"]
print(f"✅ бот @{me['username']} ({me['first_name']})")
bad = 0
for chat, need in ((ch, "публикация"), (hub, "PAPA HUB")):
    r = tg("getChatMember", chat_id=chat, user_id=me["id"]).get("result") or {}
    ok = r.get("status") == "administrator" and (chat != ch or r.get("can_post_messages"))
    print(f"{'✅' if ok else '❌'} админ в {chat if chat == ch else 'PAPA HUB'}: {r.get('status', 'нет')}"
          + ("" if ok else f"  ← сделайте бота админом ({need})"))
    bad += not ok
sys.exit(2 if bad else 0)
PY
[[ $rc -eq 1 ]] && { echo "Токен не сохранён."; exit 1; }
umask 077
touch /etc/papa-genplan/bots.env
grep -v "^$VAR=" /etc/papa-genplan/bots.env > /etc/papa-genplan/bots.env.new || true
printf '%s=%s\n' "$VAR" "$TOK" >> /etc/papa-genplan/bots.env.new
mv /etc/papa-genplan/bots.env.new /etc/papa-genplan/bots.env
chown root:papa-genplan /etc/papa-genplan/bots.env; chmod 0640 /etc/papa-genplan/bots.env
unset TOK
install -m 0644 /opt/papa/ops/frankfurt/systemd/papa-genplan.service /etc/systemd/system/papa-genplan.service
install -m 0644 /opt/papa/ops/frankfurt/systemd/papa-fabrika.service /etc/systemd/system/papa-fabrika.service
systemctl daemon-reload
( cd /opt/papa/modules/genplan && PAPA_GENPLAN_STATE=$(mktemp -d) POOL_VISION_GAP=0 $PY -m unittest discover -q -s tests 2>&1 | tail -1 )
systemctl restart papa-genplan papa-fabrika; sleep 6
echo "genplan: $(systemctl is-active papa-genplan) · fabrika: $(systemctl is-active papa-fabrika)"
journalctl -u papa-genplan -n 6 --no-pager -o cat | grep -v "^$" || true
echo "📱 Откройте нового бота и нажмите «Старт» (если ещё не нажимали) — придёт панель «Пульт PaparazziUZ готов»."
[[ $rc -eq 2 ]] && echo "⚠️ Токен сохранён, но бот ещё не админ — сделайте админом и запустите: papa-update genplan-restart"
echo "== BOT_TOKEN_DONE"
