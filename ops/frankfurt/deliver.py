"""Доставка готовых видео владельцу в Telegram (личка от главного бота PAPA). Видео приходят в ветке «outbox»
(кладёт ассистент): outbox/*.mp4 + одноимённый .txt с подписью. После отправки ассистент очищает ветку."""
import json, os, sys, urllib.error, urllib.parse, urllib.request, uuid
from pathlib import Path


def send_video(token, chat, path: Path, caption: str) -> dict:
    b = uuid.uuid4().hex
    parts = []
    for k, v in (("chat_id", str(chat)), ("caption", caption[:1024]), ("supports_streaming", "true")):
        parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"video\"; filename=\"{path.name}\"\r\n"
                 f"Content-Type: video/mp4\r\n\r\n".encode() + path.read_bytes() + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendVideo", data=b"".join(parts),
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    return json.loads(urllib.request.urlopen(req, timeout=300).read())


def send_document(token, chat, path: Path, caption: str) -> dict:
    """25.10: картинки/архивы/PDF — документом, оригиналом без сжатия."""
    b = uuid.uuid4().hex
    parts = []
    for k, v in (("chat_id", str(chat)), ("caption", caption[:1024])):
        parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"document\"; filename=\"{path.name}\"\r\n"
                 f"Content-Type: application/octet-stream\r\n\r\n".encode() + path.read_bytes() + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendDocument", data=b"".join(parts),
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    return json.loads(urllib.request.urlopen(req, timeout=300).read())


def send_message(token, chat, text: str) -> dict:
    """30.10: текстовый отчёт (outbox/*.msg) — обычным сообщением, куски по 4000 знаков."""
    r = {}
    for i in range(0, len(text), 4000):
        data = urllib.parse.urlencode({"chat_id": str(chat), "text": text[i:i + 4000],
                                       "disable_web_page_preview": "true"}).encode()
        r = json.loads(urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=60).read())
        if not r.get("ok"):
            return r
    return r


def send_post(token, chat, folder: Path, spec: dict) -> list:
    """31.10 владелец: «готовый вариант пришли мне через бот — я перекину в группу». Пост как в канале:
    фото (не документ) + подпись с жирным (HTML) + опрос. Владелец пересылает «без имени отправителя»."""
    out = []
    if spec.get("photo"):
        path = folder / spec["photo"]
        b = uuid.uuid4().hex
        parts = []
        for k, v in (("chat_id", str(chat)), ("caption", spec.get("caption_html", "")[:1024]), ("parse_mode", "HTML")):
            parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
        parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"{path.name}\"\r\n"
                     f"Content-Type: image/jpeg\r\n\r\n".encode() + path.read_bytes() + b"\r\n")
        parts.append(f"--{b}--\r\n".encode())
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendPhoto", data=b"".join(parts),
                                     headers={"Content-Type": f"multipart/form-data; boundary={b}"})
        out.append(json.loads(urllib.request.urlopen(req, timeout=120).read()))
    poll = spec.get("poll")
    if poll:
        body = json.dumps({"chat_id": chat, "question": poll["question"], "is_anonymous": poll.get("anonymous", True),
                           "options": [{"text": o} for o in poll["options"]]}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendPoll", data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            out.append(json.loads(urllib.request.urlopen(req, timeout=60).read()))
        except urllib.error.HTTPError as e:   # старый Bot API: варианты — строками
            body = json.dumps({"chat_id": chat, "question": poll["question"], "is_anonymous": poll.get("anonymous", True),
                               "options": poll["options"]}).encode()
            req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendPoll", data=body,
                                         headers={"Content-Type": "application/json"})
            out.append(json.loads(urllib.request.urlopen(req, timeout=60).read()))
    return out


DOC_EXT = {".mp4", ".mp3", ".wav", ".png", ".jpg", ".jpeg", ".webp", ".pdf", ".zip", ".svg", ".gif", ".mov"}


def main(folder):
    token = os.environ.get("SHTAB_BOT_TOKEN") or os.environ["GENPLAN_BOT_TOKEN"]   # 23.10: видео — из PAPA ШТАБ
    owners = [int(o) for o in os.environ.get("OWNER_IDS", "").split(",") if o.strip()]
    vids = []  # 24.10 правило владельца: видео — документом, оригиналом без сжатия (идут через DOC_EXT)
    docs = sorted(f for f in Path(folder).iterdir() if f.suffix.lower() in DOC_EXT)
    msgs = sorted(f for f in Path(folder).iterdir() if f.suffix.lower() == ".msg")
    posts = sorted(f for f in Path(folder).iterdir() if f.name.endswith(".post.json"))
    used = {json.loads(p.read_text(encoding="utf-8")).get("photo") for p in posts}
    docs = [d for d in docs if d.name not in used]      # фото поста идёт фото, не документом
    if not vids and not docs and not msgs and not posts:
        sys.exit("NO_VIDEO")
    routes = {}  # 30.10: отчёты разведчиков рынка — в свои каналы (razvedka-rynok-channels), иначе владельцу в личку
    env = Path("/etc/papa-genplan/razvedka-rynok.env")
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                routes[k.strip()] = int(v.strip())
    for p in posts:
        spec = json.loads(p.read_text(encoding="utf-8"))
        for o in owners:
            rs = send_post(token, o, Path(folder), spec)
            print(f"{p.name} (готовый пост) → владельцу: {'OK' if rs and all(r.get('ok') for r in rs) else rs}")
    for m in msgs:
        text = m.read_text(encoding="utf-8").strip()
        key = {"razvedka-voda": "RAZVEDKA_VODA_CHAT", "razvedka-mebel": "RAZVEDKA_MEBEL_CHAT"}.get(m.stem)
        targets = [routes[key]] if key in routes else owners
        for o in targets:
            r = send_message(token, o, text)
            print(f"{m.name} (текст) → {'канал' if key in routes else 'владельцу'}: {'OK' if r.get('ok') else r}")
    for d in docs:
        cap = d.with_suffix(".txt").read_text(encoding="utf-8").strip() if d.with_suffix(".txt").exists() else d.stem
        size = d.stat().st_size / 1048576
        if size > 49.9:
            print(f"{d.name}: {size:.1f} МБ — больше 50 МБ, бот не может отправить"); continue
        for o in owners:
            r = send_document(token, o, d, "📦 " + cap)
            print(f"{d.name} ({size:.1f} МБ) → владельцу: {'OK' if r.get('ok') else r}")
    for v in vids:
        cap = v.with_suffix(".txt").read_text(encoding="utf-8").strip() if v.with_suffix(".txt").exists() else v.stem
        size = v.stat().st_size / 1048576
        if size > 49.9:
            print(f"{v.name}: {size:.1f} МБ — больше 50 МБ, бот не может отправить"); continue
        for o in owners:
            r = send_video(token, o, v, "🎬 " + cap)
            print(f"{v.name} ({size:.1f} МБ) → владельцу: {'OK' if r.get('ok') else r}")
    print("== DELIVER_DONE")


if __name__ == "__main__":
    main(sys.argv[1])
