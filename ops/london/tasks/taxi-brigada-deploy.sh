#!/usr/bin/env bash
# 02.11 (владелец: «схема прораба — и для такси, делаем»): XOJAOBOD CITY 24 — «🚖 Бригадир + жамоа».
# Патч поверх ЖИВОГО кода (проверка md5 до правки), резервная копия, компиляция, тесты, перезапуск, проверка журнала;
# при любой ошибке — автоматический откат. Ручной откат: papa-update taxi-brigada-rollback (london).
set -uo pipefail
A=/opt/xojaobodcity24bot/app; P=/opt/papa/ops/london/patches/taxi-brigada.patch
PY=/opt/xojaobodcity24bot/venv/bin/python; BK=/opt/xojaobodcity24bot/deploy-backups; TS=$(date +%Y%m%d-%H%M%S)
cd $A || exit 1
echo "== 1. живой код не менялся?"
ok=1
for x in "main.py 1ed983167b291753e3fff65ce56101f6" "bot/keyboards/reply.py 4c81a1b1a1aa830f8c572d9c054b1bc7" "bot/handlers/drivers.py 9268207b02c03e2e0cc84eeca57563d6"; do
  set -- $x; [[ "$(md5sum < $1 | cut -d' ' -f1)" == "$2" ]] && echo "  ✅ $1" || { echo "  ❌ $1 изменился — СТОП"; ok=0; }
done
[[ -e bot/handlers/brigada.py ]] && { echo "  ❌ brigada.py уже есть — СТОП"; ok=0; }
[[ $ok == 1 ]] || exit 2
echo "== 2. резервная копия"
mkdir -p $BK && tar czf $BK/brigada-$TS.tgz main.py bot/keyboards/reply.py bot/handlers/drivers.py && echo "$BK/brigada-$TS.tgz" > $BK/brigada-LAST && echo "  $BK/brigada-$TS.tgz"
rollback() { echo "== ОТКАТ"; tar xzf $BK/brigada-$TS.tgz -C $A; rm -f $A/bot/handlers/brigada.py $A/tests/test_brigada.py; systemctl restart xojaobodcity24bot; sleep 5; echo "служба: $(systemctl is-active xojaobodcity24bot)"; exit 3; }
echo "== 3. патч"
patch -p1 --forward --no-backup-if-mismatch -d $A < $P || rollback
OWN=$(stat -c %U:%G main.py); chown $OWN bot/handlers/brigada.py tests/test_brigada.py main.py bot/keyboards/reply.py bot/handlers/drivers.py 2>/dev/null
echo "== 4. компиляция и тесты"
$PY -m py_compile main.py bot/handlers/brigada.py bot/handlers/drivers.py bot/keyboards/reply.py || rollback
( cd $A && $PY -m unittest tests.test_brigada 2>&1 | tail -3 ) | tee /tmp/brigada-test.log
grep -q "^OK" /tmp/brigada-test.log || rollback
echo "== 5. перезапуск"
T0=$(date '+%Y-%m-%d %H:%M:%S'); systemctl restart xojaobodcity24bot; sleep 10
[[ $(systemctl is-active xojaobodcity24bot) == active ]] || rollback
if journalctl -u xojaobodcity24bot --since "$T0" --no-pager -o cat | grep -qE "Traceback|Error"; then
  journalctl -u xojaobodcity24bot --since "$T0" --no-pager -o cat | tail -15; rollback; fi
echo "служба: active ✅"; journalctl -u xojaobodcity24bot --since "$T0" --no-pager -o cat | tail -4
echo "== TAXI_BRIGADA_DEPLOY_DONE"
