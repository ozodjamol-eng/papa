"""Сохранить токен Instagram для Voronka и проверить его.
Токен вводится скрыто, пишется только в /etc/papa-voronka/instagram.env (0600), на экран не выводится."""
import getpass
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENV = Path(os.environ.get("PAPA_VORONKA_IG_ENV", "/etc/papa-voronka/instagram.env"))   # GOLD WATER — свой файл
API = "https://graph.instagram.com/v24.0"


FIELDS = "user_id,username,account_type,followers_count,media_count"


def _get(url: str, headers: dict) -> dict:
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as r:
        return json.loads(r.read())


def me(token: str) -> dict:
    # сначала заголовком; если API не принимает — параметром (HTTPS, нигде не сохраняется)
    try:
        return _get(f"{API}/me?fields={FIELDS}", {"Authorization": f"Bearer {token}"})
    except urllib.error.HTTPError:
        pass
    try:
        q = urllib.parse.urlencode({"fields": FIELDS, "access_token": token})
        return _get(f"{API}/me?{q}", {})
    except urllib.error.HTTPError as e:
        err = json.loads(e.read() or b"{}").get("error", {})
        raise SystemExit(f"TOKEN_BAD: {err.get('message', e.code)}")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        env = dict(l.split("=", 1) for l in ENV.read_text().splitlines() if "=" in l)
        token = env["IG_TOKEN"]
    else:
        token = getpass.getpass("Вставьте токен Instagram (не виден) и нажмите Enter: ").strip()
        if len(token) < 50:
            raise SystemExit("TOKEN_TOO_SHORT: вставьте токен целиком")
    d = me(token)
    if sys.argv[1:] != ["check"]:
        ENV.parent.mkdir(mode=0o700, exist_ok=True)
        old = os.umask(0o077)
        try:
            ENV.write_text(f"IG_TOKEN={token}\nIG_USER_ID={d.get('user_id', d.get('id'))}\n"
                           f"IG_USERNAME={d.get('username')}\n")
        finally:
            os.umask(old)
        os.chmod(ENV, 0o600)
    print(f"аккаунт: @{d.get('username')}  тип: {d.get('account_type')}  "
          f"подписчики: {d.get('followers_count')}  публикаций: {d.get('media_count')}")
    print("TOKEN_OK")


if __name__ == "__main__":
    main()
