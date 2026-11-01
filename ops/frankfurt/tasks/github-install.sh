#!/usr/bin/env bash
# 🧭 GitHub-разведка (18.10) + 🆕 Новинки (28.10) + 🎓 Уроки мастеров (01.11): тесты → таймер (понедельник 10:00 Ташкент) → первый отчёт сейчас в «PAPA ОТЧЁТЫ».
# Только GitHub Search API (бесплатно) + оценка Haiku (ключ уже есть: /etc/papa-genplan/ai.env). Ничего не ставит с GitHub, каналы не трогает.
# Расход: ≈ 0,01–0,03 $ за отчёт (~0,1 $ в месяц). Откат: systemctl disable --now papa-github.timer
set -Eeuo pipefail
PY=/opt/papa-venv/razvedka/bin/python
echo "1/3 тесты:"
# 01.11: тесты изолированно, как в аудите (без сети, ключей и боевых флагов) — иначе падают от живого окружения
( cd /opt/papa/modules/razvedka && env -u GEMINI_API_KEY -u ANTHROPIC_API_KEY -u GITHUB_TOKEN \
    PAPA_GENPLAN_STATE="$(mktemp -d)" PAPA_GEMINI_DIR="$(mktemp -d)" PAPA_GEMINI_SAVER_FILES= \
    HTTP_PROXY=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 http_proxy=http://127.0.0.1:9 https_proxy=http://127.0.0.1:9 \
    timeout 280 $PY -m unittest discover -q -s tests 2>&1 | tail -1 )
echo "2/3 таймер:"
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-razvedka@.service /opt/papa/ops/frankfurt/systemd/papa-github.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable -q --now papa-github.timer
echo "  таймер: $(systemctl list-timers papa-github.timer --no-pager --no-legend 2>/dev/null | cut -c1-40 || true)"
echo "3/3 первый отчёт (1–2 минуты):"
U=papa-razvedka@github-auto.service
systemctl start --no-block "$U"; sleep 2
journalctl -u "$U" -f -n 0 -o cat & J=$!
while systemctl is-active -q "$U" || [[ "$(systemctl show -p ActiveState --value "$U")" == activating ]]; do sleep 3; done
sleep 1; kill $J 2>/dev/null || true
echo "результат: $(systemctl show -p Result --value "$U")"
echo "== GITHUB_INSTALL_DONE"
