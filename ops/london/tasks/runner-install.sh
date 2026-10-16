#!/usr/bin/env bash
# Лондон, ТОЛЬКО ВЛАДЕЛЕЦ В КОНСОЛИ: исполнитель papa-runner — чтобы ИИ сам выполнял задачи ops/london/tasks
# после решения автопилота Франкфурта (безопасные — сразу, остальное — по кнопке владельца в Telegram).
# Токен берётся из вывода «papa-update london-runner-token» на Франкфурте; ввод скрыт, в чат не отправлять.
# Выключить: systemctl disable --now papa-runner   (GENPLAN 5, боты, агент «только чтение» не затрагиваются)
set -Eeuo pipefail
GWHOST=nexus-frankfurt.tail83fe5c.ts.net; GWURL=https://$GWHOST:8443; ENVF=/etc/papa-runner/runner.env
R=/opt/papa/ops/london/runner
echo "1/4 проверка кода исполнителя:"
python3 -I -m py_compile $R/papa_runner.py && echo "  OK"
echo "2/4 связь с Франкфуртом по tailnet:"
GWIP=$(tailscale ip -4 nexus-frankfurt 2>/dev/null | head -1 || true)
[[ -n "$GWIP" ]] || { echo "НЕТ МАРШРУТА К ФРАНКФУРТУ (tailscale) — остановка"; exit 1; }
echo "  $GWIP"
echo "3/4 пропуск (вставьте токен с Франкфурта; ввод скрыт):"
if [[ ! -s $ENVF ]] || [[ "${NEW_TOKEN:-0}" == 1 ]] || [[ -t 0 ]]; then
  read -rs -p "Token: " TOK; echo
  TOK=$(printf '%s' "$TOK" | tr -d '[:space:]')
  [[ ${#TOK} -ge 32 ]] || { echo "ТОКЕН СЛИШКОМ КОРОТКИЙ — остановка"; exit 1; }
  install -d -m 700 /etc/papa-runner
  ( umask 077; printf 'NEXUS_GATEWAY_URL=%s\nNEXUS_GATEWAY_ADDR=%s\nPAPA_RUNNER_TOKEN=%s\n' "$GWURL" "$GWIP" "$TOK" > $ENVF )
  unset TOK
fi
chmod 600 $ENVF
code=$(set -a; . $ENVF; set +a; curl -s -o /dev/null -w '%{http_code}' --max-time 10 --resolve $GWHOST:8443:$GWIP -X POST \
  $GWURL/api/runner/next -H "Authorization: Bearer $PAPA_RUNNER_TOKEN" -H 'X-Device-ID: london-runner' -H 'Content-Type: application/json' -d '{}')
echo "  проверка пропуска: $code (200 = OK)"; [[ $code == 200 ]] || { echo "ПРОПУСК НЕ ПРИНЯТ — служба не включена"; exit 1; }
echo "4/4 служба papa-runner:"
install -m 644 $R/papa-runner.service /etc/systemd/system/papa-runner.service
systemctl daemon-reload; systemctl enable -q papa-runner; systemctl restart papa-runner; sleep 4
echo "  papa-runner: $(systemctl is-active papa-runner)"
journalctl -u papa-runner -n 3 --no-pager -o cat
echo "  genplan=$(systemctl is-active xojaobod-genplan-v3) агент=$(systemctl is-active nexus-london-agent)"
echo "== RUNNER_INSTALL_DONE  (выключить: systemctl disable --now papa-runner)"
