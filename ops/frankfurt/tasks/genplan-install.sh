# GENPLAN PAPA: хаб, бот, теневой режим (публикации только в тестовые чаты). Рабочие каналы не трогаются.
set -Eeuo pipefail
[[ -s /etc/papa-tg/publisher.env ]] || { echo "NO_ACCOUNT"; exit 1; }
( cd /opt/papa/modules/genplan && /opt/papa-venv/razvedka/bin/python -m unittest -q tests/test_genplan.py tests/test_hub_service.py 2>&1 | tail -1 )
( set -a; . /etc/papa-razvedka/telegram.env; set +a; /opt/papa-venv/razvedka/bin/python /opt/papa/ops/frankfurt/genplan_setup.py )
id papa-genplan >/dev/null 2>&1 || useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin papa-genplan
chown -R papa-genplan:papa-genplan /etc/papa-genplan
chgrp papa-genplan /etc/papa-tg /etc/papa-tg/publisher.env && chmod 750 /etc/papa-tg && chmod 640 /etc/papa-tg/publisher.env
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-genplan.service /etc/systemd/system/
systemctl daemon-reload; systemctl enable -q papa-genplan; systemctl restart papa-genplan; sleep 6
echo "papa-genplan: $(systemctl is-active papa-genplan)"
journalctl -u papa-genplan -n 5 -o cat --no-pager
echo "gateway=$(systemctl is-active nexus-private-control-v2) voronka=$(systemctl is-active papa-voronka) mem_free=$(free -m | awk '/Mem/{print $7}')MB"
echo "== GENPLAN_INSTALLED"
