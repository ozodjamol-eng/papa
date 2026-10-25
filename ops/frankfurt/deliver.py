"""Доставка готовых видео владельцу в Telegram (личка от главного бота PAPA). Видео приходят в ветке «outbox»
(кладёт ассистент): outbox/*.mp4 + одноимённый .txt с подписью. После отправки ассистент очищает ветку."""
import json, os, sys, urllib.request, uuid
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


DOC_EXT = {".mp4", ".mp3", ".wav", ".png", ".jpg", ".jpeg", ".webp", ".pdf", ".zip", ".svg", ".gif", ".mov"}


def main(folder):
    token = os.environ.get("SHTAB_BOT_TOKEN") or os.environ["GENPLAN_BOT_TOKEN"]   # 23.10: видео — из PAPA ШТАБ
    owners = [int(o) for o in os.environ.get("OWNER_IDS", "").split(",") if o.strip()]
    vids = []  # 24.10 правило владельца: видео — документом, оригиналом без сжатия (идут через DOC_EXT)
    docs = sorted(f for f in Path(folder).iterdir() if f.suffix.lower() in DOC_EXT)
    if not vids and not docs:
        sys.exit("NO_VIDEO")
    for d in docs:
        cap = d.with_suffix(".txt").read_text(encoding="utf-8").strip() if d.with_suffix(".txt").exists() else d.stem
        size = d.stat().st_size / 1e6
        if size > 49:
            print(f"{d.name}: {size:.1f} МБ — больше 50 МБ, бот не может отправить"); continue
        for o in owners:
            r = send_document(token, o, d, "📦 " + cap)
            print(f"{d.name} ({size:.1f} МБ) → владельцу: {'OK' if r.get('ok') else r}")
    for v in vids:
        cap = v.with_suffix(".txt").read_text(encoding="utf-8").strip() if v.with_suffix(".txt").exists() else v.stem
        size = v.stat().st_size / 1e6
        if size > 49:
            print(f"{v.name}: {size:.1f} МБ — больше 50 МБ, бот не может отправить"); continue
        for o in owners:
            r = send_video(token, o, v, "🎬 " + cap)
            print(f"{v.name} ({size:.1f} МБ) → владельцу: {'OK' if r.get('ok') else r}")
    print("== DELIVER_DONE")


if __name__ == "__main__":
    main(sys.argv[1])
