#!/usr/bin/env bash
# 🧭 GitHub-разведка: внеочередной отчёт сейчас → «PAPA ОТЧЁТЫ». Только чтение GitHub + оценка Haiku (~0,02 $).
set -Eeuo pipefail
U=papa-razvedka@github-auto.service
systemctl start --no-block "$U"; sleep 2
journalctl -u "$U" -f -n 0 -o cat & J=$!
while systemctl is-active -q "$U" || [[ "$(systemctl show -p ActiveState --value "$U")" == activating ]]; do sleep 3; done
sleep 1; kill $J 2>/dev/null || true
echo "результат: $(systemctl show -p Result --value "$U")"
echo "== GITHUB_NOW_DONE"
