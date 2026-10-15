"""Тонкие клиенты официальных API: Instagram (вход через Instagram) и Telegram Bot API.
Только стандартная библиотека. Токены никогда не печатаются."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

IG = "https://graph.instagram.com/v24.0"


class ApiError(Exception):
    def __init__(self, where: str, code, message: str):
        super().__init__(f"{where}: {code} {message}")
        self.code, self.message = code, message


def _http(method: str, url: str, params: dict | None = None, body: dict | None = None,
          headers: dict | None = None, timeout: int = 25) -> dict:
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    data = None
    h = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read() or b"{}")
        except ValueError:
            err = {}
        e2 = err.get("error", err)
        msg = e2.get("message") or e2.get("description") or str(e.code)
        raise ApiError(url.split("?")[0].rsplit("/", 1)[-1], e2.get("code", e.code), msg) from None


class Instagram:
    def __init__(self, token: str, user_id: str):
        self.token, self.user_id = token, str(user_id)

    def _get(self, path: str, **params) -> dict:
        params["access_token"] = self.token
        return _http("GET", f"{IG}/{path}", params)

    def recent_media(self, limit: int = 10) -> list[dict]:
        r = self._get(f"{self.user_id}/media", fields="id,caption,timestamp,permalink,comments_count,media_type",
                      limit=limit)
        return r.get("data", [])

    def comments(self, media_id: str, limit: int = 50) -> list[dict]:
        """Последние комментарии верхнего уровня (новые первыми)."""
        r = self._get(f"{media_id}/comments", fields="id,text,timestamp,username,from{id,username}", limit=limit)
        out = r.get("data", [])
        for c in out:  # API может отдать автора как from{} или только username
            f = c.setdefault("from", {})
            f.setdefault("username", c.get("username"))
        return out

    def private_reply(self, comment_id: str, text: str) -> dict:
        """Личный ответ в директ на комментарий (1 раз на комментарий, в течение 7 дней)."""
        return _http("POST", f"{IG}/{self.user_id}/messages",
                     body={"recipient": {"comment_id": comment_id}, "message": {"text": text}},
                     headers={"Authorization": f"Bearer {self.token}"})

    def refresh_token(self) -> dict:
        return _http("GET", f"{IG.rsplit('/', 1)[0]}/refresh_access_token",
                     {"grant_type": "ig_refresh_token", "access_token": self.token})


class Bot:
    def __init__(self, token: str):
        self.base = f"https://api.telegram.org/bot{token}"

    def call(self, method: str, **params) -> dict:
        r = _http("POST", f"{self.base}/{method}", body=params, timeout=40)
        if not r.get("ok"):
            raise ApiError(method, r.get("error_code"), r.get("description", ""))
        return r["result"]
