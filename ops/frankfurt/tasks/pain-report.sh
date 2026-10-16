#!/usr/bin/env bash
# 💡 «Боль аудитории»: сколько комментариев собрано и сколько среди них полезных (читает только базу).
set -Eeuo pipefail
systemctl start papa-razvedka@pain-report.service
journalctl -u papa-razvedka@pain-report.service -n 40 -o cat --no-pager
