"""Прокси Gemini: перевод форматов и путь «Google 429 → OpenRouter»."""
import json
import os
import sys
import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gemini_proxy as P  # noqa: E402


def serve(handler_cls):
    s = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


class FakeGoogle(BaseHTTPRequestHandler):
    code = 429

    def log_message(self, *a):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        body = b'{"candidates":[{"content":{"parts":[{"text":"google"}]}}]}' if self.code == 200 else b'{"error":{}}'
        self.send_response(self.code); self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)


class FakeOR(BaseHTTPRequestHandler):
    seen = {}

    def log_message(self, *a):
        pass

    def do_POST(self):
        FakeOR.seen = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
        body = json.dumps({"choices": [{"message": {"content": '{"hub":"ИБРАТ"}'}, "finish_reason": "stop"}],
                           "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.0001}}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)


class T(unittest.TestCase):
    def test_convert(self):
        body = {"systemInstruction": {"parts": [{"text": "sys"}]},
                "contents": [{"role": "user", "parts": [{"text": "hi"}, {"inline_data": {"mime_type": "image/jpeg", "data": "QUJD"}},
                                                         {"inline_data": {"mime_type": "audio/mpeg", "data": "QUJD"}}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 99, "responseMimeType": "application/json"}}
        o = P.to_openai("gemini-flash-lite-latest", body)
        self.assertEqual(o["model"], "google/gemini-2.5-flash-lite")
        self.assertEqual(o["messages"][0], {"role": "system", "content": "sys"})
        kinds = [c["type"] for c in o["messages"][1]["content"]]
        self.assertEqual(kinds, ["text", "image_url", "input_audio"])
        self.assertEqual(o["messages"][1]["content"][2]["input_audio"]["format"], "mp3")
        self.assertEqual((o["max_tokens"], o["response_format"]["type"]), (99, "json_object"))
        g = P.to_gemini({"choices": [{"message": {"content": "ok", "images": [{"image_url": {"url": "data:image/png;base64,QQ=="}}]}}]})
        parts = g["candidates"][0]["content"]["parts"]
        self.assertEqual(parts[0]["text"], "ok")
        self.assertEqual(parts[1]["inlineData"]["mimeType"], "image/png")
        self.assertEqual(P.or_model("gemini-2.5-flash-image"), "google/gemini-2.5-flash-image")

    def test_fallback(self):
        g, o = serve(FakeGoogle), serve(FakeOR)
        P.GOOGLE = f"http://127.0.0.1:{g.server_port}"
        P.OR_URL = f"http://127.0.0.1:{o.server_port}/"
        P.LOG = "/tmp/_gp_stats.json"
        os.environ["OPENROUTER_API_KEY"] = "test"
        px = serve(P.H)
        url = f"http://127.0.0.1:{px.server_port}/v1beta/models/gemini-flash-lite-latest:generateContent"

        def ask(body):
            req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"content-type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read())
        FakeGoogle.code = 200
        self.assertEqual(ask({"contents": [{"parts": [{"text": "a"}]}]})["candidates"][0]["content"]["parts"][0]["text"], "google")
        FakeGoogle.code = 429                                 # бесплатный лимит кончился → OpenRouter
        d = ask({"contents": [{"parts": [{"text": "a"}]}]})
        self.assertEqual(d["_via"], "openrouter")
        self.assertIn("ИБРАТ", d["candidates"][0]["content"]["parts"][0]["text"])
        self.assertEqual(FakeOR.seen["model"], "google/gemini-2.5-flash-lite")
        with self.assertRaises(urllib.error.HTTPError):       # поиск Google — только Google, без OpenRouter
            ask({"contents": [{"parts": [{"text": "a"}]}], "tools": [{"google_search": {}}]})


if __name__ == "__main__":
    unittest.main()
