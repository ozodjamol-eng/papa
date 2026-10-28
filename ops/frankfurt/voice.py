"""«Голос» PAPA: ElevenLabs — поиск голосов в библиотеке, клон по образцу, озвучка образцов.
Задание (voice/job.json + аудио) кладёт ассистент в ветку «voice». Ключ — /root/.elevenlabs.env (владелец ввёл сам).
Ничего не публикует. Готовые mp3 кладёт в out/ — voice.sh отправляет их в ветку voice-out (deploy-key), ассистент забирает.

job.json:
{"steps": [
  {"do": "credits"},
  {"do": "search", "params": {"language": "uz", "gender": "male", "page_size": 40}},
  {"do": "clone", "name": "PAPA-ref", "files": ["ref.mp3"], "description": "..."},
  {"do": "design", "name": "D", "description": "...", "text": "(100–1000 знаков)", "model": "eleven_ttv_v3"},
  {"do": "sts", "name": "S", "voice_id": "...", "file": "rec.mp3", "settings": {"stability": 0.5, "similarity_boost": 0.85}},
  {"do": "tts", "name": "A", "voice_id": "...|$clone:PAPA-ref", "public_owner_id": "(для голоса из библиотеки)",
   "text": "...", "model": "eleven_v3", "settings": {"stability": 0.4, "similarity_boost": 0.8, "style": 0.3},
   "format": "mp3_44100_64"}
]}"""
import json, os, sys, urllib.error, urllib.parse, urllib.request, uuid
from pathlib import Path

API = "https://api.elevenlabs.io"


def key():
    k = os.environ.get("ELEVENLABS_API_KEY")
    if not k:
        for p in ("/root/.elevenlabs.env", "/etc/papa-genplan/elevenlabs.env"):
            if Path(p).exists():
                for line in Path(p).read_text().splitlines():
                    if line.startswith("ELEVENLABS_API_KEY="):
                        k = line.split("=", 1)[1].strip()
    if not k:
        sys.exit("NO_ELEVENLABS_KEY")
    return k


def call(method, path, k, body=None, headers=None, raw=False, timeout=180):
    h = {"xi-api-key": k}
    h.update(headers or {})
    if isinstance(body, (dict, list)):
        body = json.dumps(body).encode()
        h["content-type"] = "application/json"
    req = urllib.request.Request(API + path, data=body, headers=h, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=timeout).read()
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read()[:400].decode(errors='replace')}"
    return (r if raw else json.loads(r or b"{}")), None


def multipart(fields, files):
    b = uuid.uuid4().hex
    out = []
    for n, v in fields:
        out += [f"--{b}\r\nContent-Disposition: form-data; name=\"{n}\"\r\n\r\n{v}\r\n".encode()]
    for n, p in files:
        out += [f"--{b}\r\nContent-Disposition: form-data; name=\"{n}\"; filename=\"{Path(p).name}\"\r\n"
                f"Content-Type: audio/mpeg\r\n\r\n".encode(), Path(p).read_bytes(), b"\r\n"]
    out.append(f"--{b}--\r\n".encode())
    return b"".join(out), {"content-type": f"multipart/form-data; boundary={b}"}


