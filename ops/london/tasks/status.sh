# Быстрая проверка Лондона (только чтение)
echo "диск: $(df -h / | awk 'NR==2{print "занято "$5", свободно "$4}') | память: $(free -m | awk '/Mem/{print $3"/"$2" МБ"}')"
for s in xojaobod-genplan-v3 xojaobodcity24bot goldwater-bot nginx postgresql nexus-london-agent nexus-mcp; do printf '%-24s %s\n' "$s" "$(systemctl is-active $s 2>/dev/null)"; done
