"""🔀 Прокси Gemini (31.10.2026, владелец: «твой честный выбор» → OpenRouter с предоплатой $5).

Все агенты PAPA говорят на «языке Gemini» (generateContent). Этот прокси (127.0.0.1:8790) принимает такие запросы и:
  1) сначала шлёт их в БЕСПЛАТНЫЙ Google Gemini (ключ агента, как раньше);
  2) только если Google ответил «лимит» (429) или «перегружен» (500/503) — переводит запрос в OpenRouter (предоплата)
     и возвращает ответ обратно в формате Gemini. Так $5 тратятся только на то, что не влезло в бесплатный лимит.
  Запросы с поиском Google (tools) — только в Google (в OpenRouter поиск платный отдельно).
Включение: файл /etc/papa-gemini-proxy/on (агенты сами идут через прокси). Откат: удалить этот файл.
Ключ OpenRouter — /etc/papa-gemini-proxy/env (OPENROUTER_API_KEY=…), вводит владелец; лимит ключа $5 — потолок трат.
Только стандартная библиотека."""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

GOOGLE = "https://generativelanguage.googleapis.com"
OR_URL = "https://openrouter.ai/api/v1/chat/completions"
PORT = int(os.environ.get("GEMINI_PROXY_PORT", "8790"))
FALLBACK_CODES = {429, 500, 502, 503, 504}
LOG = os.environ.get("STATE_DIRECTORY", "/var/lib/papa-gemini-proxy") + "/stats.json"
_lock = threading.Lock()

# модель Gemini → модель OpenRouter (одна и та же модель Google, только через OpenRouter)
MODELS = {
    "lite": "google/gemini-2.5-flash-lite",
    "image": "google/gemini-2.5-flash-image",
    "pro": "google/gemini-2.5-pro",
    "flash": "google/gemini-2.5-flash",
}


def or_model(gemini_model: str) -> str:
    m = gemini_model.lower()
    if "image" in m:
        return MODELS["image"]
    if "lite" in m:
        return MODELS["lite"]
    if "pro" in m:
        return MODELS["pro"]
    return MODELS["flash"]


def _text(parts) -> str:
    return "".join(p.get("text", "") for p in parts or [] if isinstance(p, dict))


def to_openai(model: str, body: dict) -> dict:
    """Запрос Gemini → запрос OpenRouter (OpenAI-формат)."""
    msgs = []
    si = body.get("systemInstruction") or body.get("system_instruction")
    if si:
        msgs.append({"role": "system", "content": _text(si.get("parts"))})
    for c in body.get("contents") or []:
        role = "assistant" if c.get("role") == "model" else "user"
        content = []
        for p in c.get("parts") or []:
            if "text" in p:
                content.append({"type": "text", "text": p["text"]})
                continue
            d = p.get("inline_data") or p.get("inlineData")
            if d:
                mime = d.get("mime_type") or d.get("mimeType") or ""
                if mime.startswith("image/"):
                    content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{d['data']}"}})
                elif mime.startswith("audio/"):
                    fmt = mime.split("/", 1)[1].replace("mpeg", "mp3").replace("x-wav", "wav")
                    content.append({"type": "input_audio", "input_audio": {"data": d["data"], "format": fmt}})
        msgs.append({"role": role, "content": content})
    out = {"model": or_model(model), "messages": msgs}
    g = body.get("generationConfig") or {}
    if "temperature" in g:
        out["temperature"] = g["temperature"]
    if "maxOutputTokens" in g:
        out["max_tokens"] = g["maxOutputTokens"]
    if g.get("responseMimeType") == "application/json":
        out["response_format"] = {"type": "json_object"}
    if "IMAGE" in [x.upper() for x in g.get("responseModalities") or []]:
        out["modalities"] = ["image", "text"]
        ar = (g.get("imageConfig") or {}).get("aspectRatio")
        if ar:
            out["image_config"] = {"aspect_ratio": ar}
    return out


