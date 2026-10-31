"""PAPA ежедневный аудит (протокол docs/AUDIT.md). Сервер проверяет сам, без ИИ; отчёт — в «🎉 КАТТА ДАВРА Пульт».
  full  (02:00 Ташкент) — всё + копия базы GENPLAN; отчёт всегда (короткий, если всё в порядке).
  quick (04:30)         — службы, боты, утро, застрявшие посты; пишет ТОЛЬКО при проблемах.
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
SERVICES = ["papa-genplan", "papa-fabrika", "papa-autopilot", "papa-voronka", "papa-shodiyona", "nexus-private-control-v2", "nexus-connect", "tailscaled"]
TIMERS = ["papa-curator.timer", "papa-razvedka-daily.timer"]
ERR = re.compile(r"error|ошибк|failed|traceback|exception|не удалось|❌", re.I)


STUCK_DRIFT = dt.timedelta(minutes=75)   # 30.10 №14: переносы дольше (час сетки + тихое окно Жумы) — пост застрял


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


SELF_RESTART = {"papa-autopilot"}
REPORTS_ENV = ("/etc/papa-test/bot.env", "/etc/papa-reports.env")   # бот отчётов + id канала «PAPA ОТЧЁТЫ»


def report_token(env: dict) -> str:
    """23.10 владелец: отчёты и тревоги — в главный пульт PAPA ШТАБ; не подключён — главный бот, как раньше."""
    return env.get("SHTAB_BOT_TOKEN") or env.get("GENPLAN_BOT_TOKEN", "")


def deliver(env: dict, text: str, urgent: bool, send=None) -> list[str]:
    """20.10 владелец: отчёты — прямо в бот (главный пульт), отдельных каналов не нужно.
    Пульт не принял — запасной путь: бот отчётов в «PAPA ОТЧЁТЫ», чтобы не потерялось. Возвращает, куда ушло."""
    send = send or tg
    went = []
    for o in env.get("OWNER_IDS", "").split(","):
        if o.strip() and send(report_token(env), "sendMessage", chat_id=o.strip(), text=text[:4000],
                              disable_web_page_preview=True).get("ok"):
            went.append("pult")
    if not went:
        rep = envf(*REPORTS_ENV)
        tok, chan = rep.get("PAPA_TEST_BOT_TOKEN", ""), rep.get("PAPA_REPORTS_CHANNEL_ID", "")
        if tok and chan and send(tok, "sendMessage", chat_id=chan, text=text[:4000], disable_web_page_preview=True).get("ok"):
            went.append("reports")
    return went


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
                if s in SELF_RESTART:                 # 19.10: автопилот сам перезапускается после каждого обновления кода — это норма
                    continue
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
            # 22.10 аудит: тесты не должны ходить в сеть и тратить боевые ключи (раньше зависали > 300 с).
            for k in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "GITHUB_TOKEN"):
                env.pop(k, None)
            env.update({"HTTP_PROXY": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9",
                        "http_proxy": "http://127.0.0.1:9", "https_proxy": "http://127.0.0.1:9", "NO_PROXY": "", "no_proxy": "",
                        # 31.10: тесты не читают боевые счётчик и флаг экономии Gemini (иначе вечером падали «страж»)
                        "PAPA_GEMINI_DIR": sh("mktemp", "-d"), "PAPA_GEMINI_SAVER_FILES": ""})
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
        snap = admins_snapshot(env.get(ch.get("bot_token_env", ""), "") or tok, chat)   # свой бот канала видит своих админов
        if snap is None:
            if state.setdefault("admin_unreadable", {}).get(code) != now.date().isoformat():   # 20.10: напоминать раз в день, а не один раз навсегда
                state["admin_unreadable"][code] = now.date().isoformat()
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


# ================= 🛡 СТРАЖ (20.10, владелец: «сделай раз и навсегда, чтобы был порядок») =================
# Каждые 10 минут 05:00–23:00: может ли каждый публикующий писать в свой канал, жив ли ключ ИИ,
# не застряла ли реклама/пост. Сломалось — СРАЗУ сообщение владельцу; что можно починить само — чинится
# (права PAPA в группе — задача xojaobod-admin с кнопкой владельца). Повтор напоминания, пока не исправлено.
AI_ENV = "/etc/papa-genplan/ai.env"
REPEAT = {"rights": 2 * 3600, "ai": 12 * 3600, "post": 10 ** 9, "heal": 2 * 3600, "voronka": 3 * 3600,
          "unit": 6 * 3600, "saver": 10 ** 9}
# 24.10 владелец: воронка молчала 2,5 суток (токен Instagram сбросился после смены пароля) — никто не заметил.
VORONKAS = {"@paparazzi.uz": Path("/var/lib/papa-voronka/voronka.sqlite3"),
            "GOLD WATER": Path("/var/lib/papa-voronka/goldwater.sqlite3"),
            "Shodiyona": Path("/var/lib/papa-voronka/shodiyona.sqlite3")}
VORONKA_UNITS = {"@paparazzi.uz": "papa-voronka", "GOLD WATER": "papa-voronka-goldwater",
                 "Shodiyona": "papa-voronka-shodiyona"}
VORONKA_STALE_MIN = 15          # проход раз в 2 минуты; 15 минут тишины = воронка стоит


def voronka_last(db_path: Path) -> dt.datetime | None:
    """Время последнего успешного прохода воронки (None — базы нет/не прочитать)."""
    if not db_path.exists():
        return None
    try:
        c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
        r = c.execute("SELECT v FROM kv WHERE k='last_run'").fetchone()
        c.close()
        return dt.datetime.fromisoformat(r[0][:19]).replace(tzinfo=dt.timezone.utc) if r else None
    except (sqlite3.Error, ValueError):
        return None


def unit_enabled(name: str) -> bool:
    """27.10: воронку, выключенную владельцем (systemctl disable), страж не трогает — это не авария."""
    unit = VORONKA_UNITS.get(name)
    if not unit:
        return True
    try:
        r = subprocess.run(["systemctl", "is-enabled", unit], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() in ("enabled", "enabled-runtime")
    except (subprocess.SubprocessError, OSError):
        return True


def voronka_guard(now: dt.datetime, state: dict, dbs: dict = VORONKAS, last=voronka_last,
                  enabled=unit_enabled) -> list[str]:
    alerts, t = [], now.timestamp()
    for name, path in dbs.items():
        if not enabled(name):
            state.setdefault("guard_seen", {}).pop(f"voronka:{name}", None)
            continue
        lr = last(path)
        if lr is None:
            continue
        key = f"voronka:{name}"
        paused = state.setdefault("guard_paused", {})
        mins = int((now - lr).total_seconds() // 60)
        if mins > VORONKA_STALE_MIN and name in paused:
            continue                                  # сам поставил на паузу и уже сообщил — ждём новый токен
        if mins > VORONKA_STALE_MIN:
            # 27.10 рецепт: умер токен Instagram → пауза (не долбить Instagram ошибками) и одна понятная просьба владельцу
            unit = VORONKA_UNITS.get(name)
            if unit and token_dead(unit):
                stop(unit)
                paused[name] = t
                state.setdefault("guard_seen", {})[key] = t
                alerts.append(f"🛠 Воронка {name}: токен Instagram больше не действует (сменили пароль?). "
                              f"Поставил на паузу сам. Новый токен — на Франкфурте: papa-update {TOKEN_TASK.get(name, 'voronka-token')}")
                continue
            if due(state, key, "voronka", t):
                alerts.append(f"🚨 Воронка {name} СТОИТ уже {mins // 60} ч {mins % 60} мин — комментарии остаются без ответа. "
                              "Чаще всего слетел токен Instagram (смена пароля). Проверка: papa-update voronka-status")
        elif ok_again(state, key):
            state.setdefault("guard_paused", {}).pop(name, None)
            alerts.append(f"✅ Воронка {name} снова работает")
    return alerts


TOKEN_TASK = {"@paparazzi.uz": "voronka-token", "GOLD WATER": "goldwater-voronka-token", "Shodiyona": "shodiyona-voronka-token"}


def token_dead(unit: str) -> bool:
    out = sh("journalctl", "-u", unit, "--since", "1 hour ago", "--no-pager", "-o", "cat", timeout=30)
    return "Error validating access token" in out or "session has been invalidated" in out


def stop(unit: str) -> None:
    sh("systemctl", "stop", unit, timeout=60)        # enabled остаётся: новый токен (задача *-token) сам её запустит


# 27.10 рецепт: упавшая служба — сам перезапуск, не больше 2 раз за 6 часов; не поднялась — зовём владельца
UNITS = ["papa-genplan", "papa-fabrika", "papa-shodiyona", "papa-xotira", "papa-assistant",
         "papa-voronka", "papa-voronka-goldwater", "papa-voronka-shodiyona"]
UNIT_TRIES = 2


def unit_state(unit: str) -> tuple[bool, bool]:
    """(включена в автозапуск, работает)."""
    en = sh("systemctl", "is-enabled", unit, timeout=10) in ("enabled", "enabled-runtime")
    return en, sh("systemctl", "is-active", unit, timeout=10) == "active"


def unit_guard(now: dt.datetime, state: dict, units=UNITS, st=unit_state, restart=None) -> list[str]:
    restart = restart or (lambda u: sh("systemctl", "restart", u, timeout=90))
    alerts, t = [], now.timestamp()
    tries = state.setdefault("unit_tries", {})
    skip = {VORONKA_UNITS[n] for n in state.get("guard_paused", {}) if n in VORONKA_UNITS}
    for u in units:
        if u in skip:
            continue
        en, up = st(u)
        if not en:
            continue                                  # выключена владельцем — не трогаем
        recent = [x for x in tries.get(u, []) if t - x < REPEAT["unit"]]
        if up:
            if recent and ok_again(state, f"unit:{u}"):
                alerts.append(f"✅ {u} снова работает")
            tries[u] = recent
            continue
        if len(recent) < UNIT_TRIES:
            restart(u)
            recent.append(t)
            state.setdefault("guard_seen", {})[f"unit:{u}"] = t
            alerts.append(f"🛠 {u} упала — перезапустил сам (попытка {len(recent)} из {UNIT_TRIES})")
        elif due(state, f"unitfail:{u}", "unit", t):
            alerts.append(f"🚨 {u} не поднимается после {UNIT_TRIES} перезапусков — нужен ассистент. "
                          f"Проверка на Франкфурте: systemctl status {u}")
        tries[u] = recent
    return alerts


# 27.10 рецепт: Gemini упёрся в дневной лимит → до конца дня выключаем проверку утренних видео (самое прожорливое),
# чтобы бесплатного лимита хватило на хуки. Флаг читает genplan/ai.vision; завтра сам перестаёт действовать.
SAVER = Path("/var/lib/papa-genplan/gemini-saver")
SAVER_SHARED = Path("/var/lib/papa-sources-choice/gemini-saver")   # 30.10: тот же флаг видит и фоновая Разведка (budget.py)


def gemini_limit_hit() -> bool:
    out = sh("journalctl", "-u", "papa-genplan", "-u", "papa-fabrika", "-u", "papa-razvedka@*", "--since", "1 hour ago",
             "--no-pager", "-o", "cat", timeout=30)
    return "лимит Gemini исчерпан" in out or ("Gemini" in out and "429" in out) or "Gemini: лимит исчерпан" in out


def saver_guard(now: dt.datetime, state: dict, hit=gemini_limit_hit, flag: Path = SAVER,
                shared: Path | None = SAVER_SHARED) -> list[str]:
    today = now.date().isoformat()
    try:                                          # 31.10: флаг до обнуления лимита Google (полночь PT) — считаем снятым
        from zoneinfo import ZoneInfo
        reset = now.astimezone(ZoneInfo("America/Los_Angeles")).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        on = flag.read_text().strip() == today and flag.stat().st_mtime >= reset
    except (OSError, ValueError):
        on = False
    if on or not hit():
        return []
    try:
        flag.write_text(today)
        flag.chmod(0o644)
    except OSError:
        return []
    if shared is not None:
        try:                                      # общая папка GENPLAN ↔ Разведка: фоновые агенты тоже останавливаются
            shared.write_text(today)
            shared.chmod(0o644)
        except OSError:
            pass
    return ["🛠 Gemini упёрся в дневной лимит — до конца дня выключил проверку утренних видео и фоновую Разведку, "
            "чтобы хватило на ИИ-ассистента и хуки. Завтра включится сама."]


def due(state: dict, key: str, kind: str, now: float) -> bool:
    seen = state.setdefault("guard_seen", {})
    if now - seen.get(key, 0) >= REPEAT[kind]:
        seen[key] = now
        return True
    return False


def ok_again(state: dict, key: str) -> bool:
    """Было сломано, стало хорошо — один раз сообщить «восстановлено»."""
    return state.setdefault("guard_seen", {}).pop(key, None) is not None


def account_rights(run=None) -> dict | None:
    run = run or (lambda: subprocess.run([PY, str(REPO / "ops/frankfurt/xojaobod_check.py"), "--json"],
                                         capture_output=True, text=True, timeout=90).stdout)
    try:
        return json.loads((run() or "").strip().splitlines()[-1])
    except (ValueError, IndexError, subprocess.SubprocessError, OSError):
        return None


def enqueue(task: str, reason: str, key: str, gw: Path = GW_DB) -> bool:
    """Поставить задачу автопилоту (как это делает ИИ через шлюз). approve-задача придёт владельцу кнопкой."""
    import hashlib
    import secrets
    if not gw.exists():
        return False
    payload = json.dumps({"task": task, "reason": reason[:300]}, ensure_ascii=False)
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        c = sqlite3.connect(str(gw), timeout=15)
        c.execute("INSERT OR IGNORE INTO tasks (id,operation,target,priority,status,payload,idempotency,fingerprint,"
                  "requested_by,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                  (secrets.token_hex(12), "papa_task", "frankfurt", 10, "queued", payload, key,
                   hashlib.sha256(payload.encode()).hexdigest(), "guard", now, now))
        c.commit(); c.close()
        return True
    except sqlite3.Error:
        return False


def ai_alive(env_ai: dict, get=None) -> str | None:
    """27.10: проверяем Gemini — основной ИИ PAPA (аккаунт Anthropic заблокирован, он больше не проверяется).
    None — ключ жив (или не задан); иначе текст беды."""
    key = env_ai.get("GEMINI_API_KEY", "").strip().strip('"').strip("'")
    if not key:
        return None
    def _get():
        req = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models?pageSize=1",
                                     headers={"x-goog-api-key": key})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, ""
        except urllib.error.HTTPError as e:
            return e.code, (e.read() or b"")[:300].decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001 — сеть: не тревожим
            return 0, type(e).__name__
    code, body = (get or _get)()
    if code in (200, 0, 429, 500, 502, 503):
        return None
    return "ключ не принят (истёк или удалён)" if code in (400, 401, 403) and ("API_KEY" in body or "key" in body.lower()) \
        else f"HTTP {code}"


def guard(cfg: dict, env: dict, now: dt.datetime, state: dict, db_path: Path = GP_DB, rights=account_rights,
          ai_check=ai_alive, queue=enqueue) -> list[str]:
    alerts: list[str] = []
    t = now.timestamp()
    main_tok = env.get("GENPLAN_BOT_TOKEN", "")
    # 1) права публикации в каждом рабочем канале/группе
    for code, ch in cfg["channels"].items():
        live = ch.get("mode") == "live" or (ch.get("morning") or {}).get("live") or (ch.get("digest") or {}).get("live")
        if not live:
            continue
        key = f"rights:{code}"
        if ch.get("publisher") == "bot":
            tok = env.get(ch.get("bot_token_env", ""), "") or main_tok
            me = tg(tok, "getMe")
            if not me.get("ok"):
                continue                      # сеть/Telegram — не тревожим ложно
            m = tg(tok, "getChatMember", chat_id="@" + ch["username"], user_id=me["result"]["id"])
            if not m.get("ok"):
                continue
            r = m.get("result") or {}
            good = r.get("status") == "administrator" and r.get("can_post_messages", True)
            who = "@" + me["result"].get("username", "бот")
        elif ch.get("publisher") == "account":
            r = rights()
            if r is None:
                continue
            good = bool(r.get("session") and r.get("admin"))
            who = "аккаунт PAPA"
            if not good and r.get("session") and due(state, f"heal:{code}", "heal", t):
                if queue("xojaobod-admin", f"🛡 Страж: у аккаунта PAPA сняли права в {ch['title']} — вернуть (ничего не публикует)",
                         f"guard-heal-{code}-{now:%Y%m%d%H}"):
                    alerts.append(f"🛠 {ch['title']}: запросил починку — нажмите «✅ Разрешить» (xojaobod-admin)")
            if not r.get("session"):
                who = "аккаунт PAPA (сессия слетела — нужен вход владельца)"
        else:
            continue
        if good:
            if ok_again(state, key):
                alerts.append(f"✅ {ch['title']}: права публикации снова в порядке")
        elif due(state, key, "rights", t):
            alerts.append(f"🚨 {ch['title']}: {who} НЕ МОЖЕТ публиковать (сняли права админа). Посты и реклама не выйдут!")
    # 2) ключ ИИ
    why = ai_check(envf(AI_ENV))
    if why and due(state, "ai", "ai", t):
        alerts.append(f"🚨 ИИ (Gemini): {why}. ИИ-хуки и Тренд-разведка не работают — посты выходят без ИИ-хука. "
                      "Новый ключ: papa-update genplan-gemini-key (Франкфурт)")
    elif not why and ok_again(state, "ai"):
        alerts.append("✅ ИИ (Gemini) снова работает")
    # 2б) воронки Instagram
    alerts += voronka_guard(now, state)
    alerts += unit_guard(now, state)
    alerts += saver_guard(now, state)
    # 3) реклама и посты: время прошло — не вышли; ошибки публикации
    if db_path.exists():
        db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=15)
        db.row_factory = sqlite3.Row
        late = (now - dt.timedelta(minutes=7)).isoformat()
        drift = (now - STUCK_DRIFT).isoformat()
        try:                                       # 30.10 сверка №14: пост, который всё время переносят (+10 после рекламы и т.п.),
            stuck = db.execute(                    # тоже ловим — по исходному времени planned_at, с запасом STUCK_DRIFT
                "SELECT id, channel, rubric, COALESCE(planned_at, scheduled_at) AS scheduled_at FROM materials "
                "WHERE status='queued' AND scheduled_at IS NOT NULL AND (scheduled_at < ? OR planned_at < ?)",
                (late, drift)).fetchall()
        except sqlite3.Error:                      # старая база без planned_at
            stuck = db.execute("SELECT id, channel, rubric, scheduled_at FROM materials WHERE status='queued' "
                               "AND scheduled_at IS NOT NULL AND scheduled_at < ?", (late,)).fetchall()
        for r in stuck:
            ad = (r["rubric"] or "").lower().startswith("реклама")
            if due(state, f"stuck:{r['id']}", "post", t):
                when = dt.datetime.fromisoformat(r["scheduled_at"]).astimezone(TZ).strftime("%H:%M")
                alerts.append(("🚨 РЕКЛАМА" if ad else "⚠️ Пост") + f" ({Audit.title(cfg, r['channel'])}, {when}) не вышла вовремя — "
                              "проверьте пульт (📅 СЕГОДНЯ)")
        since = (now - dt.timedelta(hours=3)).isoformat()
        try:
            rows = db.execute("SELECT p.id, p.channel, p.error, m.rubric FROM publications p LEFT JOIN materials m ON m.id=p.material_id "
                              "WHERE p.at>=? AND (p.status='failed' OR (p.status='missed' AND m.rubric LIKE 'Реклама%'))",
                              (since,)).fetchall()
        except sqlite3.Error:
            rows = db.execute("SELECT id, channel, error, '' AS rubric FROM publications WHERE status='failed' AND at>=?",
                              (since,)).fetchall()
        for r in rows:
            if due(state, f"pubfail:{r['id']}", "post", t):
                ad = (r["rubric"] or "").lower().startswith("реклама")
                alerts.append(("🚨 РЕКЛАМА не вышла" if ad else "❌ Пост не вышел") +
                              f" ({Audit.title(cfg, r['channel'])}): {(r['error'] or '')[:150]}")
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
        alerts = guard(cfg, env, now, state)
        if now.minute < 10:                          # охрана админов и «тишина» — раз в час, как раньше
            alerts += watch(cfg, env, now, state)
        sp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        print("\n".join(alerts) or "watch: всё спокойно")
        if send and alerts:
            for o in env.get("OWNER_IDS", "").split(","):
                if o.strip():
                    tg(report_token(env), "sendMessage", chat_id=o.strip(), text="\n\n".join(alerts)[:4000])
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
        print("отправлено:", ", ".join(deliver(env, msg, urgent=bool(a.bad))) or "никуда")
    return 1 if a.bad else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    sys.exit(main(args[0] if args else "full", "--no-send" not in args))
