#!/usr/bin/env bash
# NEXUS London agent install. NEW separate service only, read-only.
# GENPLAN, bots, old NEXUS, nginx, postgres, firewall: untouched (nothing restarted, no files changed).
set -Eeuo pipefail; umask 022
S=/root/nexus-london; L=/usr/local/lib/nexus-london-agent; ENVF=/etc/nexus-london-agent.env
GWHOST=nexus-frankfurt.tail83fe5c.ts.net; GWURL=https://$GWHOST:8443
ip -4 -o addr show | grep -q '165.227.239.109/' || { echo WRONG_HOST; exit 1; }
command -v python3 >/dev/null || { echo NO_PYTHON3; exit 1; }

echo "== 1. code + system user (no shell, no home)"
id nexus-agent >/dev/null 2>&1 || useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin nexus-agent
install -d -m 755 $L; install -m 644 $S/nexus_london_agent.py $L/
python3 -I -m py_compile $L/nexus_london_agent.py && rm -rf $L/__pycache__

echo "== 2. selftest in the SAME sandbox as the service (read-only)"
SANDBOX=(-p User=nexus-agent -p Group=nexus-agent -p SupplementaryGroups=systemd-journal
  -p AmbientCapabilities=CAP_DAC_READ_SEARCH -p CapabilityBoundingSet=CAP_DAC_READ_SEARCH -p NoNewPrivileges=yes
  -p ProtectSystem=strict -p ProtectHome=yes -p PrivateTmp=yes -p PrivateDevices=yes
  "-p" "InaccessiblePaths=-/opt/xojaobod-genplan-v5/.env.production -/opt/xojaobod-genplan-v5/.env -/opt/xojaobod-genplan-v3/.env.production -/opt/xojaobod-genplan-v3/.env -/opt/xojaobod-autopost/.env -/opt/xojaobodcity24bot/.env")
timeout 60 systemd-run --quiet --wait --pipe --collect "${SANDBOX[@]}" /usr/bin/python3 -I $L/nexus_london_agent.py selftest | tee $S/selftest.json
echo "secret_check=$(timeout 30 systemd-run --quiet --wait --pipe --collect "${SANDBOX[@]}" /bin/sh -c 'cat /opt/xojaobod-genplan-v5/.env.production >/dev/null 2>&1 && echo READABLE || echo blocked')"

echo "== 3. route to Frankfurt gateway over tailnet"
GWIP=$(tailscale ip -4 nexus-frankfurt 2>/dev/null | head -1 || true)
[[ -n "$GWIP" ]] || { echo NO_TAILNET_ROUTE_TO_FRANKFURT; exit 1; }
echo "gateway_ip=$GWIP status_noauth=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 --resolve $GWHOST:8443:$GWIP $GWURL/api/status)  (401 = OK)"

echo "== 4. agent token (paste the line from Frankfurt; input is hidden)"
if [[ ! -s $ENVF ]] || [[ "${1:-}" == "--new-token" ]]; then
  read -rs -p "Token: " TOK; echo
  TOK=$(printf '%s' "$TOK" | tr -d '[:space:]')
  [[ ${#TOK} -ge 32 ]] || { echo TOKEN_TOO_SHORT; exit 1; }
  ( umask 077; printf 'NEXUS_GATEWAY_URL=%s\nNEXUS_GATEWAY_ADDR=%s\nNEXUS_AGENT_ID=london\nNEXUS_AGENT_TOKEN=%s\n' "$GWURL" "$GWIP" "$TOK" > $ENVF )
  unset TOK
fi
chmod 600 $ENVF; sed 's/TOKEN=.*/TOKEN=<hidden>/' $ENVF
code=$(set -a; . $ENVF; set +a; curl -s -o /dev/null -w '%{http_code}' --max-time 10 --resolve $GWHOST:8443:$GWIP -X POST $GWURL/api/agent/hello \
  -H "Authorization: Bearer $NEXUS_AGENT_TOKEN" -H 'X-Device-ID: london' -H 'Content-Type: application/json' \
  -d '{"platform":"Linux","hostname":"install-check","details":{"version":"install"}}')
echo "token_check=$code  (200 = OK)"; [[ $code == 200 ]] || { echo TOKEN_REJECTED; exit 1; }

echo "== 5. service"
install -m 644 $S/nexus-london-agent.service /etc/systemd/system/
systemctl daemon-reload; systemctl enable --now nexus-london-agent; sleep 8
echo "agent=$(systemctl is-active nexus-london-agent) mem=$(systemctl show nexus-london-agent -p MemoryCurrent --value)"
journalctl -u nexus-london-agent -n 5 --no-pager -o cat
echo "genplan=$(systemctl is-active xojaobod-genplan-v3.service 2>/dev/null || true) nexus_mcp=$(systemctl is-active nexus-mcp 2>/dev/null || true) nginx=$(systemctl is-active nginx)"
echo "== LONDON_AGENT_DONE (remove: systemctl disable --now nexus-london-agent)"
