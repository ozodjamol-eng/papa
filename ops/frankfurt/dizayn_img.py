"""Дизайн квартир: заготовка (3D-белая модель по чертежу) + стиль → фото-картинка через Gemini.
Вход: папка с job.json [{"name","prompt","ref"}] и картинками. Выход: <out>/<name>.png. Ничего не публикует."""
import base64, json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

MODELS = [os.environ.get("DIZAYN_IMG_MODEL", "gemini-2.5-flash-image"), "gemini-2.5-flash-image-preview",
          "gemini-3-pro-image-preview"]

def gen_openrouter(key, prompt, ref: Path | None, aspect="16:9"):
    """OpenRouter (31.10 владелец: карта без проверки $50) — та же модель Gemini Flash Image."""
    content = [{"type": "text", "text": prompt}]
    if ref and ref.exists():
        content.append({"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(ref.read_bytes()).decode()}})
    body = {"model": os.environ.get("DIZAYN_OR_MODEL", "google/gemini-2.5-flash-image"),
            "messages": [{"role": "user", "content": content}], "modalities": ["image", "text"],
            "image_config": {"aspect_ratio": aspect}}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            d = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"OpenRouter HTTP {e.code} {e.read()[:300].decode(errors='replace')}")
    for im in ((d.get("choices") or [{}])[0].get("message") or {}).get("images") or []:
        url = (im.get("image_url") or {}).get("url", "")
        if url.startswith("data:"):
            return base64.b64decode(url.split(",", 1)[1]), body["model"]
    raise RuntimeError(f"OpenRouter: нет картинки {str(d)[:300]}")


def gen(key, prompt, ref: Path | None, aspect="16:9"):
    if os.environ.get("OPENROUTER_API_KEY"):
        return gen_openrouter(os.environ["OPENROUTER_API_KEY"], prompt, ref, aspect)
    parts = [{"text": prompt}]
    if ref and ref.exists():
        parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(ref.read_bytes()).decode()}})
    body = {"contents": [{"parts": parts}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": aspect}}}
    errs = []
    for m in dict.fromkeys(MODELS):
        req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                                     data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": key})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read())
        except urllib.error.HTTPError as e:
            errs.append(f"{m}: HTTP {e.code} {e.read()[:300].decode(errors='replace')}")
            continue
        for p in (d.get("candidates") or [{}])[0].get("content", {}).get("parts", []):
            data = (p.get("inlineData") or p.get("inline_data") or {}).get("data")
            if data:
                return base64.b64decode(data), m
        errs.append(f"{m}: нет картинки в ответе {str(d)[:200]}")
    raise RuntimeError(" | ".join(errs))

def main(src, out):
    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("GEMINI_API_KEY") or sys.exit("нет ключа")
    src, out = Path(src), Path(out); out.mkdir(parents=True, exist_ok=True)
    jobs = json.loads((src / "job.json").read_text(encoding="utf-8"))
    cap = int(os.environ.get("DIZAYN_IMG_CAP", "12"))   # предел за один заход: 12 картинок ≈ $0,5
    if len(jobs) > cap:
        print(f"предел {cap} картинок за заход — лишние пропущены"); jobs = jobs[:cap]
    ok = 0
    for j in jobs:
        try:
            img, m = gen(key, j["prompt"], src / j["ref"] if j.get("ref") else None, j.get("aspect", "16:9"))
            (out / f"{j['name']}.png").write_bytes(img); ok += 1
            print(f"OK {j['name']} ({m}, {len(img)//1024} КБ)", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {j['name']}: {str(e)[:600]}", flush=True)
        time.sleep(4)
    print(f"DIZAYN_IMG {ok}/{len(jobs)}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
