"""PAPA ежедневный аудит (протокол docs/AUDIT.md). Сервер проверяет сам, без ИИ; отчёт — в «🎉 КАТТА ДАВРА Пульт».
  full  (02:00 Ташкент) — всё + копия базы GENPLAN; отчёт всегда (короткий, если всё в порядке).
  quick (05:30)         — службы, боты, утро, застрявшие посты; пишет ТОЛЬКО при проблемах.
Только чтение (кроме копии базы и файла last.json). Стандартная библиотека Python."""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import tomllib
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

TZ = dt.timezone(dt.timedelta(hours=5))
REPO = Path("/opt/papa")
GP_DB = Path("/var/lib/papa-genplan/genplan.sqlite3")
GW_DB = Path(os.environ.get("PAPA_AUTOPILOT_GW_DB", "/var/lib/nexus-private-control/control.sqlite3"))
OUT = Path("/var/lib/papa-audit")
BACKUPS = Path("/var/backups/papa")
PY = "/opt/papa-venv/razvedka/bin/python"
SERVICES = ["papa-genplan", "papa-fabrika", "papa-autopilot", "papa-voronka", "nexus-private-control-v2", "nexus-connect", "tailscaled"]
TIMERS = ["papa-curator.timer", "papa-razvedka-daily.timer"]
ERR = re.compile(r"error|ошибк|failed|traceback|exception|не удалось|❌", re.I)


def sh(*cmd: str, timeout: int = 60) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception as e:  # noqa: BLE001
        return f"ERR {type(e).__name__}"


def envf(*paths: str) -> dict:
    out = {}
    for p in paths:
        try:
            for line in Path(p).read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = line.split("=", 1)
                    out[k.strip()] = v.strip().strip('"').strip("'")
        except OSError:
            pass
    return out


