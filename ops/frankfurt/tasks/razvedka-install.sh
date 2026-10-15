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
# отчёт для Pult: читает только шлюз (группа nexus-private-control), файлы наследуют группу
install -d -m 2750 -o papa-razvedka -g nexus-private-control /var/lib/papa-razvedka-pub
systemctl daemon-reload
if [[ -s /etc/papa-razvedka/telegram.env && -s /var/lib/papa-razvedka/razvedka.sqlite3 ]]; then
  systemctl start papa-razvedka@publish.service && journalctl -u papa-razvedka@publish.service -n 3 -o cat --no-pager | grep PUBLISHED || true
fi
echo "gateway=$(systemctl is-active nexus-private-control-v2) connect=$(systemctl is-active nexus-connect) mem_free=$(free -m | awk '/Mem/{print $7}')MB"
echo "== RAZVEDKA_INSTALLED (дальше: papa-update razvedka-login)"
