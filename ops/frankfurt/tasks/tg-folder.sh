# Создать (или показать) ссылку-папку «PAPA»: Хўжаобод Сити 24 + PaparazziUZ — вступление в оба канала одним нажатием.
set -Eeuo pipefail
[[ -s /etc/papa-razvedka/telegram.env ]] || { echo "NO_LOGIN"; exit 1; }
set -a; . /etc/papa-razvedka/telegram.env; set +a
/opt/papa-venv/razvedka/bin/python /opt/papa/ops/frankfurt/tg_folder.py
