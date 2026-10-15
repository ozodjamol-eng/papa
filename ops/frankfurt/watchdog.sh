#!/usr/bin/env bash
# NEXUS V2 independent watchdog: runs outside the gateway process. Read-only checks.
set -uo pipefail
fail=()
systemctl is-active --quiet nexus-private-control-v2 || fail+=("service_not_active")
code=$(curl -s -o /dev/null -m 5 -w '%{http_code}' http://127.0.0.1:8788/ || true)
[[ "$code" == 200 ]] || fail+=("http_root_$code")
code=$(curl -s -o /dev/null -m 5 -w '%{http_code}' http://127.0.0.1:8788/api/status || true)
[[ "$code" == 401 ]] || fail+=("auth_guard_$code")
hb=/var/lib/nexus-private-control/state/worker.heartbeat
if [[ -r $hb ]]; then
  age=$(( $(date +%s) - $(cut -d. -f1 "$hb") ))
  (( age < 120 )) || fail+=("worker_stalled_${age}s")
else fail+=("no_heartbeat"); fi
# PAPA: Connect (MCP для ChatGPT/Claude) и Разведка
systemctl is-active --quiet nexus-connect || fail+=("connect_not_active")
code=$(curl -s -o /dev/null -m 5 -w '%{http_code}' http://127.0.0.1:8789/.well-known/oauth-protected-resource || true)
[[ "$code" == 200 ]] || fail+=("connect_http_$code")
for u in papa-razvedka@run.service papa-razvedka@collect.service; do
  systemctl is-failed --quiet "$u" && fail+=("${u%%.service}_failed")
done
# Voronka: служба жива и сводка свежая (обновляется каждые 2 мин)
if systemctl is-enabled --quiet papa-voronka 2>/dev/null; then
  systemctl is-active --quiet papa-voronka || fail+=("voronka_not_active")
  vs=/var/lib/papa-voronka-pub/stats.json
  if [[ -e $vs ]]; then (( $(date +%s) - $(stat -c %Y "$vs") < 900 )) || fail+=("voronka_stalled"); fi
fi
free_kb=$(df -Pk /var/lib/nexus-private-control | awk 'NR==2{print $4}')
(( free_kb > 1048576 )) || fail+=("disk_low")
avail_kb=$(awk '/MemAvailable/{print $2}' /proc/meminfo)
(( avail_kb > 61440 )) || fail+=("memory_low")
if ((${#fail[@]})); then msg="FAIL ${fail[*]}"; suffix=/fail; else msg="OK worker_age=${age}s"; suffix=; fi
echo "$msg"
if [[ -n "${HC_PING_URL:-}" ]]; then
  curl -fsS -m 10 --retry 3 -o /dev/null --data-raw "frankfurt nexus-v2: $msg" "${HC_PING_URL}${suffix}" || echo "ping_failed"
fi
[[ -z "$suffix" ]]
