#!/usr/bin/env bash
# ТОЛЬКО ЧТЕНИЕ, шаг 2: кто создавал пакет дайджеста (digest.png + manifest.json) в ~20:13 13–14.10. Ничего не меняет.
set -uo pipefail
G=/opt/xojaobod-genplan-v5
sp(){ sed 's|/| / |g' | cut -c1-230; }   # пробелы в путях — чтобы длинный путь не принимался за секрет при выводе
echo "== папки пакетов (manifest.json за 10 дней)"
find / -xdev \( -path /proc -o -path /sys -o -path '*/venv/*' \) -prune -o -type f -name manifest.json -mtime -10 -printf '%TY-%Tm-%Td %TH:%TM  %h\n' 2>/dev/null | sort | tail -10 | sp
D=$(find / -xdev \( -path /proc -o -path /sys \) -prune -o -type f -name digest.png -printf '%T@ %h\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
echo "== последняя папка пакета:"; echo "  $D" | sp; ls -la "$D" 2>/dev/null | sp
P=$(dirname "$D" 2>/dev/null)
echo "== соседние папки (по дням)"; ls -1 "$P" 2>/dev/null | tail -8 | sp
echo "== код, который пишет digest.png / manifest.json / photo_caption"
for dir in /opt/nexus /opt/ozod-hub /opt/nexus-control-center $G /root; do
  grep -rlE "digest\.png|photo_caption" "$dir" --include='*.py' --include='*.sh' --include='*.js' 2>/dev/null | grep -v -e '/venv/' -e evening_digest_publisher | head -10
done | sort -u | sp
echo "== таймеры и cron около 20:00–20:30"
grep -rhE "OnCalendar=.*(19|20):[0-5]" /etc/systemd/system/*.timer 2>/dev/null | sort -u
for f in /etc/systemd/system/*.timer; do grep -qE "OnCalendar=.*(19|20):[0-5]" "$f" && echo "  $(basename $f): $(systemctl is-enabled $(basename $f) 2>/dev/null)/$(systemctl is-active $(basename $f) 2>/dev/null)"; done
crontab -l 2>/dev/null | grep -vE '^\s*(#|$)' | cut -c1-160 | sp
ls /etc/cron.d 2>/dev/null | head
echo "== журнал 14.10 20:05–20:20 (кто работал перед дайджестом)"
journalctl --since "2026-10-14 20:05" --until "2026-10-14 20:20" --no-pager -o short-iso 2>/dev/null | grep -vE "sshd|CRON.*session|systemd-logind" | cut -c1-200 | sed -E 's/[0-9]{6,12}:[A-Za-z0-9_-]{30,}/<скрыто>/g' | head -40 | sp
echo "== EVENING_TRACE2_DONE"
