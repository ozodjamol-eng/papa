#!/usr/bin/env bash
# 🧭 Показать последний отчёт GitHub-разведки, «Новинки сервисов» и очередь навыков на проверку (только чтение).
# 01.11 владелец: новинки всегда изучать — ассистент забирает очередь в сессию (скилл navyki-razvedka). Расход $0.
set -Eeuo pipefail
D=/var/lib/papa-razvedka-pub/github
[[ -d "$D" ]] || { echo "❌ нет $D — разведка ещё не запускалась (задача github-now)"; exit 1; }
for f in latest-github.txt latest-novinki.txt latest-masters.txt latest-tg-masters.txt latest-neyro.txt navyki-queue.json; do
  if [[ -f "$D/$f" ]]; then echo "===== $f ($(date -r "$D/$f" '+%d.%m %H:%M'))"; cat "$D/$f"; echo; else echo "===== $f — нет"; fi
done
# 05.11: + тренд-разведка — для вечерней сводки Разведки (ассистент сортирует по направлениям к 22:00)
for f in /var/lib/papa-razvedka-pub/trend/latest-daily.txt /var/lib/papa-razvedka-pub/trend/latest-market.txt; do
  [[ -f "$f" ]] && { echo "===== $(basename "$f") ($(date -r "$f" '+%d.%m %H:%M'))"; cat "$f"; echo; }
done
echo "== GITHUB_SHOW_DONE"
