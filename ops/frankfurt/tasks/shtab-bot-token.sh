#!/usr/bin/env bash
# 🏛 Токен нового ГЛАВНОГО пульта «PAPA ШТАБ» (решение владельца 23.10). Токен вводит владелец, на экране не виден,
# в чат и репозиторий не попадает. Проверка: бот живой, админ в PAPA HUB. Службы НЕ перезапускаются — штаб
# подключается отдельным шагом после теста (пульты каналов работают как прежде).
set -euo pipefail
VAR=SHTAB_BOT_TOKEN
PY=/opt/papa-venv/razvedka/bin/python
read -rsp "Вставьте токен бота PAPA ШТАБ (из @BotFather) и нажмите Enter: " TOK; echo
[[ "$TOK" =~ ^[0-9]{6,}:[A-Za-z0-9_-]{30,}$ ]] || { echo "Это не похоже на токен — скопируйте целиком из @BotFather"; exit 1; }
set -a; . /etc/papa-genplan/genplan.env; set +a
rc=0
TOK="$TOK" $PY - <<'PY' || rc=$?
import json, os, sys, urllib.request, urllib.parse, urllib.error
tok, hub = os.environ["TOK"], os.environ["HUB_CHAT_ID"]
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
r = tg("getChatMember", chat_id=hub, user_id=me["id"]).get("result") or {}
ok = r.get("status") == "administrator"
print(f"{'✅' if ok else '❌'} админ в PAPA HUB: {r.get('status', 'нет')}" + ("" if ok else "  ← сделайте бота админом PAPA HUB"))
sys.exit(0 if ok else 2)
PY
[[ $rc -eq 1 ]] && { echo "Токен не сохранён."; exit 1; }
umask 077
touch /etc/papa-genplan/bots.env
grep -v "^$VAR=" /etc/papa-genplan/bots.env > /etc/papa-genplan/bots.env.new || true
printf '%s=%s\n' "$VAR" "$TOK" >> /etc/papa-genplan/bots.env.new
mv /etc/papa-genplan/bots.env.new /etc/papa-genplan/bots.env
chown root:papa-genplan /etc/papa-genplan/bots.env; chmod 0640 /etc/papa-genplan/bots.env
unset TOK
echo "🔒 Токен сохранён. Службы не трогал — штаб подключу отдельным шагом."
[[ $rc -eq 2 ]] && echo "⚠️ Бот ещё не админ PAPA HUB — сделайте админом и запустите эту задачу ещё раз."
echo "== SHTAB_TOKEN_DONE"