def tg(token: str, method: str, **p) -> dict:
    data = urllib.parse.urlencode({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                                   for k, v in p.items()}).encode()
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/{method}", data=data, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read() or b"{}")
        except ValueError:
            return {"ok": False, "description": f"HTTP {e.code}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "description": type(e).__name__}


class Audit:
    def __init__(self):
        self.bad: list[str] = []      # ❌ сломано
        self.warn: list[str] = []     # ⚠️ внимание
        self.info: list[str] = []     # цифры дня

    # ---------- службы ----------
    def services(self):
        for s in SERVICES:
            st = sh("systemctl", "is-active", s)
            if st != "active":
                self.bad.append(f"служба {s}: {st or 'нет'}")
            else:
                n = sh("systemctl", "show", "-p", "NRestarts", "--value", s)
                if n.isdigit() and int(n) >= 3:
                    self.warn.append(f"{s} перезапускалась {n} раз")
        for t in TIMERS:
            if sh("systemctl", "is-active", t) != "active":
                self.bad.append(f"таймер {t} выключен")

    # ---------- боты и права в каналах ----------
    def bots(self, cfg: dict, env: dict):
        main = env.get("GENPLAN_BOT_TOKEN", "")
        ok = 0
        for code, ch in cfg["channels"].items():
            if ch.get("publisher") != "bot" or ch.get("mode") != "live":
                continue
            tok = env.get(ch.get("bot_token_env", ""), "") or main
            me = tg(tok, "getMe")
            if not me.get("ok"):
                self.bad.append(f"бот пульта {ch['title']}: {me.get('description', 'не отвечает')}")
                continue
            m = tg(tok, "getChatMember", chat_id="@" + ch["username"], user_id=me["result"]["id"]).get("result") or {}
            if m.get("status") != "administrator" or not m.get("can_post_messages"):
                self.bad.append(f"@{me['result']['username']} не админ с публикацией в @{ch['username']}")
            else:
                ok += 1
        self.info.append(f"боты-пульты с правами: {ok}")

    # ---------- GENPLAN: публикации, застрявшие, утро ----------
    def genplan(self, cfg: dict, now: dt.datetime, quick: bool):
        if not GP_DB.exists():
            self.bad.append("нет базы GENPLAN")
            return
        db = sqlite3.connect(f"file:{GP_DB}?mode=ro", uri=True, timeout=15)
        db.row_factory = sqlite3.Row
        stuck = db.execute("SELECT channel, count(*) n FROM materials WHERE status='queued' AND scheduled_at IS NOT NULL "
                           "AND scheduled_at < ? GROUP BY channel", ((now - dt.timedelta(minutes=15)).isoformat(),)).fetchall()
        for r in stuck:
            self.bad.append(f"{self.title(cfg, r['channel'])}: {r['n']} пост(а) застряли — время прошло, не вышли")
        day = now.date().isoformat()
        for r in db.execute("SELECT channel, key, status, prepared, approved FROM fixed_posts WHERE day=? AND status='pending'",
                            (day,)).fetchall():
            if not r["prepared"]:
                self.bad.append(f"{self.title(cfg, r['channel'])}: утро «{r['key']}» не подготовлено")
            elif not r["approved"]:
                self.warn.append(f"{self.title(cfg, r['channel'])}: утро «{r['key']}» ждёт ✅")
        if quick:
            return
        since = (now - dt.timedelta(hours=24)).isoformat()
        for code, ch in cfg["channels"].items():
            rows = db.execute("SELECT status, error FROM publications WHERE channel=? AND at>=?", (code, since)).fetchall()
            c = Counter(r["status"] for r in rows)
            fx = Counter(r["status"] for r in db.execute("SELECT status FROM fixed_posts WHERE channel=? AND at>=? AND at<=?",
                                                          (code, since, now.isoformat())))
            line = f"{ch['title']}: вышло {c['done'] + fx['done']}"
            if c["failed"] or fx["failed"]:
                errs = Counter((r["error"] or "")[:60] for r in rows if r["status"] == "failed").most_common(1)
                self.warn.append(f"{ch['title']}: ошибок публикации {c['failed'] + fx['failed']}" + (f" — {errs[0][0]}" if errs else ""))
            q = db.execute("SELECT count(*) FROM materials WHERE channel=? AND status='queued'", (code,)).fetchone()[0]
            self.info.append(line + f" · в очереди {q}")
        tomorrow = (now.date() + dt.timedelta(days=1)).isoformat()
        nt = db.execute("SELECT count(*), sum(prepared), sum(approved) FROM fixed_posts WHERE day=? AND status='pending'",
                        (tomorrow,)).fetchone()
        if nt[0]:
            self.info.append(f"утро завтра: {nt[0]} постов, готово {nt[1] or 0}, одобрено {nt[2] or 0}")
        try:
            ok = db.execute("SELECT count(*) FROM morning_pool WHERE status='ok'").fetchone()[0]
            new = db.execute("SELECT count(*) FROM morning_pool WHERE status='new'").fetchone()[0]
            self.info.append(f"утренние видео: годных {ok}, ждут проверки {new}")
        except sqlite3.Error:
            pass
        cur = db.execute("SELECT count(*), sum(status IN ('queued','published')) FROM materials WHERE source IS NOT NULL "
                         "AND created_at>=?", (since,)).fetchone()
        self.info.append(f"куратор за сутки: прислал {cur[0]}, взято {cur[1] or 0}")
        db.close()

    @staticmethod
    def title(cfg, code):
        return cfg["channels"].get(code, {}).get("title", code)

    # ---------- журналы, автопилот, Лондон, сервер ----------
    def journals(self):
        out = sh("journalctl", "-u", "papa-genplan", "-u", "papa-fabrika", "-u", "papa-autopilot", "-u", "papa-razvedka@*",
                 "--since", "24 hours ago", "--no-pager", "-o", "cat", timeout=90)
        lines = [re.sub(r"\d+", "#", line)[:90] for line in out.splitlines() if ERR.search(line)]
        top = Counter(lines).most_common(3)
        if top:
            self.info.append("частые ошибки в журналах: " + "; ".join(f"{t} ×{n}" for t, n in top))
        if "Gemini" in out and ("429" in out or "лимит" in out):
            self.info.append("Gemini: дневной лимит заканчивался")

    def gateway(self):
        if not GW_DB.exists():
            return
        db = sqlite3.connect(f"file:{GW_DB}?mode=ro", uri=True, timeout=15)
        since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)).isoformat()
        f = db.execute("SELECT count(*) FROM tasks WHERE operation='papa_task' AND status='failed' AND updated_at>=?",
                       (since,)).fetchone()[0]
        n = db.execute("SELECT count(*) FROM tasks WHERE operation='papa_task' AND updated_at>=?", (since,)).fetchone()[0]
        self.info.append(f"автопилот за сутки: задач {n}, с ошибкой {f}")
        r = db.execute("SELECT last_seen FROM devices WHERE id='london'").fetchone()
        if not r or time.time() - r[0] > 600:
            self.warn.append("агент Лондона (GENPLAN 5) молчит больше 10 минут")
        db.close()

    def server(self):
        df = sh("df", "--output=pcent,avail", "-BG", "/").splitlines()[-1].split()
        mem = sh("free", "-m").splitlines()[1].split()
        pct = int(df[0].rstrip("%"))
        (self.bad if pct >= 90 else self.warn if pct >= 80 else self.info).append(f"диск {df[0]}, свободно {df[1]}")
        self.info.append(f"память {mem[2]}/{mem[1]} МБ")

    def backup(self, now: dt.datetime):
        BACKUPS.mkdir(parents=True, exist_ok=True)
        dst = BACKUPS / f"genplan-{now.date().isoformat()}.sqlite3"
        try:
            src = sqlite3.connect(f"file:{GP_DB}?mode=ro", uri=True, timeout=30)
            out = sqlite3.connect(dst)
            src.backup(out)
            out.close()
            src.close()
            os.chmod(dst, 0o600)
            for old in sorted(BACKUPS.glob("genplan-*.sqlite3"))[:-7]:
                old.unlink()
            self.info.append(f"копия базы GENPLAN: {dst.name} ({dst.stat().st_size // 1024} КБ, хранится 7 дней)")
        except Exception as e:  # noqa: BLE001
            self.bad.append(f"копия базы не сделалась: {type(e).__name__}")

    def tests(self):
        res = []
        for mod, extra in (("genplan", {"POOL_VISION_GAP": "0"}), ("razvedka", {})):
            env = {**os.environ, **extra, "PAPA_GENPLAN_STATE": sh("mktemp", "-d")}
            p = subprocess.run([PY, "-m", "unittest", "discover", "-q", "-s", "tests"], cwd=REPO / "modules" / mod,
                               capture_output=True, text=True, env=env, timeout=300)
            ran = re.search(r"Ran (\d+)", p.stderr)
            if p.returncode != 0:
                self.bad.append(f"автотесты {mod} не прошли: {p.stderr.strip().splitlines()[-1][:80] if p.stderr.strip() else '?'}")
            res.append(f"{mod} {ran.group(1) if ran else '?'}")
        self.info.append("автотесты: " + ", ".join(res) + (" ✅" if not any("автотесты" in b for b in self.bad) else ""))

    def text(self, quick: bool, now: dt.datetime) -> str:
        head = f"🩺 Аудит PAPA · {now:%d.%m %H:%M}" + (" (утренняя проверка)" if quick else "")
        if not self.bad and not self.warn:
            head += "\n✅ Всё в порядке"
        else:
            head += f"\n{'❌' if self.bad else '⚠️'} Проблем: {len(self.bad)} · внимание: {len(self.warn)}"
        parts = [head]
        if self.bad:
            parts.append("\n".join("❌ " + x for x in self.bad))
        if self.warn:
            parts.append("\n".join("⚠️ " + x for x in self.warn))
        if self.info and not quick:
            parts.append("\n".join("• " + x for x in self.info))
        if self.bad:
            parts.append("Чиню сам через автопилот, что можно; ваше — напишу отдельно.")
        return "\n\n".join(parts)


