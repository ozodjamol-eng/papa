#!/usr/bin/env bash
# 🧭 Показать последний отчёт GitHub-разведки, «Новинки сервисов» и очередь навыков на проверку (только чтение).
# 01.11 владелец: новинки всегда изучать — ассистент забирает очередь в сессию (скилл navyki-razvedka). Расход $0.
set -Eeuo pipefail
D=/var/lib/papa-razvedka-pub/github
[[ -d "$D" ]] || { echo "❌ нет $D — разведка ещё не запускалась (задача github-now)"; exit 1; }
for f in latest-github.txt latest-novinki.txt latest-masters.txt navyki-queue.json; do
  if [[ -f "$D/$f" ]]; then echo "===== $f ($(date -r "$D/$f" '+%d.%m %H:%M'))"; cat "$D/$f"; echo; else echo "===== $f — нет"; fi
done
echo "== GITHUB_SHOW_DONE"
