# Главный канал Katta Davra (бывший @XOJAOBODLIKLARIMIZ): название, юзернейм, описание, боты, ссылка панели, папка.
set -Eeuo pipefail
set -a; . /etc/papa-razvedka/telegram.env; set +a
/opt/papa-venv/razvedka/bin/python /opt/papa/ops/frankfurt/davra_setup.py
