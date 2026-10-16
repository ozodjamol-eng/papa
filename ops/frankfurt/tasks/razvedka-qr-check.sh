#!/usr/bin/env bash
# ТОЛЬКО ЧТЕНИЕ: есть ли вход Разведки под аккаунтом PAPA (после razvedka-qr). Секреты не выводит.
F=/etc/papa-razvedka/telegram-papa.env
if [[ -s $F ]]; then echo "файл: есть, изменён $(date -r $F '+%F %H:%M')"; echo "аккаунт: @$(grep -E '^PAPA_TG_USERNAME=' $F | cut -d= -f2) (id $(grep -E '^PAPA_TG_USER_ID=' $F | cut -d= -f2))"
else echo "файла нет — вход по QR ещё не сделан"; fi
echo "== RAZVEDKA_QR_CHECK_DONE"
