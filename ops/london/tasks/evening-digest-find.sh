#!/usr/bin/env bash
# ТОЛЬКО ЧТЕНИЕ: найти СБОРЩИК вечернего дайджеста (кто делает digest.png + manifest + handoff-proof) на Лондоне и в архивах.
set -uo pipefail
sp(){ sed 's|/| / |g' | cut -c1-200; }
K='handoff-proof|background_matches_weather|weather_as_of|КЕЧКИ ДАЙЖЕСТ|evening-digest-'
echo "== протокол (как задумано)"; sed -n 1,60p /opt/xojaobod-genplan-v5/docs/EVENING_DIGEST_PROTOCOL.md 2>/dev/null | cut -c1-200
echo "== код на диске с признаками сборщика"
grep -rlE "$K" /opt /root /home /srv --include='*.py' --include='*.sh' --include='*.js' --include='*.md' 2>/dev/null \
  | grep -v -e '/venv/' -e 'evening_digest_publisher' -e '/opt/papa/' -e 'factory_review/evening-digest-20' | head -20 | sp
echo "== внутри архивов"
for a in /var/backups/papa-archive/*.tar.gz; do
  [[ -f $a ]] || continue
  n=$(tar -tzf "$a" 2>/dev/null | grep -iE "evening|digest" | grep -v -e '/venv/' -e '__pycache__' | head -10)
  [[ -n "$n" ]] && { echo "--- $(basename "$a")"; echo "$n" | sp; }
done
echo "== EVENING_FIND_DONE"
