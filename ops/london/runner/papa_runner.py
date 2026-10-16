#!/usr/bin/env python3
"""PAPA runner (Лондон, root): выполняет `papa-update <задача>` — только задачи ops/london/tasks, которые
автопилот Франкфурта уже разрешил (allow.json Лондона + кнопка владельца) и перевёл в статус 'ready'.

Граница безопасности:
  * сам ничего не решает «шире» Франкфурта: ещё раз сверяет имя с ops/london/autopilot/allow.json
    (deny — отказ; незнакомое имя или нет файла задачи — отказ);
  * связь только исходящая, по tailnet, HTTPS с проверкой сертификата, свой токен (устройство london-runner);
  * одна задача за раз, тайм-аут, stdin закрыт; в выводе маскируются строки, похожие на секреты.
Только стандартная библиотека Python. Отключить: systemctl disable --now papa-runner
"""
from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import time
from pathlib import Path

VERSION = "runner-1.0"
REPO = Path(os.environ.get("PAPA_REPO", "/opt/papa"))
UPDATE = os.environ.get("PAPA_UPDATE", "/usr/local/bin/papa-update")
TASK_TIMEOUT = int(os.environ.get("PAPA_RUNNER_TIMEOUT", str(20 * 60)))
OUT_LIMIT = 12000
NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]{1,48}")
SECRETS = [re.compile(p) for p in (r"\b\d{6,12}:[A-Za-z0-9_-]{30,}\b",
                                   r"\bAIza[0-9A-Za-z_-]{30,}\b",
                                   r"\b(?:sk|nxa|ghp|gho|github_pat)_[A-Za-z0-9_]{20,}\b",
                                   r"(?i)((?:token|key|secret|password|hash)\s*[=:]\s*)\S{12,}",
                                   r"\b[A-Za-z0-9+/_-]{48,}={0,2}\b")]


def log(*a) -> None:
    print(*a, flush=True)


def mask(text: str) -> str:
    for rx in SECRETS:
        text = rx.sub(lambda m: (m.group(1) if m.groups() else "") + "<скрыто>", text)
    return text


def allowed(task: str, repo: Path = REPO) -> str:
    """'' — можно; иначе причина отказа. Решение «сразу/по кнопке» уже принял Франкфурт."""
    if not isinstance(task, str) or not NAME_RE.fullmatch(task):
        return "bad_name"
    try:
        allow = json.loads((repo / "ops" / "london" / "autopilot" / "allow.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "no_allow_list"
    if any(re.search(p, task) for p in allow.get("deny_patterns", [])):
        return "denied"
    if task not in allow.get("auto", []) + allow.get("approve", []):
        return "not_listed"
    if not (repo / "ops" / "london" / "tasks" / f"{task}.sh").is_file():
        return "no_such_task"
    return ""


def run(task: str) -> tuple[int, str]:
    try:
        p = subprocess.run([UPDATE, task], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=TASK_TIMEOUT, cwd="/root",
                           env={"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
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


def execute(t: dict, runner=run, refresh=True) -> tuple[bool, dict]:
    task = t.get("task", "")
    if refresh:   # свежие задачи и allow.json из GitHub (то же, что papa-update без задачи)
        subprocess.run([UPDATE], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    why = allowed(task, REPO)
    if why:
        return False, {"task": task, "rc": 126, "error": why, "summary": f"Лондон отказался: {why}"}
    t0 = time.time()
    rc, out = runner(task)
    return rc == 0, {"task": task, "rc": rc, "minutes": round((time.time() - t0) / 60, 1),
                     "summary": last_line(out), "output": out}


class TailnetHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, addr, port, context):
        super().__init__(host, port, context=context, timeout=20)
        self._addr = addr

    def connect(self):
        sock = socket.create_connection((self._addr or self.host, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


class Gateway:
    def __init__(self, url, addr, token):
        if not url.startswith("https://"):
            raise SystemExit("HTTPS required")
        hostport = url[len("https://"):].split("/", 1)[0]
        self.host, _, port = hostport.partition(":")
        self.port, self.addr = int(port or 443), addr
        self.ctx = ssl.create_default_context()
        self.headers = {"Authorization": "Bearer " + token, "X-Device-ID": "london-runner",
                        "Content-Type": "application/json", "User-Agent": "papa-runner/" + VERSION}

    def post(self, path, body):
        c = TailnetHTTPS(self.host, self.addr, self.port, self.ctx)
        try:
            c.request("POST", path, body=json.dumps(body, ensure_ascii=False).encode(), headers=self.headers)
            r = c.getresponse()
            data = r.read(65536)
            if r.status != 200:
                raise RuntimeError("http_%d" % r.status)
            return json.loads(data or b"{}")
        finally:
            c.close()


def main() -> None:
    if os.geteuid() != 0:
        sys.exit("нужен root")
    url = os.getenv("NEXUS_GATEWAY_URL", "").rstrip("/")
    token = os.getenv("PAPA_RUNNER_TOKEN", "")
    if not url or len(token) < 32:
        sys.exit("нет NEXUS_GATEWAY_URL / PAPA_RUNNER_TOKEN")
    gw = Gateway(url, os.getenv("NEXUS_GATEWAY_ADDR", ""), token)
    log("PAPA runner", VERSION, "запущен")
    me = Path(__file__).resolve()
    start = hashlib.sha256(me.read_bytes()).hexdigest()
    backoff = 5
    while True:
        try:
            t = gw.post("/api/runner/next", {}).get("task")
            if t:
                log("задача", t["id"][:8], t.get("task"))
                ok, res = execute(t)
                for _ in range(5):                   # итог важнее всего — повторяем доставку
                    try:
                        gw.post("/api/runner/result", {"task_id": t["id"], "ok": ok, "result": res})
                        break
                    except (OSError, RuntimeError, http.client.HTTPException):
                        time.sleep(10)
                log("итог", t["id"][:8], "ok" if ok else f"ошибка {res.get('rc')}")
            elif hashlib.sha256(me.read_bytes()).hexdigest() != start:   # papa-update принёс новый код — перезапуск
                log("новый код исполнителя — перезапуск")
                sys.exit(0)
            backoff = 5
        except (OSError, RuntimeError, ValueError, http.client.HTTPException) as exc:
            log("шлюз недоступен:", type(exc).__name__, str(exc)[:80])
            backoff = min(backoff * 2, 60)
            time.sleep(backoff)
            continue
        time.sleep(5)


if __name__ == "__main__":
    main()
