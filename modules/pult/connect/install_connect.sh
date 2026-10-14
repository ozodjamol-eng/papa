#!/usr/bin/env bash
# NEXUS Connect install. New separate service only; gateway, bots, nginx untouched. Public exposure is a SEPARATE step.
set -Eeuo pipefail; umask 022
S=/root/nexus-connect-ship; B=/opt/nexus-connect; PY=/opt/nexus-private-control-v2/.venv/bin/python; R=$B/releases/r1
[[ "$(hostname)" == ubuntu-s-1vcpu-1gb-fra1 ]] || { echo WRONG_HOST; exit 1; }
HOST=$(tailscale status --json | $PY -c 'import json,sys;print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')
BASE="https://$HOST:8443"; echo "BASE=$BASE"
echo "== 1. code + tests"
install -d -m 755 $B/releases; rm -rf "$R"; install -d -m 755 "$R"
cp -r $S/nexus_connect $S/tests "$R/"; chmod -R a+rX "$R"
( cd "$R" && PYTHONDONTWRITEBYTECODE=1 timeout 300 $PY -m pytest -q -p no:cacheprovider tests 2>&1 | tail -2 ) | tee $S/pytest.txt
grep -qE '^[0-9]+ passed' $S/pytest.txt && ! grep -q failed $S/pytest.txt || { echo TESTS_FAILED; exit 1; }
ln -sfn releases/r1 $B/current.new && mv -T $B/current.new $B/current
echo "== 2. user + secrets (never printed)"
id nexus-connect >/dev/null 2>&1 || useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin nexus-connect
install -d -m 700 -o nexus-connect -g nexus-connect /var/lib/nexus-connect
if [[ ! -s /etc/nexus-connect.env ]]; then
  ( umask 077; printf 'NEXUS_CONNECT_BASE_URL=%s\nNEXUS_CONNECT_DB=/var/lib/nexus-connect/connect.sqlite3\nNEXUS_GATEWAY_URL=http://127.0.0.1:8788\nNEXUS_CONNECT_SECRET=%s\n' "$BASE" "$(openssl rand -hex 32)" > /etc/nexus-connect.env )
fi
chmod 600 /etc/nexus-connect.env; sed 's/=.*/=<set>/' /etc/nexus-connect.env
echo "== 3. service (local only, 127.0.0.1:8789)"
install -m 644 $S/nexus-connect.service /etc/systemd/system/nexus-connect.service
systemctl daemon-reload; systemctl enable --now nexus-connect; sleep 4
systemctl is-active nexus-connect
echo "meta=$(curl -s http://127.0.0.1:8789/.well-known/oauth-protected-resource | $PY -c 'import json,sys;print(json.load(sys.stdin)["resource"])')"
echo "mcp_noauth=$(curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:8789/mcp -H 'Content-Type: application/json' -d '{}')"
echo "register_evil=$(curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:8789/register -H 'Content-Type: application/json' -d '{"redirect_uris":["https://evil.com/cb"]}')"
echo "gateway=$(systemctl is-active nexus-private-control-v2) bots_nginx=$(systemctl is-active nginx xojaobod.service | tr '\n' ' ')"
echo "== CONNECT_LOCAL_DONE (rollback: systemctl disable --now nexus-connect)"
