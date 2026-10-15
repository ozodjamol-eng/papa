#!/usr/bin/env bash
# Ключ Google Gemini (бесплатный тариф) для Fabrika: перевод и переписывание текстов.
# Ключ вводит владелец — на экране не виден, в чат и репозиторий не попадает. Бот сам выбирает рабочую модель Flash.
set -euo pipefail
read -rsp "Вставьте ключ Gemini (AIza...) и нажмите Enter: " KEY; echo
[[ ${#KEY} -ge 30 ]] || { echo "Ключ слишком короткий — скопируйте целиком"; exit 1; }
MODEL=$(GEMINI_API_KEY="$KEY" python3 - <<'PY'
import json, os, re, urllib.request, urllib.error
key = os.environ["GEMINI_API_KEY"]; base = "https://generativelanguage.googleapis.com/v1beta"
def get(url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                 headers={"content-type": "application/json", "x-goog-api-key": key})
    return json.loads(urllib.request.urlopen(req, timeout=40).read())
try:
    models = get(f"{base}/models?pageSize=200").get("models", [])
except urllib.error.HTTPError as e:
    raise SystemExit(f"KEY_BAD {e.code}")
bad = ("lite", "tts", "live", "image", "audio", "embed", "thinking", "exp", "native", "transcribe", "translate", "robotics", "computer")
cands = [m["name"].split("/", 1)[1] for m in models
         if "generateContent" in m.get("supportedGenerationMethods", []) and "flash" in m["name"]
         and not any(b in m["name"] for b in bad)]
ver = lambda n: [float(x) for x in re.findall(r"\d+(?:\.\d+)?", n)[:1]] or [0]
cands.sort(key=lambda n: (ver(n), "preview" not in n, "latest" in n), reverse=True)
for name in cands[:6] + ["gemini-flash-latest"]:
    try:
        r = get(f"{base}/models/{name}:generateContent",
                {"contents": [{"parts": [{"text": "Translate to Uzbek Cyrillic, one word: Hello"}]}]})
        if r.get("candidates"):
            print(name); break
    except urllib.error.HTTPError:
        continue
else:
    raise SystemExit("NO_MODEL")
PY
) || { echo "GEMINI_FAILED: $MODEL — проверьте ключ"; exit 1; }
echo "модель: $MODEL"
umask 077
touch /etc/papa-genplan/ai.env
grep -v -E '^(GEMINI_API_KEY|GEMINI_MODEL)=' /etc/papa-genplan/ai.env > /etc/papa-genplan/ai.env.new || true
printf 'GEMINI_API_KEY=%s\nGEMINI_MODEL=%s\n' "$KEY" "$MODEL" >> /etc/papa-genplan/ai.env.new
mv /etc/papa-genplan/ai.env.new /etc/papa-genplan/ai.env
chown root:papa-genplan /etc/papa-genplan/ai.env; chmod 0640 /etc/papa-genplan/ai.env
unset KEY
systemctl restart papa-genplan papa-fabrika; sleep 4
echo "genplan: $(systemctl is-active papa-genplan) | fabrika: $(systemctl is-active papa-fabrika)"
echo "== GEMINI_OK"
