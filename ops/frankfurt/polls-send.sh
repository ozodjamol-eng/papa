#!/usr/bin/env bash
# 🗳 Опросы (31.10, владелец: «чаще делать такие опросы»): вт / чт / сб в 19:00 Ташкент сервер присылает владельцу
# в PAPA ШТАБ готовый пост дня (карточка + жирная подпись + опрос) из ops/frankfurt/polls/<дата>/ — он пересылает
# в группу «без имени отправителя». Один раз в день (отметка в /var/lib/papa-polls). Нет поста на сегодня — тишина.
set -Eeuo pipefail
DAY=$(TZ=Asia/Tashkent date +%F)
MARK=/var/lib/papa-polls/$DAY.sent
mkdir -p /var/lib/papa-polls
[[ -e "$MARK" && "${1:-}" != "--force" ]] && { echo "уже отправлено сегодня"; exit 0; }
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
git -C /opt/papa fetch -q origin main
git -C /opt/papa archive FETCH_HEAD "ops/frankfurt/polls/$DAY" 2>/dev/null | tar -x -C "$T" 2>/dev/null || { echo "на $DAY опроса нет"; exit 0; }
set -a; . /etc/papa-genplan/genplan.env; [ -f /etc/papa-genplan/bots.env ] && . /etc/papa-genplan/bots.env; set +a
python3 -I /opt/papa/ops/frankfurt/deliver.py "$T/ops/frankfurt/polls/$DAY" && touch "$MARK"
