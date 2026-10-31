#!/usr/bin/env bash
# CADCraft (storytold/cadcraft, MIT/Apache) — бесплатный CAD с MCP. Ставит cadcraft-cli в ~/.local/bin с проверкой SHA256.
# Проверен skill-check 31.10.2026 (v0.8.0). Обновлять версию — только после повторного skill-check.
set -Eeuo pipefail
V=0.8.0; SHA=df3c2e668439f0410564b1fa9d21827bb663eb3d01703902c41f02b9c5276193
B="$HOME/.local/bin"; mkdir -p "$B"
command -v cadcraft-cli >/dev/null && cadcraft-cli --version 2>/dev/null | grep -q "$V" && { echo "уже стоит $V"; exit 0; }
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
curl -sSL -o "$T/c.tgz" "https://github.com/storytold/cadcraft/releases/download/v$V/cadcraft-$V-linux-x86_64.tar.gz"
echo "$SHA  $T/c.tgz" | sha256sum -c - >/dev/null || { echo "SHA256 НЕ СОВПАЛ — стоп"; exit 1; }
tar xzf "$T/c.tgz" -C "$T"; install -m 755 "$T/cadcraft-$V-linux-x86_64/bin/cadcraft-cli" "$B/cadcraft-cli"
echo "OK cadcraft-cli $V → $B"