# ---------- протоколы «Охрана каналов» и «Тихий канал» (каждый час 07–23) ----------
RIGHTS = ("can_change_info", "can_post_messages", "can_edit_messages", "can_delete_messages", "can_invite_users",
          "can_restrict_members", "can_promote_members", "can_manage_chat", "can_pin_messages")
SILENT_H = 3


def admins_snapshot(token: str, chat: str) -> dict | None:
    r = tg(token, "getChatAdministrators", chat_id=chat)
    if not r.get("ok"):
        return None
    out = {}
    for m in r["result"]:
        u = m["user"]
        name = ("@" + u["username"]) if u.get("username") else (u.get("first_name") or str(u["id"]))
        out[str(u["id"])] = {"name": name, "status": m["status"], "rights": sorted(k for k in RIGHTS if m.get(k))}
    return out


def admin_changes(old: dict, new: dict) -> list[str]:
    msgs = []
    for uid, a in new.items():
        if uid not in old:
            msgs.append(f"новый админ {a['name']} ({', '.join(a['rights']) or 'без прав'})")
        elif old[uid]["rights"] != a["rights"] or old[uid]["status"] != a["status"]:
            added = set(a["rights"]) - set(old[uid]["rights"])
            msgs.append(f"у {a['name']} изменились права" + (f": +{', '.join(sorted(added))}" if added else ""))
    for uid, a in old.items():
        if uid not in new:
            msgs.append(f"снят админ {a['name']}")
    return msgs


