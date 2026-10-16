#!/usr/bin/env bash
# ТОЛЬКО ЧТЕНИЕ, шаг 3: как пакет дайджеста попадал на Лондон (handoff) и что пришло 15.10. Ничего не меняет.
set -uo pipefail
R=/opt/xojaobod-genplan-v5/data/factory_review
sp(){ sed 's|/| / |g' | sed -E 's/[0-9]{6,12}:[A-Za-z0-9_-]{30,}/<скрыто>/g' | cut -c1-230; }
echo "== handoff-proof 14.10"; python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(json.dumps(d,ensure_ascii=False,indent=1)[:1500])" "$R/evening-digest-2026-10-14/handoff-proof.json" 2>&1 | sp
echo "== manifest 14.10 (ключи и короткие значения)"; python3 -c "
import json,sys; d=json.load(open(sys.argv[1]))
for k,v in d.items(): print(' ',k,'=',str(v)[:90])" "$R/evening-digest-2026-10-14/manifest.json" 2>&1 | sp
echo "== папка 15.10"; ls -la "$R/evening-digest-2026-10-15" 2>&1 | sp
for f in "$R"/evening-digest-2026-10-15/*.json; do [[ -f $f ]] && { echo "--- $(basename $f)"; head -c 800 "$f" | sp; echo; }; done
echo "== кто заходил на сервер 14.10 и 15.10 в 20:00–20:30"
for d in 2026-10-14 2026-10-15; do journalctl --since "$d 19:50" --until "$d 20:31" --no-pager -o short-iso _COMM=sshd 2>/dev/null | grep -E "Accepted|session opened" | cut -c1-170 | sp; done
journalctl --since "2026-10-14 20:08" --until "2026-10-14 20:14" --no-pager -o short-iso 2>/dev/null | grep -vE "UFW BLOCK|apscheduler|magicsock|derp|prayer-watchdog|nexus-watch" | cut -c1-170 | head -25 | sp
echo "== EVENING_TRACE3_DONE"