def to_gemini(resp: dict) -> dict:
    """Ответ OpenRouter → ответ Gemini (candidates/content/parts + usageMetadata)."""
    ch = (resp.get("choices") or [{}])[0]
    msg = ch.get("message") or {}
    parts = []
    if msg.get("content"):
        parts.append({"text": msg["content"] if isinstance(msg["content"], str) else _text(msg["content"])})
    for im in msg.get("images") or []:
        url = ((im.get("image_url") or {}).get("url")) or ""
        if url.startswith("data:") and ";base64," in url:
            mime, data = url[5:].split(";base64,", 1)
            parts.append({"inlineData": {"mimeType": mime, "data": data}})
    u = resp.get("usage") or {}
    fr = {"stop": "STOP", "length": "MAX_TOKENS"}.get(ch.get("finish_reason") or "", "STOP")
    return {"candidates": [{"content": {"role": "model", "parts": parts}, "finishReason": fr}],
            "usageMetadata": {"promptTokenCount": u.get("prompt_tokens", 0),
                              "candidatesTokenCount": u.get("completion_tokens", 0)},
            "_via": "openrouter", "_cost": u.get("cost")}


def _stat(key: str, cost: float = 0.0):
    with _lock:
        try:
            with open(LOG, encoding="utf-8") as f:
                st = json.load(f)
        except (OSError, ValueError):
            st = {}
        day = time.strftime("%Y-%m-%d")
        d = st.setdefault(day, {})
        d[key] = d.get(key, 0) + 1
        if cost:
            d["cost"] = round(d.get("cost", 0.0) + float(cost), 6)
        for k in sorted(st)[:-14]:
            st.pop(k, None)
        try:
            os.makedirs(os.path.dirname(LOG), exist_ok=True)
            with open(LOG, "w", encoding="utf-8") as f:
                json.dump(st, f)
        except OSError:
            pass


def call_openrouter(model: str, body: dict, timeout: int = 180) -> tuple[int, dict]:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        return 503, {"error": {"code": 503, "message": "OpenRouter: нет ключа"}}
    req = urllib.request.Request(OR_URL, data=json.dumps(to_openai(model, body)).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}",
                                          "X-Title": "PAPA"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read())
    except urllib.error.HTTPError as e:
        code = 429 if e.code == 402 else e.code          # 402 = $5 кончились — для агентов это «лимит»
        return code, {"error": {"code": code, "message": f"OpenRouter {e.code}: {e.read()[:200]!r}"}}
    except Exception as e:  # noqa: BLE001
        return 503, {"error": {"code": 503, "message": f"OpenRouter: {type(e).__name__}"}}
    if resp.get("error"):
        return 503, {"error": {"code": 503, "message": f"OpenRouter: {resp['error']}"}}
    out = to_gemini(resp)
    _stat("openrouter", out.get("_cost") or 0.0)
    return 200, out


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code: int, data: bytes, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):                                        # список моделей и т. п. — как есть в Google
        self._google("GET", None)

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if ":generateContent" not in self.path:
            return self._google("POST", raw)
        try:
            body = json.loads(raw or b"{}")
        except ValueError:
            return self._send(400, b'{"error":{"code":400,"message":"bad json"}}')
        model = self.path.split("/models/", 1)[-1].split(":", 1)[0]
        code, data, hdr = self._google("POST", raw, reply=False)
        if code == 200 or code not in FALLBACK_CODES or body.get("tools"):
            _stat("google" if code == 200 else f"google_{code}")
            return self._send(code, data, hdr)
        c2, out = call_openrouter(model, body)
        if c2 != 200:
            _stat(f"openrouter_{c2}")
        return self._send(c2, json.dumps(out).encode())

    def _google(self, method: str, raw, reply: bool = True):
        hdrs = {k: v for k, v in self.headers.items() if k.lower() in ("content-type", "x-goog-api-key")}
        req = urllib.request.Request(GOOGLE + self.path, data=raw, method=method, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                res = (r.status, r.read(), r.headers.get("Content-Type", "application/json"))
        except urllib.error.HTTPError as e:
            res = (e.code, e.read(), e.headers.get("Content-Type", "application/json"))
        except Exception as e:  # noqa: BLE001
            res = (503, json.dumps({"error": {"code": 503, "message": f"Google: {type(e).__name__}"}}).encode(),
                   "application/json")
        if reply:
            return self._send(*res)
        return res


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print(f"gemini-proxy: 127.0.0.1:{PORT} · Google бесплатно → OpenRouter при лимите", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    sys.exit(main())
