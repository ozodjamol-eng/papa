"""Ролики «Кечки дайжест» по данным Франкфурта: data/<канал>.json (ветка digest-data) → MP4 <канал>-digest-ДАТА.mp4.
Запуск: python3 make_digest.py DATA_DIR OUT_DIR (нужны node+playwright, ffmpeg, numpy)."""
import json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def build(js: Path, out: Path) -> Path:
    d = json.loads(js.read_text(encoding="utf-8"))
    out.mkdir(parents=True, exist_ok=True)
    name = f"{d['channel']}-digest-{d['day']}"
    raw, wav, mp4 = out / f"{name}.raw.mp4", out / f"{name}.wav", out / f"{name}.mp4"
    subprocess.run([sys.executable, str(HERE / "audio_evening.py"), str(wav)], check=True)
    subprocess.run(["node", str(HERE.parent / "weather" / "render.mjs"), str(HERE / "evening.html"), "video", "60", str(raw)],
                   check=True, env={**os.environ, "WEATHER_JSON": str(js)})
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-i", str(wav), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", str(mp4)], check=True)
    raw.unlink(missing_ok=True); wav.unlink(missing_ok=True)
    return mp4


if __name__ == "__main__":
    data, out = Path(sys.argv[1]), Path(sys.argv[2])
    for js in sorted(data.glob("*.json")):
        print(build(js, out), flush=True)
