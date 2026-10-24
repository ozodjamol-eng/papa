"""«Голос»: образцы mp3 → владельцу в Telegram (личка от PAPA ШТАБ), подпись — из out/captions.json или имя файла."""
import json, os, sys, urllib.request, uuid
from pathlib import Path


def send_audio(token, chat, path: Path, caption: str) -> dict:
    b = uuid.uuid4().hex
    parts = [f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
             for k, v in (("chat_id", str(chat)), ("caption", caption[:1024]), ("title", path.stem), ("performer", "PAPA · Голос"))]
    parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"audio\"; filename=\"{path.name}\"\r\n"
                 f"Content-Type: audio/mpeg\r\n\r\n".encode() + path.read_bytes() + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendAudio", data=b"".join(parts),
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())


def main(folder):
    token = os.environ.get("SHTAB_BOT_TOKEN") or os.environ["GENPLAN_BOT_TOKEN"]
    owners = [int(o) for o in os.environ.get("OWNER_IDS", "").split(",") if o.strip()]
    caps = {}
    cj = Path(folder) / "captions.json"
    if cj.exists():
        caps = json.loads(cj.read_text(encoding="utf-8"))
    for f in sorted(Path(folder).glob("*.mp3")):
        for o in owners:
            r = send_audio(token, o, f, "🎙 " + caps.get(f.stem, f.stem))
            print(f"{f.name} → Telegram: {'OK' if r.get('ok') else r}")


if __name__ == "__main__":
    main(sys.argv[1])