def watch(cfg: dict, env: dict, now: dt.datetime, state: dict) -> list[str]:
    alerts = []
    tok = env.get("GENPLAN_BOT_TOKEN", "")
    adm = state.setdefault("admins", {})
    for code, ch in cfg["channels"].items():
        chat = "@" + ch["username"]
        snap = admins_snapshot(tok, chat)
        if snap is None:
            if not state.setdefault("admin_unreadable", {}).get(code):
                state["admin_unreadable"][code] = 1
                alerts.append(f"🛡 {ch['title']}: бот не видит список админов — охрана для него не работает")
            continue
        if code in adm:
            for m in admin_changes(adm[code], snap):
                alerts.append(f"🚨 {ch['title']}: {m}. Если это не вы — срочно проверьте админов канала!")
        adm[code] = snap
    if not (dt.time(9, 0) <= now.time() <= dt.time(22, 0)) or not GP_DB.exists():
        return alerts
    db = sqlite3.connect(f"file:{GP_DB}?mode=ro", uri=True, timeout=15)
    sil = state.setdefault("silent", {})
    for code, ch in cfg["channels"].items():
        if ch.get("mode") != "live" or ch.get("publisher") != "bot":
            continue
        last = max([r[0] for r in db.execute("SELECT max(at) FROM publications WHERE channel=? AND status='done'", (code,))
                    if r[0]] + [r[0] for r in db.execute("SELECT max(at) FROM fixed_posts WHERE channel=? AND status='done'", (code,))
                                if r[0]] or [""])
        if not last:
            continue
        gap = (now - dt.datetime.fromisoformat(last).astimezone(TZ)).total_seconds() / 3600
        if gap >= SILENT_H and sil.get(code) != last:
            sil[code] = last
            alerts.append(f"🔇 {ch['title']}: тишина {gap:.0f} ч (последний пост {dt.datetime.fromisoformat(last).astimezone(TZ):%H:%M}). "
                          "Загляните в пульт (📅 СЕГОДНЯ) или напишите мне «тишина» — разберу.")
    db.close()
    return alerts


def main(mode: str = "full", send: bool = True) -> int:
    quick = mode == "quick"
    now = dt.datetime.now(TZ)
    cfg = tomllib.loads((REPO / "modules/genplan/config.toml").read_text(encoding="utf-8"))
    env = envf("/etc/papa-genplan/genplan.env", "/etc/papa-genplan/bots.env")
    if mode == "watch":
        OUT.mkdir(parents=True, exist_ok=True)
        sp = OUT / "watch.json"
        try:
            state = json.loads(sp.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            state = {}
        alerts = watch(cfg, env, now, state)
        sp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        print("\n".join(alerts) or "watch: всё спокойно")
        if send and alerts:
            for o in env.get("OWNER_IDS", "").split(","):
                if o.strip():
                    tg(env.get("GENPLAN_BOT_TOKEN", ""), "sendMessage", chat_id=o.strip(), text="\n\n".join(alerts)[:4000])
        return 0
    a = Audit()
    steps = [a.services, lambda: a.bots(cfg, env), lambda: a.genplan(cfg, now, quick)]
    if not quick:
        steps += [a.journals, a.gateway, a.server, lambda: a.backup(now), a.tests]
    for step in steps:
        try:
            step()
        except Exception as e:  # noqa: BLE001 — одна проверка не роняет аудит
            a.warn.append(f"проверка не выполнилась: {type(e).__name__}: {str(e)[:80]}")
    msg = a.text(quick, now)
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"last-{mode}.json").write_text(json.dumps({"at": now.isoformat(), "bad": a.bad, "warn": a.warn, "info": a.info},
                                                      ensure_ascii=False), encoding="utf-8")
    if send and (not quick or a.bad):
        for o in env.get("OWNER_IDS", "").split(","):
            if o.strip():
                tg(env.get("GENPLAN_BOT_TOKEN", ""), "sendMessage", chat_id=o.strip(), text=msg[:4000], disable_web_page_preview=True)
    return 1 if a.bad else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    sys.exit(main(args[0] if args else "full", "--no-send" not in args))
