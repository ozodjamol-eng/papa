#!/usr/bin/env bash
# ТОЛЬКО ЧТЕНИЕ: откуда вечерний дайджест GENPLAN 5 берёт «пакет» и какая служба старого NEXUS его готовила. Ничего не меняет.
set -uo pipefail
G=/opt/xojaobod-genplan-v5; U=xojaobod-evening-digest.service
hide(){ sed -E 's/[0-9]{6,12}:[A-Za-z0-9_-]{30,}/<скрыто>/g; s/(token|key|secret|password)([=: ]+)[^ ]{8,}/\1\2<скрыто>/Ig' | cut -c1-200; }
echo "== чем запускается"
ARGV=$(systemctl show $U -p ExecStart --value | sed -E 's/.*argv\[\]=([^;]*);.*/\1/')
echo "  $ARGV" | sed "s|$G|<G5>|g"
SCRIPT=$(echo "$ARGV" | tr ' ' '\n' | grep -m1 '\.py$'); echo "  скрипт: ${SCRIPT/#$G/<G5>}"
[[ -f "$SCRIPT" ]] || { echo "  скрипта нет"; }
echo "== что он читает (пути и слова package/пакет/json в коде)"
grep -nE "package|PACKAGE|\.json|Path\(|open\(|INVALID|getenv|environ" "$SCRIPT" 2>/dev/null | hide | sed "s|$G|<G5>|g" | head -40
MOD=$(grep -oE "from [a-zA-Z0-9_.]+ import|import [a-zA-Z0-9_.]+" "$SCRIPT" 2>/dev/null | awk '{print $2}' | grep -iE "digest|evening|package" | sort -u)
for m in $MOD; do f=$G/$(echo $m | tr . /).py; [[ -f $f ]] && { echo "--- модуль ${f/#$G/<G5>}"; grep -nE "package|PACKAGE|\.json|Path\(|INVALID|_DIR|_PATH" "$f" | hide | head -30; }; done
echo "== файлы-пакеты по датам (что лежит и когда обновлялось)"
find / -xdev \( -path /proc -o -path /sys -o -path /var/lib/docker -o -path '*/venv/*' -o -path '*/.venv/*' -o -path '*/node_modules/*' \) -prune -o \
  -type f \( -iname '*evening*' -o -iname '*digest*' \) -mtime -10 -printf '%TY-%Tm-%Td %TH:%TM\t%s\t%p\n' 2>/dev/null | sort | tail -25 | sed "s|$G|<G5>|g"
echo "== старые службы NEXUS, остановленные 15.10, которые касались дайджеста/вечера/погоды"
L=$(ls -1t /var/backups/papa-archive/old-nexus-units-*.state 2>/dev/null | head -1); echo "  список: ${L:-нет}"
[[ -n "$L" ]] && while read -r unit state act; do
  [[ "$act" == active ]] || [[ "$unit" == *.timer ]] || continue
  frag=$(systemctl show "$unit" -p FragmentPath --value 2>/dev/null)
  ex=$(systemctl show "$unit" -p ExecStart --value 2>/dev/null | sed -E 's/.*argv\[\]=([^;]*);.*/\1/' | cut -c1-160)
  hit=""; [[ -f "$frag" ]] && grep -qiE "digest|evening|weather|ob.?havo|vechki|kechki|package" "$frag" && hit="★"
  echo "$ex" | grep -qiE "digest|evening|weather|package|daily|x24" && hit="★"
  printf '  %s %-40s %-8s было:%s  %s\n' "${hit:- }" "$unit" "$state" "$act" "$ex"
done < "$L"
echo "== кто ещё пишет в ту же папку (поиск по коду /opt/nexus)"
for k in $(grep -oE "['\"][^'\"]*(digest|evening)[^'\"]*['\"]" "$SCRIPT" 2>/dev/null | tr -d "'\"" | grep -E "/|\.json" | sort -u | head -5); do
  echo "--- «$k»"; grep -rlF "$(basename "$k")" /opt/nexus --include='*.py' 2>/dev/null | head -8
done
echo "== EVENING_TRACE_DONE"
