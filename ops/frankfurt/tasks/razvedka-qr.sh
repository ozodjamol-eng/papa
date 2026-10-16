#!/usr/bin/env bash
# Франкфурт, ТОЛЬКО ВЛАДЕЛЕЦ В КОНСОЛИ: вход Разведки под рабочим аккаунтом PAPA (@papa_admin_uz) по QR.
# Сканировать в Telegram аккаунта PAPA: Настройки → Устройства → «Подключить устройство».
# Сохраняется ОТДЕЛЬНО (telegram-papa.env); Разведка пока работает как раньше — переключение отдельным шагом,
# после переноса папок и подписок. Основной профиль владельца не трогается.
set -Eeuo pipefail
/opt/papa-venv/razvedka/bin/python -c 'import qrcode' 2>/dev/null || /opt/papa-venv/razvedka/bin/pip install -q qrcode
/opt/papa-venv/razvedka/bin/python /opt/papa/ops/frankfurt/tg_account_qr.py /etc/papa-razvedka/telegram-papa.env "PAPA Razvedka"
chmod 600 /etc/papa-razvedka/telegram-papa.env
u=$(grep -E '^PAPA_TG_USERNAME=' /etc/papa-razvedka/telegram-papa.env | cut -d= -f2)
[[ "$u" == "papa_admin_uz" ]] && echo "аккаунт: @$u — верно" || echo "⚠️ вошёл аккаунт @${u:-?}, а нужен @papa_admin_uz — сообщите Claude"
echo "== RAZVEDKA_QR_DONE"
