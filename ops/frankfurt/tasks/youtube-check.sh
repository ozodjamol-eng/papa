#!/usr/bin/env bash
# 🔎 Только чтение (12.11): годится ли уже имеющийся ключ Google (Gemini) для поиска YouTube (YouTube Data API v3).
# Один поисковый запрос, ключ не печатается. Ничего не скачивает и не публикует.
set -uo pipefail
set -a; . /etc/papa-genplan/ai.env; set +a
python3 -I - <<'P'
import json, os, urllib.error, urllib.parse, urllib.request
k = os.environ.get("GEMINI_API_KEY", "")
if not k:
    print("NO_KEY"); raise SystemExit
q = urllib.parse.urlencode({"part": "snippet", "q": "eurodance 90s hits live", "type": "video", "maxResults": 3, "key": k})
try:
    d = json.load(urllib.request.urlopen("https://www.googleapis.com/youtube/v3/search?" + q, timeout=30))
    print("YOUTUBE_OK найдено:", len(d.get("items", [])))
    for it in d.get("items", []):
        print(" -", it["snippet"]["title"][:70])
except urllib.error.HTTPError as e:
    body = e.read()[:400].decode(errors="replace").replace(k, "***")
    print("YOUTUBE_FAIL", e.code, body)
P
echo "== YOUTUBE_CHECK_DONE"
