# Фаза 0: безопасная уборка Лондона. GENPLAN, боты, базы, NEXUS — не трогаются и не перезапускаются.
set -Eeuo pipefail
before=$(df -B1 / | awk 'NR==2{print $4}')
echo "до:    $(df -h / | awk 'NR==2{print "занято "$5", свободно "$4}')"
# 1. системные журналы: сжать до 300 МБ и закрепить лимит
journalctl --vacuum-size=300M -q || true
install -d /etc/systemd/journald.conf.d
printf '[Journal]\nSystemMaxUse=300M\n' > /etc/systemd/journald.conf.d/papa-limit.conf
systemctl restart systemd-journald
# 2. кэши загрузчиков (восстанавливаются сами при следующей установке)
rm -rf /root/.npm/_cacache /root/.cache/pip
# 3. пустой файл-мусор в корне GENPLAN 5 (удаляется, только если размер 0)
F=/opt/xojaobod-genplan-v5/genplan_v3_production.db
if [[ -f "$F" && ! -s "$F" ]]; then rm -f "$F"; echo "удалён пустой $F"; fi
after=$(df -B1 / | awk 'NR==2{print $4}')
echo "после: $(df -h / | awk 'NR==2{print "занято "$5", свободно "$4}')  (+$(( (after-before)/1048576 )) МБ)"
echo "журналы: $(journalctl --disk-usage | grep -o '[0-9.]*[KMG]')"
echo "genplan=$(systemctl is-active xojaobod-genplan-v3) city24=$(systemctl is-active xojaobodcity24bot) goldwater=$(systemctl is-active goldwater-bot) nginx=$(systemctl is-active nginx) agent=$(systemctl is-active nexus-london-agent)"
echo "== CLEANUP_DONE"
