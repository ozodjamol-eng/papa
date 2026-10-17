"""«Уши» PAPA: расшифровка речи из аудио через Gemini (ключ /etc/papa-genplan/ai.env).
Аудио приходит в ветке «ears» репозитория (кладёт ассистент), после расшифровки ветку ассистент очищает.
Вывод — текст в исходном языке + перевод на русский, если речь не русская."""
import base64, json, os, sys, urllib.error, urllib.request
from pathlib import Path

PROMPT = ("Transcribe the speech in this audio verbatim, in its original language and script "
          "(Uzbek may be Latin or Cyrillic — keep what is spoken; Russian in Cyrillic). "
          "Put a rough timestamp [mm:ss] at the start of each sentence or phrase. "
          "Note music or sound effects in brackets briefly. "
          "If the speech is not in Russian, after the transcript add a section 'ПЕРЕВОД:' with a faithful Russian translation. "
          "Output only the transcript (and translation).")


def main(paths):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("NO_GEMINI_KEY: нужен ключ Gemini (задача genplan-gemini-key)")
    models = list(dict.fromkeys([os.environ.get("GEMINI_MODEL", "gemini-flash-latest"), "gemini-flash-latest"]))
    for p in paths:
        data = base64.b64encode(Path(p).read_bytes()).decode()
        body = {"contents": [{"parts": [{"inline_data": {"mime_type": "audio/mp3", "data": data}}, {"text": PROMPT}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8192}}
        print(f"===== {Path(p).name} =====", flush=True)
        for i, m in enumerate(models):
            req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                                         data=json.dumps(body).encode(),
                                         headers={"content-type": "application/json", "x-goog-api-key": key})
            try:
                d = json.loads(urllib.request.urlopen(req, timeout=180).read())
                parts = ((d.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
                txt = "".join(x.get("text", "") for x in parts if not x.get("thought")).strip()
                print(txt or f"(пустой ответ: {str(d)[:300]})")
                break
            except urllib.error.HTTPError as e:
                msg = e.read()[:300]
                if i == len(models) - 1:
                    print(f"ОШИБКА Gemini {e.code} ({m}): {msg!r}" + (" — дневной лимит исчерпан, попробуйте позже" if e.code == 429 else ""))
    print("== HEAR_DONE")


if __name__ == "__main__":
    main(sys.argv[1:])