def main(job_dir, out_dir):
    k = key()
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    job = json.loads((Path(job_dir) / "job.json").read_text())
    clones = {}
    owners = {}  # voice_id → public_owner_id из поиска (id автора маскируется в выводе — берём отсюда)
    for st in job["steps"]:
        do = st["do"]
        print(f"===== {do} {st.get('name', '')} =====", flush=True)
        if do == "credits":
            d, err = call("GET", "/v1/user/subscription", k)
            print(err or f"tier={d.get('tier')} used={d.get('character_count')} limit={d.get('character_limit')} "
                         f"clones={d.get('voice_add_edit_counter', '?')}/{d.get('voice_limit')} "
                         f"reset={d.get('next_character_count_reset_unix')}")
        elif do == "search":
            q = urllib.parse.urlencode(st.get("params", {}))
            d, err = call("GET", f"/v1/shared-voices?{q}", k)
            if err:
                print(err); continue
            for v in d.get("voices", []):
                owners[v.get("voice_id")] = v.get("public_owner_id")
                print(json.dumps({x: v.get(x) for x in ("name", "voice_id", "public_owner_id", "language", "accent",
                                                       "gender", "age", "descriptive", "use_case", "category",
                                                       "cloned_by_count", "usage_character_count_1y")},
                                 ensure_ascii=False), "|", (v.get("description") or "")[:140].replace("\n", " "))
        elif do == "clone":
            body, h = multipart([("name", st["name"]), ("description", st.get("description", "")),
                                 ("remove_background_noise", "false")],
                                [("files", str(Path(job_dir) / f)) for f in st["files"]])
            d, err = call("POST", "/v1/voices/add", k, body, h)
            if err:
                print(err); continue
            clones[st["name"]] = d.get("voice_id")
            print("voice_id", d.get("voice_id"))
        elif do == "tts":
            vid = st["voice_id"]
            if vid.startswith("$clone:"):
                vid = clones.get(vid[7:]) or ""
                if not vid:
                    print("NO_CLONE"); continue
            owner = st.get("public_owner_id")
            if owner == "auto":
                owner = owners.get(vid)
            if owner:
                _, err = call("POST", f"/v1/voices/add/{owner}/{vid}", k,
                              {"new_name": f"PAPA-{st['name']}"})
                if err and "already" not in err.lower():
                    print("add:", err)
            fmt = st.get("format", "mp3_44100_64")
            body = {"text": st["text"], "model_id": st.get("model", "eleven_v3")}
            if st.get("settings"):
                body["voice_settings"] = st["settings"]
            if st.get("language_code"):
                body["language_code"] = st["language_code"]
            audio, err = call("POST", f"/v1/text-to-speech/{vid}?output_format={fmt}", k, body, raw=True, timeout=300)
            if err:
                print(err); continue
            (Path(out_dir) / f"{st['name']}.mp3").write_bytes(audio)
            print(f"OK {st['name']}.mp3 {len(audio)//1024} КБ voice_id={vid}")
        elif do == "design":  # 25.10: дизайн голоса с нуля по описанию (не клон) — сохраняем превью mp3
            import base64
            body = {"voice_description": st["description"], "text": st["text"],
                    "model_id": st.get("model", "eleven_ttv_v3"), "auto_generate_text": False}
            if st.get("guidance_scale"):
                body["guidance_scale"] = st["guidance_scale"]
            d, err = call("POST", f"/v1/text-to-voice/design?output_format={st.get('format', 'mp3_44100_128')}", k, body, timeout=300)
            if err:
                print(err); continue
            for i, pv in enumerate(d.get("previews", []), 1):
                name = f"{st['name']}_{i}"
                (Path(out_dir) / f"{name}.mp3").write_bytes(base64.b64decode(pv["audio_base_64"]))
                print(f"OK {name}.mp3 generated_voice_id={pv.get('generated_voice_id')} {pv.get('duration_secs')} с")
        elif do == "save_design":  # сохранить голос из превью design в аккаунт (занимает слот голоса)
            d, err = call("POST", "/v1/text-to-voice", k, {"voice_name": st["name"], "voice_description": st.get("description", ""),
                                                          "generated_voice_id": st["generated_voice_id"]})
            print(err or f"saved voice_id={d.get('voice_id')}")
        elif do == "sts":  # 29.10: Voice Changer — подача (темп, паузы, чувство) из записи, тембр — другого голоса
            vid = st["voice_id"]
            if vid.startswith("$clone:"):
                vid = clones.get(vid[7:]) or ""
            fields = [("model_id", st.get("model", "eleven_multilingual_sts_v2")),
                      ("remove_background_noise", "true" if st.get("denoise", True) else "false")]
            if st.get("settings"):
                fields.append(("voice_settings", json.dumps(st["settings"])))
            body, h = multipart(fields, [("audio", str(Path(job_dir) / st["file"]))])
            fmt = st.get("format", "mp3_44100_128")
            audio, err = call("POST", f"/v1/speech-to-speech/{vid}?output_format={fmt}", k, body, h, raw=True, timeout=300)
            if err:
                print(err); continue
            (Path(out_dir) / f"{st['name']}.mp3").write_bytes(audio)
            print(f"OK {st['name']}.mp3 {len(audio)//1024} КБ voice_id={vid}")
        elif do == "delete_voice":
            _, err = call("DELETE", f"/v1/voices/{st['voice_id']}", k)
            print(err or "deleted")
    caps = {st["name"]: st["caption"] for st in job["steps"] if st.get("do") == "tts" and st.get("caption")}
    if caps:
        (Path(out_dir) / "captions.json").write_text(json.dumps(caps, ensure_ascii=False), encoding="utf-8")
    print("===== done =====")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
