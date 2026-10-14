echo "диск: $(df -h / | awk 'NR==2{print "занято "$5", свободно "$4}') | память: $(free -m | awk '/Mem/{print $3"/"$2" МБ"}')"
for s in nexus-private-control-v2 nexus-connect tailscaled papa-razvedka-daily.timer; do printf '%-28s %s\n' "$s" "$(systemctl is-active $s 2>/dev/null)"; done
