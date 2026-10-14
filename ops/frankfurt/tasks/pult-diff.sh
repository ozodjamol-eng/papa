# Только чтение: чем код Pult в репозитории отличается от работающего на сервере.
for pair in "gateway:/opt/nexus-private-control-v2/current" "connect:/opt/nexus-connect/current"; do
  name=${pair%%:*}; dir=$(readlink -f "${pair#*:}")
  echo "== $name: сервер = $dir"
  diff -rq -x __pycache__ -x .pytest_cache -x '*.pyc' "/opt/papa/modules/pult/$name" "$dir" 2>&1 \
    | sed "s#/opt/papa/modules/pult/$name#REPO#g; s#$dir#SERVER#g" | head -25
  diff -ru -x __pycache__ -x .pytest_cache -x '*.pyc' -x tests "/opt/papa/modules/pult/$name" "$dir" 2>/dev/null \
    | grep -E '^(\+\+\+ |@@|[-+][^-+])' | cut -c1-150 | head -40
done
echo "== PULT_DIFF_DONE"
