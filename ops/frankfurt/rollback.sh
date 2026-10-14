#!/usr/bin/env bash
# Roll back ONLY the NEXUS V2 gateway code to the morning release. Other services untouched.
set -Eeuo pipefail
B=/opt/nexus-private-control-v2
target=${1:-NEXUS_PRIVATE_CONTROL_V2}
[[ -d "$B/$target/nexus_control" ]] || { echo "no release $target"; exit 1; }
ln -sfn "$target" "$B/current.new" && mv -T "$B/current.new" "$B/current"
systemctl restart nexus-private-control-v2; sleep 3
systemctl is-active nexus-private-control-v2 && echo "ROLLED_BACK_TO $target"
