#!/usr/bin/env bash
# Франкфурт, ТОЛЬКО ВЛАДЕЛЕЦ В КОНСОЛИ (автопилоту запрещено: -token): пропуск для исполнителя Лондона.
#   1) шлюз и Connect с поддержкой Лондона (тесты + автооткат);
#   2) новый токен устройства london-runner → в настройки шлюза (копия старых настроек), перезапуск, проверка, откат при сбое;
#   3) токен показывается ОДИН раз — скопируйте его в консоль Лондона (papa-update runner-install). В чат не отправлять.
# Повторный запуск выдаёт новый токен (старый перестаёт работать).
set -Eeuo pipefail
echo "1/3 шлюз и Connect:"
bash /opt/papa/ops/frankfurt/tasks/pult-deploy.sh || { echo "ШЛЮЗ НЕ ОБНОВИЛСЯ — ничего не меняю"; exit 1; }
echo "2/3 токен в настройки шлюза:"
ENVF=""
for f in $(systemctl show -p EnvironmentFiles --value nexus-private-control-v2 | tr ' ' '\n' | grep '^/' | sed 's/^-//'); do
  [[ -f "$f" ]] && grep -q '^NEXUS_AGENT_TOKENS_JSON=' "$f" && ENVF=$f
done
[[ -n "$ENVF" ]] || { echo "НЕ НАШЁЛ NEXUS_AGENT_TOKENS_JSON в настройках шлюза — остановка"; exit 1; }
B="$ENVF.bak-$(date +%F-%H%M%S)"; cp -a "$ENVF" "$B"
TOK=$(python3 -c 'import secrets; print(secrets.token_urlsafe(36))')
PAPA_TOK="$TOK" python3 - "$ENVF" <<'PY'
import json, os, sys, pathlib
p = pathlib.Path(sys.argv[1]); lines = p.read_text(encoding="utf-8").splitlines()
for i, line in enumerate(lines):
    if line.startswith("NEXUS_AGENT_TOKENS_JSON="):
        raw = line.split("=", 1)[1].strip()
        q = raw[0] if raw[:1] in ("'", '"') and raw[-1:] == raw[:1] else ""
        data = json.loads(raw[1:-1] if q else raw)
        data["london-runner"] = os.environ["PAPA_TOK"]
        val = json.dumps(data, separators=(",", ":"))
        lines[i] = "NEXUS_AGENT_TOKENS_JSON=" + (f"'{val}'" if q != '"' else '"' + val.replace('"', '\\"') + '"')
        break
p.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("  устройства:", ", ".join(sorted(data)))
PY
systemctl restart nexus-private-control-v2; ok=0
for i in $(seq 1 15); do sleep 2
  c=$(curl -s -o /dev/null -m 5 -w '%{http_code}' -X POST http://127.0.0.1:8788/api/runner/next -H "Authorization: Bearer $TOK" -H 'X-Device-ID: london-runner' || true)
  [[ $c == 200 ]] && { ok=1; break; }
done
if [[ $ok != 1 ]]; then cp -a "$B" "$ENVF"; systemctl restart nexus-private-control-v2; echo "!! ПРОВЕРКА НЕ ПРОШЛА — настройки возвращены"; exit 1; fi
echo "  шлюз принял пропуск (200); агент «только чтение» работает как раньше"
echo "3/3 скопируйте строку ниже и вставьте в консоли ЛОНДОНА, когда runner-install попросит Token:"
echo
echo "$TOK"
echo
unset TOK
echo "== LONDON_RUNNER_TOKEN_DONE"
