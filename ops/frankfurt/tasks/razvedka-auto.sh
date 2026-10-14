# Включить ежедневный сбор и отчёт в 06:10 по Ташкенту.
systemctl enable --now papa-razvedka-daily.timer
systemctl list-timers papa-razvedka-daily.timer --no-pager | head -3
