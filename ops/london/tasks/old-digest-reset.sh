#!/usr/bin/env bash
# 30.10: старый «Кечки дайжест» Лондона (заменён дайжестом PAPA с 18.10) висит в статусе failed и засоряет проверки.
# Только снимаем отметку failed и выключаем его таймер, если он есть. Файлы не удаляются; GENPLAN, боты, базы не трогаются.
set -uo pipefail
U=xojaobod-evening-digest
systemctl disable --now "$U.timer" 2>/dev/null && echo "таймер $U.timer выключен" || echo "таймера $U.timer нет"
systemctl reset-failed "$U.service" 2>/dev/null || true
echo "$U: $(systemctl is-active $U.service)"
echo "city24=$(systemctl is-active xojaobodcity24bot) goldwater=$(systemctl is-active goldwater-bot) agent=$(systemctl is-active nexus-london-agent)"
echo "откат: systemctl enable --now $U.timer"
echo "== OLD_DIGEST_RESET_DONE"
