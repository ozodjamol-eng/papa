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


def main(folder):
    token = os.environ["GENPLAN_BOT_TOKEN"]
    owners = [int(o) for o in os.environ.get("OWNER_IDS", "").split(",") if o.strip()]
    vids = sorted(Path(folder).glob("*.mp4"))
    if not vids:
        sys.exit("NO_VIDEO")
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
