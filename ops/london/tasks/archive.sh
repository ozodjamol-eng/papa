# Фаза 0, этап 2: упаковать старое в архив и отключить старые службы.
# Оригиналы НЕ удаляются (это отдельная задача archive-purge через неделю).
# GENPLAN 5, боты, базы, старый NEXUS — не трогаются.
set -Eeuo pipefail
A=/var/backups/papa-archive; TS=$(date +%Y%m%d_%H%M); OUT=$A/old-genplan-$TS.tar.gz
install -d -m 700 $A
LIST=$(mktemp)
for p in /opt/xojaobod-autopost /opt/xojaobod-genplan-v3 /root/gp2_final_stage /root/gp2_menu_stage /root/genplan_v2_manual_stage \
         /opt/xojaobod-genplan-v5/data/genplan_v3.db \
         /etc/systemd/system/xojaobod-autopost.service /etc/systemd/system/xojaobod-maintenance.service \
         /etc/systemd/system/xojaobod-genplan-v3.service.bak_v5_20260924; do
  [[ -e $p ]] && echo "$p" >> "$LIST"
done
# старые копии баз GENPLAN 5: всё, кроме 3 самых свежих
ls -1dt /opt/xojaobod-genplan-v5/backups/* 2>/dev/null | tail -n +4 >> "$LIST" || true
echo "в архив: $(wc -l < "$LIST") объектов, $(du -shc $(cat "$LIST") 2>/dev/null | tail -1 | cut -f1)"
tar -czf "$OUT" --absolute-names -T "$LIST"
chmod 600 "$OUT"
tar -tzf "$OUT" > /dev/null && echo "архив проверен: $OUT ($(du -h "$OUT" | cut -f1))"
cp "$LIST" "$A/old-genplan-$TS.list"; sha256sum "$OUT" > "$OUT.sha256"; rm -f "$LIST"
# старые службы: выключить автозапуск (файлы остаются, включить обратно — systemctl enable)
for s in xojaobod-autopost xojaobod-maintenance; do
  if systemctl list-unit-files "$s.service" --no-legend | grep -q .; then
    systemctl disable --now "$s" 2>/dev/null || true
    echo "$s: $(systemctl is-enabled $s 2>/dev/null || true) / $(systemctl is-active $s 2>/dev/null || true)"
  fi
done
echo "genplan=$(systemctl is-active xojaobod-genplan-v3) city24=$(systemctl is-active xojaobodcity24bot) goldwater=$(systemctl is-active goldwater-bot)"
echo "== ARCHIVE_DONE (оригиналы на месте; удалить их — через неделю: papa-update archive-purge)"
