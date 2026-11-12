#!/usr/bin/env bash
# 📊 Apify: сколько потрачено в этом месяце и на что (только чтение, 12.11). Ключ — /etc/papa-razvedka/apify.env, на экран не выводится.
set -euo pipefail
. /etc/papa-razvedka/apify.env
python3 - "$APIFY_TOKEN" <<'P'
import json, sys, urllib.request
t = sys.argv[1]
def get(p):
    r = urllib.request.Request("https://api.apify.com/v2" + p, headers={"Authorization": "Bearer " + t})
    return json.load(urllib.request.urlopen(r, timeout=60))["data"]
lim = get("/users/me/limits")
cur, mx = lim.get("current", {}), lim.get("limits", {})
print("Цикл:", lim.get("monthlyUsageCycle", {}))
print(f"Потрачено: ${cur.get('monthlyUsageUsd', 0):.2f} из ${mx.get('maxMonthlyUsageUsd', 0):.2f}")
runs = get("/actor-runs?desc=1&limit=40")["items"]
tot = {}
for r in runs:
    a = r.get("actId"); u = (r.get("usageTotalUsd") or 0)
    k = (r.get("startedAt") or "")[:10]
    tot.setdefault(k, [0, 0.0]); tot[k][0] += 1; tot[k][1] += u
for k in sorted(tot): print(f"  {k}: запусков {tot[k][0]}, ${tot[k][1]:.3f}")
if runs:
    r = get(f"/actor-runs/{runs[0]['id']}")
    print("Последний запуск:", r.get("startedAt"), "| результатов:", (r.get("stats") or {}).get("resultCount", "?") if False else "", "| $", r.get("usageTotalUsd"))
P
echo "== APIFY_USAGE_DONE"
