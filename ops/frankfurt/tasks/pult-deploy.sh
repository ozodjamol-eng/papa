# Развернуть шлюз и Connect из репозитория: тесты → переключение → проверка → автооткат при сбое.
set -Eeuo pipefail
H=$(git -C /opt/papa rev-parse --short HEAD)
PY=/opt/nexus-private-control-v2/.venv/bin/python
code(){ curl -s -o /dev/null -m 5 -w '%{http_code}' "$@" || true; }
deploy(){
  local name=$1 base=$2 svc=$3 R prev
  R=$base/releases/papa-$H; prev=$(readlink "$base/current")
  if [[ "$prev" == "releases/papa-$H" ]]; then echo "$name: уже на papa-$H"; return 0; fi
  rm -rf "$R.tmp"; install -d "$R.tmp"; cp -r "/opt/papa/modules/pult/$name/." "$R.tmp/"
  find "$R.tmp" -name __pycache__ -prune -exec rm -rf {} +; chmod -R a+rX "$R.tmp"
  local t; t=$(cd "$R.tmp" && PYTHONDONTWRITEBYTECODE=1 timeout 300 "$PY" -m pytest -q -p no:cacheprovider tests 2>&1 | tail -1)
  echo "$name тесты: $t"
  if ! grep -qE '[0-9]+ passed' <<<"$t" || grep -qE 'failed|error' <<<"$t"; then
    rm -rf "$R.tmp"; echo "$name: TESTS_FAILED — остаёмся на $prev"; return 1; fi
  rm -rf "$R"; mv "$R.tmp" "$R"
  ln -sfn "releases/papa-$H" "$base/current.new" && mv -T "$base/current.new" "$base/current"
  systemctl restart "$svc"; sleep 4
  if health_$name; then echo "$name: OK → papa-$H (было $prev)"; else
    ln -sfn "$prev" "$base/current.new" && mv -T "$base/current.new" "$base/current"
    systemctl restart "$svc"; echo "$name: HEALTH_FAILED — откат на $prev"; return 1; fi
}
health_gateway(){ [[ $(code http://127.0.0.1:8788/) == 200 && $(code http://127.0.0.1:8788/api/status) == 401 ]]; }
health_connect(){ [[ $(code http://127.0.0.1:8789/.well-known/oauth-protected-resource) == 200 && $(code -X POST http://127.0.0.1:8789/mcp -H 'Content-Type: application/json' -d '{}') == 401 ]]; }
# Защита: первый переход на репозиторий — только если код совпадает с работающим (кроме тестов и служебных файлов)
guard(){
  local name=$1 dir; dir=$(readlink -f "$2")
  [[ "$(basename "$dir")" == papa-* ]] && return 0
  local d; d=$(diff -rq -x __pycache__ -x .pytest_cache -x '*.pyc' -x tests -x install_connect.sh -x nexus-connect.service \
       -x requirements.txt -x README.md -x deploy -x BUILD_REPORT.md -x '*.png' "/opt/papa/modules/pult/$name" "$dir" 2>&1 | grep -v '^Only in /opt/papa' || true)
  if [[ -n "$d" ]]; then echo "$name: код в репозитории отличается от работающего — развёртывание остановлено:"; echo "$d" | head -15; return 1; fi
  echo "$name: код совпадает с работающим ($dir)"
}
[[ "${FORCE:-0}" == 1 ]] || { guard gateway /opt/nexus-private-control-v2/current && guard connect /opt/nexus-connect/current; } || { echo "== PULT_DEPLOY_STOPPED"; exit 1; }
rc=0
deploy gateway /opt/nexus-private-control-v2 nexus-private-control-v2 || rc=1
deploy connect /opt/nexus-connect nexus-connect || rc=1
echo "gateway=$(systemctl is-active nexus-private-control-v2) connect=$(systemctl is-active nexus-connect)"
[[ $rc == 0 ]] && echo "== PULT_DEPLOY_DONE" || echo "== PULT_DEPLOY_PARTIAL (см. выше)"
exit $rc
