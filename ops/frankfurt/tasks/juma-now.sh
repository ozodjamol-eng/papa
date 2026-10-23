#!/usr/bin/env bash
# 🕌 Разовый пятничный перевыпуск (23.10, приказ владельца): «Жума муборак» в Хўжаобод City 24 и PaparazziUZ.
# Видео «Жума» — то же, что утром вышло в КАТТА ДАВРА (свой водяной знак каждого канала), текст — пятничный шаблон владельца.
# Утренние строки greeting этих двух каналов за сегодня ставятся заново через ~10 мин; старые посты остаются как есть.
# Выходит само (утро = протокол), в боте — предпросмотр с 🗑. Откат: 🗑 в предпросмотре.
set -euo pipefail
PY=/opt/papa-venv/razvedka/bin/python
DB=/var/lib/papa-genplan/genplan.sqlite3
cp -a "$DB" "$DB.bak-juma-$(date +%F-%H%M)"
set -a; . /etc/papa-genplan/genplan.env; set +a
sudo -u papa-genplan --preserve-env=GENPLAN_BOT_TOKEN,HUB_CHAT_ID,OWNER_IDS $PY - "$DB" <<'PY'
import datetime as dt, os, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, "/opt/papa/modules/genplan")
from genplan import morning as M, media, store, plan
from genplan.__main__ import cfg
from genplan.fabrika import upload_video
C = cfg()
db = store.connect(sys.argv[1])
now = dt.datetime.now(plan.TZ)
day = now.date()
assert day.weekday() == 4, "сегодня не пятница"
src = None
d = db.execute("SELECT source FROM fixed_posts WHERE channel='davra' AND day=? AND key='greeting'", (day.isoformat(),)).fetchone()
if d and (d["source"] or "").startswith("pool:"):
    p = db.execute("SELECT * FROM morning_pool WHERE key=?", (d["source"][5:],)).fetchone()
    if p and (M.pool_dir() / p["file"]).exists():
        src = M.pool_dir() / p["file"]
if src is None:
    for p in db.execute("SELECT * FROM morning_pool WHERE status='ok' AND weekday='Жума' ORDER BY quality DESC, views DESC"):
        if (M.pool_dir() / p["file"]).exists():
            src = M.pool_dir() / p["file"]; break
print("видео Жума:", src)
assert src is not None, "в запасе нет файла видео «Жума»"
BODY = {
 "xojaobod": "🕌 Ассалому алайкум ва раҳматуллоҳи ва барокатуҳ!\n\n📅 Бугун, {date}\n🤲 ЖУМА МУБОРАК БЎЛСИН, {address}!\n\n🌙 Ҳафтанинг энг табаррук куни — дуолар ижобат бўладиган, барака ва раҳмат ёғиладиган кун. Шу муборак кун ҳурматидан Аллоҳ барчамизни мағфират қилсин!\n\n✨ Хонадонларимизга тинчлик, яқинларимизга саломатлик, дастурхонимизга барака берсин!\n\n💫 Ризқингиз кенг, ҳар бир босган қадамингиз тавфиқли, тавбаларингиз қабул, дуоларингиз ижобат бўлсин!\n\n🕊 Аллоҳ паноҳида бўлинг!",
 "paparazzi": "🕌 ЖУМА МУБОРАК, {address}!\n\nАссалому алайкум ва раҳматуллоҳи ва барокатуҳ!\n📅 Бугун, {date} — ҳафтанинг энг табаррук куни.\n\n🤲 Аллоҳим, шу муборак Жума ҳурматидан дуоларимизни ижобат, тавбаларимизни қабул айлагин. Қалбимизга хотиржамлик, хонадонимизга файзу барака бергин!\n\n✨ Кўнглингиздаги эзгу ниятларингиз ушалсин, бугун сизни фақат хушхабарлар кутиб турсин!\n\n🕊 Аллоҳ паноҳида бўлинг!",
}
date = f"{day.day} {M.MONTHS_UZ[day.month - 1]}"
at = (now + dt.timedelta(minutes=10)).replace(second=0, microsecond=0)
work = Path(tempfile.mkdtemp(prefix="juma-"))
try:
    for i, chn in enumerate(("xojaobod", "paparazzi")):
        ch = C["channels"][chn]
        o = {**M.opts(ch), "tag": "#ЖУМА_МУБОРАК"}
        r = db.execute("SELECT * FROM fixed_posts WHERE channel=? AND day=? AND key='greeting'", (chn, day.isoformat())).fetchone()
        assert r, f"нет утренней строки {chn}"
        body = BODY[chn].format(date=date, address=(ch.get("morning") or {}).get("address", "азизлар"))
        cap = M.greeting_caption(ch, o, day, body)
        logo = media.text_logo("@" + ch["username"], work / f"wm-{chn}.png")
        out = media.watermark_video(src, logo, work / f"out-{chn}.mp4", style="rise")
        res = upload_video(os.environ["GENPLAN_BOT_TOKEN"], int(os.environ["HUB_CHAT_ID"]), out, cap)
        if ch.get("bot_token_env"):
            keep = M.own_file(r["id"]); keep.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(out, keep)
        t = at + dt.timedelta(minutes=5 * i)
        M.update(db, r["id"], status="pending", at=t.isoformat(), text=cap, hub_msg=int(res["message_id"]),
                 source="juma:" + src.name, prepared=1, approved=1, redo=0, tries=0, next_try=None,
                 error=None, message_id=None, preview_sent=0)
        print(f"  {ch['title']}: выйдет в {t:%H:%M}\n---\n{cap}\n---")
finally:
    shutil.rmtree(work, ignore_errors=True)
PY
echo "== JUMA_NOW_DONE"
