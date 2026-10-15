# НЕОБРАТИМО (утверждено владельцем): удалить старое, что уже в архиве или не нужно новой архитектуре.
# GENPLAN 5 (код, рабочая база, свежие медиа), боты, PostgreSQL — не трогаются.
set -Euo pipefail
before=$(df -B1 / | awk 'NR==2{print $4}')
ARC=$(ls -1t /var/backups/papa-archive/old-genplan-*.tar.gz 2>/dev/null | head -1)
if [[ -n "$ARC" ]] && tar -tzf "$ARC" >/dev/null 2>&1; then
  # оригиналы того, что уже лежит в проверенном архиве
  while read -r p; do [[ -e "$p" ]] && rm -rf -- "$p"; done < "${ARC%.tar.gz}.list"
  echo "удалены оригиналы из архива $(basename "$ARC")"
else echo "архив не найден или повреждён — оригиналы НЕ удаляются"; fi
# медиа старого конвейера NEXUS → GENPLAN старше 7 дней (свежие остаются для постов в очереди)
for d in /opt/xojaobod-genplan-v5/data/nexus_handoff /opt/xojaobod-genplan-v5/data/intelligence_media /opt/xojaobod-genplan-v5/data/branding_tmp; do
  [[ -d "$d" ]] && find "$d" -type f -mtime +7 -delete && find "$d" -mindepth 1 -type d -empty -delete && echo "очищено (старше 7 дней): $d → $(du -sh "$d" | cut -f1)"
done
# старые резервные копии старого NEXUS (оставить 3 последних)
ls -1dt /opt/nexus/backups/* 2>/dev/null | tail -n +4 | xargs -r rm -rf --
after=$(df -B1 / | awk 'NR==2{print $4}')
echo "освобождено: $(( (after-before)/1048576 )) МБ; диск: $(df -h / | awk 'NR==2{print "занято "$5", свободно "$4}')"
echo "genplan=$(systemctl is-active xojaobod-genplan-v3) city24=$(systemctl is-active xojaobodcity24bot) goldwater=$(systemctl is-active goldwater-bot)"
echo "== PURGE_DONE"
