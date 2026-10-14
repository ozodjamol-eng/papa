# Установить Разведку на Франкфурте (без входа в Telegram). Существующие службы не трогаются.
set -Eeuo pipefail
python3 -c 'import tomllib, venv' || { echo "NEED_PYTHON_3_11"; exit 1; }
id papa-razvedka >/dev/null 2>&1 || useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin papa-razvedka
install -d -m 755 /opt/papa-venv
[[ -x /opt/papa-venv/razvedka/bin/python ]] || python3 -m venv /opt/papa-venv/razvedka
/opt/papa-venv/razvedka/bin/pip install -q --upgrade pip
/opt/papa-venv/razvedka/bin/pip install -q -r /opt/papa/modules/razvedka/requirements.txt
echo "telethon $(/opt/papa-venv/razvedka/bin/python -c 'import telethon;print(telethon.__version__)')"
( cd /opt/papa/modules/razvedka && /opt/papa-venv/razvedka/bin/python -m unittest -q tests/test_razvedka.py 2>&1 | tail -1 )
/opt/papa-venv/razvedka/bin/python -c 'from telethon.tl.functions.chatlists import CheckChatlistInviteRequest; print("chatlists API: ok")'
install -d -m 700 /etc/papa-razvedka
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-razvedka@.service /opt/papa/ops/frankfurt/systemd/papa-razvedka-daily.timer /etc/systemd/system/
systemctl daemon-reload
echo "gateway=$(systemctl is-active nexus-private-control-v2) connect=$(systemctl is-active nexus-connect) mem_free=$(free -m | awk '/Mem/{print $7}')MB"
echo "== RAZVEDKA_INSTALLED (дальше: papa-update razvedka-login)"
