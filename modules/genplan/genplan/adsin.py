"""💰 31.10 «Реклама под ключ», этап 2 (план выходных владельца: «реклама без меня — только ✅ и деньги»).

ИИ-ассистент собрал заказ → владелец нажал ✅ → в папке /var/lib/papa-ads-inbox/order-N лежит meta.json + файлы.
Здесь бот-пульт Хўжаобода сам загружает рекламу владельцу в чат пульта, заводит карточку и сразу открывает экран
«📣 Реклама — когда выпустить?». Владельцу остаётся одно касание: время. Дальше — как обычная реклама пульта
(держится 10 мин наверху, 📅 несколько дней). Папка заказа после этого удаляется."""
from __future__ import annotations

import json
import mimetypes
import os
import shutil
import uuid
import urllib.request
from pathlib import Path

INBOX = Path(os.environ.get("PAPA_ADS_INBOX", "/var/lib/papa-ads-inbox"))
CHANNEL = "xojaobod"                                       # реклама — только Хўжаобод (решение 20.10)


def _multipart(fields: dict, files: dict) -> tuple[bytes, str]:
    b = uuid.uuid4().hex
    out = bytearray()
    for k, v in fields.items():
        out += f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n".encode() + str(v).encode() + b"\r\n"
    for k, (name, data) in files.items():
        ct = mimetypes.guess_type(name)[0] or "application/octet-stream"
        out += (f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{name}\"\r\n"
                f"Content-Type: {ct}\r\n\r\n").encode() + data + b"\r\n"
    out += f"--{b}--\r\n".encode()
    return bytes(out), b


def upload(token: str, method: str, fields: dict, files: dict):
    """Bot API с файлами (обычный вызов пульта шлёт только JSON). Токен в ошибки не попадает."""
    body, b = _multipart(fields, files)
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            out = json.loads(r.read())
    except urllib.error.HTTPError as e:
        out = json.loads(e.read() or b"{}")
    if not out.get("ok"):
        raise RuntimeError(f"{method}: {out.get('description')}")
    return out["result"]


def send_pack(token: str, chat: int, d: Path, meta: dict, up=upload) -> list[dict]:
    """Реклама владельцу в чат пульта как есть: один файл — с подписью; 2–3 — альбомом; без файлов — текст."""
    media = [m for m in meta.get("media") or [] if (d / m["file"]).is_file()]
    text = meta.get("text") or ""
    if not media:
        return [up(token, "sendMessage", {"chat_id": chat, "text": text or "(матн йўқ)"}, {})]
    if len(media) == 1:
        m = media[0]
        method, field = {"photo": ("sendPhoto", "photo"), "video": ("sendVideo", "video"),
                         "animation": ("sendAnimation", "animation")}.get(m["kind"], ("sendDocument", "document"))
        return [up(token, method, {"chat_id": chat, "caption": text[:1024]}, {field: (m["file"], (d / m["file"]).read_bytes())})]
    group, files = [], {}
    for i, m in enumerate(media[:10]):
        k = f"f{i}"
        item = {"type": m["kind"] if m["kind"] in ("photo", "video") else "document", "media": f"attach://{k}"}
        if i == 0 and text:
            item["caption"] = text[:1024]
        group.append(item)
        files[k] = (m["file"], (d / m["file"]).read_bytes())
    return up(token, "sendMediaGroup", {"chat_id": chat, "media": json.dumps(group)}, files)


def note_of(meta: dict) -> str:
    opts = [f"{meta.get('days') or 1} кун"] + (["кечки 18–20"] if meta.get("evening") else []) + \
           (["тепада қадаб"] if meta.get("pin") else [])
    return (f"💰 Заказ ИИ-ассистента · {meta.get('client') or '—'}\n📦 {meta.get('what') or '—'} · "
            + " · ".join(opts) + (f" · 🗓 {meta['date']}" if meta.get("date") else "")
            + ("\n📅 Несколько дней — кнопкой после выбора времени" if int(meta.get("days") or 1) > 1 else ""))


def scan(bot, token: str, db, cfg: dict, owners: list[int], inbox: Path = INBOX, up=upload, log=print) -> int:
    """Каждый проход GENPLAN: готовые заказы → карточка рекламы в пульте Хўжаобода. Возвращает число заказов."""
    from . import hub, store
    if not owners or not inbox.is_dir() or CHANNEL not in cfg.get("channels", {}):
        return 0
    n = 0
    for d in sorted(inbox.glob("order-*")):
        mf = d / "meta.json"
        if not mf.is_file():
            continue                                        # ещё пишется
        try:
            meta = json.loads(mf.read_text(encoding="utf-8"))
            msgs = send_pack(token, owners[0], d, meta, up=up)
            hub.direct(bot, db, cfg, owners, owners[0], msgs, channel=CHANNEL)
            from . import bots
            m = db.execute("SELECT * FROM materials WHERE via=? ORDER BY id DESC LIMIT 1", (bots.key_of(bot),)).fetchone()
            if m:
                store.update(db, m["id"], status="draft", scheduled_at=None, auto=0, stock=0)   # не авто-слот: время — владелец
                store.kv_set(db, f"ad_order_{m['id']}", json.dumps({k: meta.get(k) for k in
                             ("id", "client_chat", "bc", "client", "days", "evening", "pin")}, ensure_ascii=False))
                t, kb = hub.ad_screen(db, cfg, m["id"], hub._now())
                hub._edit(bot, owners[0], m["owner_msg"], note_of(meta) + "\n\n" + t, kb)
            n += 1
            log(f"💰 заказ {meta.get('id')} → пульт Хўжаобода")
        except Exception as e:  # noqa: BLE001 — один плохой заказ не держит остальные
            log(f"💰 заказ {d.name}: {type(e).__name__}: {str(e)[:150]}")
            bad = d.with_name(d.name.replace("order-", "bad-"))
            shutil.rmtree(bad, ignore_errors=True)
            d.rename(bad)
            continue
        shutil.rmtree(d, ignore_errors=True)
    return n


def published(db, cfg: dict, mid: int, msg_id, inbox: Path = INBOX) -> bool:
    """Реклама из заказа вышла (первый раз) → файл для ИИ-ассистента: он сам скажет клиенту «чиқди ✅» со ссылкой."""
    from . import store
    raw = store.kv_get(db, f"ad_order_{mid}")
    if not raw or store.kv_get(db, f"ad_order_done_{mid}") or not inbox.is_dir():
        return False
    o = json.loads(raw)
    user = ((cfg.get("channels") or {}).get(CHANNEL) or {}).get("username") or ""
    link = f"https://t.me/{user}/{msg_id}" if user and isinstance(msg_id, int) else (f"https://t.me/{user}" if user else "")
    f = inbox / f"done-{o.get('id')}.json"
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps({**o, "link": link}, ensure_ascii=False), encoding="utf-8")
    os.chmod(tmp, 0o660)
    os.replace(tmp, f)
    store.kv_set(db, f"ad_order_done_{mid}", "1")
    return True
