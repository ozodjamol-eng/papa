"""PAPA автопилот (Франкфурт, root): берёт из шлюза NEXUS задачи papa_task, поставленные ИИ, и выполняет
`papa-update <задача>` — ровно то, что владелец делает в консоли.

Граница безопасности — здесь, а не в шлюзе:
  * allow.json: auto — сразу; approve (и всё незнакомое) — только после кнопки «✅ Разрешить» владельца в Telegram;
    deny — никогда (секреты, вход в аккаунты, сам автопилот);
  * одна задача за раз, тайм-аут, stdin закрыт (задачи с вводом не пройдут);
  * в выводе маскируются строки, похожие на токены;
  * о каждой задаче владелец получает сообщение от «🎉 КАТТА ДАВРА Пульт».
Лондон (с 2026-10-16): задачу target=london решает этот же исполнитель — по ops/london/autopilot/allow.json и той же
кнопке владельца, — но не выполняет сам: переводит в 'ready', её забирает papa-runner на Лондоне; итог приходит сюда.
Только стандартная библиотека Python. Отключить: systemctl disable --now papa-autopilot
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(os.environ.get("PAPA_REPO", "/opt/papa"))
HERE = Path(__file__).resolve()
ALLOW = HERE.parent / "allow.json"
ALLOW_LONDON = Path(os.environ.get("PAPA_ALLOW_LONDON", str(HERE.parents[2] / "london" / "autopilot" / "allow.json")))
LONDON_WAIT = int(os.environ.get("PAPA_LONDON_WAIT", str(25 * 60)))
SERVER_NAME = {"frankfurt": "🖥 Франкфурт", "london": "🖥 Лондон"}
GW_DB = Path(os.environ.get("PAPA_AUTOPILOT_GW_DB", "/var/lib/nexus-private-control/control.sqlite3"))
GP_DB = Path(os.environ.get("PAPA_GENPLAN_DB", "/var/lib/papa-genplan/genplan.sqlite3"))
GP_ENV = Path(os.environ.get("PAPA_GENPLAN_ENV", "/etc/papa-genplan/genplan.env"))
UPDATE = os.environ.get("PAPA_UPDATE", "/usr/local/bin/papa-update")
TASK_TIMEOUT = int(os.environ.get("PAPA_AUTOPILOT_TIMEOUT", str(45 * 60)))
APPROVAL_WAIT = int(os.environ.get("PAPA_AUTOPILOT_APPROVAL_WAIT", str(30 * 60)))
OUT_LIMIT = 12000
SECRETS = [re.compile(p) for p in (r"\b\d{6,12}:[A-Za-z0-9_-]{30,}\b",          # токен бота Telegram
                                   r"\bAIza[0-9A-Za-z_-]{30,}\b",                 # ключ Google/Gemini
                                   r"\b(?:sk|nxa|ghp|gho|github_pat)_[A-Za-z0-9_]{20,}\b",
                                   r"(?i)((?:token|key|secret|password|hash)\s*[=:]\s*)\S{12,}",
                                   r"\b[A-Za-z0-9+/_-]{48,}={0,2}\b")]          # длинные base64/hex-строки


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(*a) -> None:
    print(*a, flush=True)


# ---------- политика ----------
def policy(task: str, allow: dict | None = None, server: str = "frankfurt") -> str:
    """auto / approve / deny для имени задачи на сервере."""
    if allow is None:
        try:
            allow = json.loads((ALLOW_LONDON if server == "london" else ALLOW).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return "deny"                                   # нет списка — ничего не делаем
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,48}", task):
        return "deny"
    if any(re.search(p, task) for p in allow.get("deny_patterns", [])):
        return "deny"
    if task in allow.get("auto", []):
        return "auto"
    return "approve"


def mask(text: str) -> str:
    for rx in SECRETS:
        text = rx.sub(lambda m: (m.group(1) if m.groups() else "") + "<скрыто>", text)
    return text


# ---------- базы: открываем от имени владельца файла, чтобы root не создал чужих -wal/-shm ----------
@contextlib.contextmanager
def as_owner(path: Path):
    st = path.stat()
    if os.geteuid() != 0 or st.st_uid == 0:
        yield
        return
    os.setegid(st.st_gid)
    os.seteuid(st.st_uid)
    try:
        yield
    finally:
        os.seteuid(0)
        os.setegid(0)


@contextlib.contextmanager
def db(path: Path):
    with as_owner(path):
        c = sqlite3.connect(str(path), timeout=15)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA busy_timeout=15000")
        try:
            yield c
            c.commit()
        finally:
            c.close()


def audit(c, action: str, subject: str, info: str = "") -> None:
    c.execute("INSERT INTO audit(ts,actor,action,subject,info) VALUES(?,?,?,?,?)",
              (utc(), "papa-autopilot", action, subject[:160], info[:500]))


def claim(path: Path = GW_DB) -> dict | None:
    with db(path) as c:
        c.execute("BEGIN IMMEDIATE")
        c.execute("UPDATE tasks SET status='expired', updated_at=? WHERE operation='papa_task' AND status='queued' AND created_at<?",
                  (utc(), datetime.fromtimestamp(time.time() - 3600, timezone.utc).isoformat()))
        r = c.execute("SELECT * FROM tasks WHERE operation='papa_task' AND target IN ('frankfurt','london') "
                      "AND status='queued' ORDER BY created_at LIMIT 1").fetchone()
        if not r:
            return None
        # Франкфурт: running сразу; Лондон: 'deciding' — исполнитель Лондона берёт только 'ready'
        c.execute("UPDATE tasks SET status=?, attempts=attempts+1, updated_at=? WHERE id=?",
                  ("running" if r["target"] == "frankfurt" else "deciding", utc(), r["id"]))
        audit(c, "claimed", r["id"])
        return {"id": r["id"], **json.loads(r["payload"]), "by": r["requested_by"], "server": r["target"]}


def set_status(tid: str, status: str, result: dict | None = None, path: Path = GW_DB) -> None:
    with db(path) as c:
        c.execute("UPDATE tasks SET status=?, result=?, updated_at=? WHERE id=?",
                  (status, json.dumps(result, ensure_ascii=False) if result is not None else None, utc(), tid))
        audit(c, status, tid, (result or {}).get("summary", ""))


def recover(path: Path = GW_DB) -> None:
    """После перезапуска исполнителя: зависшие «running/awaiting_owner» — ошибка (повторять сами не будем)."""
    with db(path) as c:
        n = c.execute("UPDATE tasks SET status='failed', result=?, updated_at=? WHERE operation='papa_task' "
                      "AND ((target='frankfurt' AND status='running') OR status IN ('awaiting_owner','deciding'))",
                      (json.dumps({"error": "autopilot_restarted", "summary": "исполнитель перезапускался — запустите заново"}),
                       utc())).rowcount
        if n:
            audit(c, "recovered", "papa_task", f"{n}")


# ---------- Telegram (бот «КАТТА ДАВРА Пульт») ----------
def env_file(p: Path) -> dict:
    out = {}
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def tg(method: str, **params) -> dict:
    e = env_file(GP_ENV)
    tok = e.get("GENPLAN_BOT_TOKEN")
    if not tok:
        return {}
    data = urllib.parse.urlencode({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
                                   for k, v in params.items()}).encode()
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/{method}", data=data, timeout=20) as r:
            return json.loads(r.read()).get("result") or {}
    except Exception as ex:  # noqa: BLE001 — уведомление не должно ронять исполнителя
        log("telegram:", type(ex).__name__)
        return {}


def owners() -> list[int]:
    return [int(x) for x in env_file(GP_ENV).get("OWNER_IDS", "").split(",") if x.strip().lstrip("-").isdigit()]


def notify(text: str, markup: dict | None = None) -> list[tuple[int, int]]:
    sent = []
    for o in owners():
        p = {"chat_id": o, "text": text[:4000], "disable_web_page_preview": True}
        if markup:
            p["reply_markup"] = markup
        r = tg("sendMessage", **p)
        if r.get("message_id"):
            sent.append((o, r["message_id"]))
    return sent


def approval(tid: str, path: Path = GP_DB) -> str | None:
    """Ответ владельца: кнопку обрабатывает GENPLAN (у бота один получатель обновлений) и пишет kv autopilot_<id>."""
    try:
        with db(path) as c:
            r = c.execute("SELECT v FROM kv WHERE k=?", (f"autopilot_{tid}",)).fetchone()
            return r[0] if r else None
    except sqlite3.Error:
        return None


# ---------- выполнение ----------
def run(task: str) -> tuple[int, str]:
    try:
        p = subprocess.run([UPDATE, task], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=TASK_TIMEOUT, cwd="/root", env={"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                                                                  "HOME": "/root", "LANG": "C.UTF-8", "TERM": "dumb"})
        out, rc = p.stdout.decode("utf-8", "replace"), p.returncode
    except subprocess.TimeoutExpired as e:
        out, rc = (e.stdout or b"").decode("utf-8", "replace") + f"\n== TIMEOUT {TASK_TIMEOUT // 60} мин", 124
    out = mask(out)
    return rc, (out if len(out) <= OUT_LIMIT else "…(начало обрезано)…\n" + out[-OUT_LIMIT:])


def last_line(out: str) -> str:
    for line in reversed(out.strip().splitlines()):
        if line.strip():
            return line.strip()[:200]
    return ""


def status_of(tid: str, path: Path = GW_DB) -> dict:
    with db(path) as c:
        r = c.execute("SELECT status, result FROM tasks WHERE id=?", (tid,)).fetchone()
        return {"status": r["status"], "result": json.loads(r["result"] or "{}")} if r else {"status": "missing", "result": {}}


def wait_london(tid: str, gw: Path, sleep) -> tuple[int, str]:
    """Отдать задачу исполнителю Лондона и дождаться итога (выполняет papa-runner, не мы)."""
    set_status(tid, "ready", None, gw)
    t0 = time.time()
    while time.time() - t0 < LONDON_WAIT:
        st = status_of(tid, gw)
        if st["status"] in ("succeeded", "failed", "expired"):
            res = st["result"]
            return (res.get("rc", 1) if st["status"] != "expired" else 125), res.get("output", "") or res.get("summary", "")
        sleep(5)
    st = status_of(tid, gw)
    if st["status"] == "ready":                 # исполнитель так и не взял — снимаем, чтобы не выполнилась внезапно позже
        set_status(tid, "failed", {"error": "runner_offline", "summary": "исполнитель Лондона не ответил — задача снята"}, gw)
        return 126, "исполнитель Лондона (papa-runner) не ответил за 25 мин — задача снята, ничего не выполнено"
    return 127, "Лондон ещё выполняет — итог смотрите позже (nexus_papa_result)"


def handle(t: dict, gw: Path = GW_DB, gp: Path = GP_DB, runner=run, sleep=time.sleep) -> str:
    tid, task, reason = t["id"], t.get("task", ""), (t.get("reason") or "").strip()
    server = t.get("server", "frankfurt")
    where = SERVER_NAME.get(server, server)
    if runner is run:                       # свежий список задач и allow.json из GitHub до решения
        subprocess.run([UPDATE], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    pol = policy(task, server=server)
    win = in_window(datetime.now(timezone.utc))
    if server == "london" and pol == "auto" and win and task not in LONDON_READ_ONLY:
        pol = "approve"                        # GENPLAN 5 в главные часы: любое изменение — только с кнопкой владельца
    if pol == "auto" and server == "frankfurt" and task in WINDOW_TASKS and win:
        if reason.upper().startswith("СРОЧНО"):
            pol = "approve"                    # срочная починка в прайм-тайм — только с кнопкой владельца
        else:
            set_status(tid, "failed", {"error": "release_window", "summary": f"окно выкладки: сейчас главные посты ({win}) — "
                                       "перезапуски и выкладки после; срочно — reason «СРОЧНО …» и кнопка владельца"}, gw)
            return "window"
    if pol == "deny":
        set_status(tid, "failed", {"error": "denied", "summary": f"«{task}» автопилоту запрещена — только владелец в консоли"}, gw)
        return "denied"
    if pol == "approve":
        set_status(tid, "awaiting_owner", None, gw)
        msgs = notify(f"🤖 Автопилот просит разрешения ({where})\n\nЗадача: {task}\nЗачем: {reason or '—'}",
                      {"inline_keyboard": [[{"text": "✅ Разрешить", "callback_data": f"ap:{tid}:y"},
                                            {"text": "❌ Нет", "callback_data": f"ap:{tid}:n"}]]})
        if not msgs:
            set_status(tid, "failed", {"error": "no_owner_channel", "summary": "не смог спросить владельца в Telegram"}, gw)
            return "no_owner"
        t0 = time.time()
        ans = None
        while time.time() - t0 < APPROVAL_WAIT:
            ans = approval(tid, gp)
            if ans:
                break
            sleep(3)
        if ans != "yes":
            set_status(tid, "failed", {"error": "not_approved",
                                       "summary": "владелец отказал" if ans == "no" else "владелец не ответил за 30 минут"}, gw)
            return "rejected"
        if server == "frankfurt":
            set_status(tid, "running", None, gw)
    notify(f"🤖 Автопилот запускает ({where}): {task}" + (f"\nЗачем: {reason}" if reason else ""))
    t0 = time.time()
    if server == "london":
        rc, out = wait_london(tid, gw, sleep)
        out = mask(out)
    else:
        rc, out = runner(task)
    mins = round((time.time() - t0) / 60, 1)
    summary = last_line(out)
    if server == "frankfurt":
        set_status(tid, "succeeded" if rc == 0 else "failed",
                   {"task": task, "rc": rc, "minutes": mins, "summary": summary, "output": out}, gw)
    notify(f"{'✅' if rc == 0 else '❌'} Автопилот ({where}): {task} — {'готово' if rc == 0 else f'ошибка (код {rc})'} за {mins} мин\n{summary}")
    return "ok" if rc == 0 else "failed"


# Протокол «Окно выкладки» (16.10): в главные часы постов не перезапускаем и не выкатываем
WINDOWS = (("04:30", "07:30"), ("19:00", "22:00"))      # Ташкент; утро с 05:00 (решение 17.10)
LONDON_READ_ONLY = {"status", "london-diagnose", "genplan-inventory", "evening-digest-trace", "evening-digest-trace2", "evening-digest-trace3", "evening-digest-find", "genplan5-ads-trace", "genplan5-ads-list"}   # только чтение — можно и в главные часы
WINDOW_TASKS = {"genplan-restart", "pult-deploy", "morning-deploy", "morning-refresh", "curator-install", "audit-install",
                "folders-sort", "morning-hunt"}


def in_window(now_utc: datetime) -> str:
    t = (now_utc + timedelta(hours=5)).strftime("%H:%M")
    return next((f"{a}–{b}" for a, b in WINDOWS if a <= t < b), "")


def code_hash() -> str:
    return hashlib.sha256(HERE.read_bytes() + ALLOW.read_bytes()).hexdigest()   # allow Лондона читается при каждой задаче


def main() -> None:
    if os.geteuid() != 0:
        sys.exit("нужен root")
    if not GW_DB.exists():
        sys.exit(f"нет базы шлюза {GW_DB}")
    recover()
    start = code_hash()
    log("PAPA автопилот запущен")
    while True:
        try:
            t = claim()
            if t:
                log("задача", t["id"], t.get("task"))
                log("итог", handle(t))
            elif code_hash() != start:                     # после papa-update пришёл новый код — перезапускаемся сами
                log("новый код автопилота — перезапуск")
                sys.exit(0)
        except Exception as e:  # noqa: BLE001
            log("ошибка:", type(e).__name__, str(e)[:200])
        time.sleep(3)


if __name__ == "__main__":
    main()
