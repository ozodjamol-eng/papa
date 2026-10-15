"""Telegram: заявки на вступление в канал → приветствие в личку → одобрение.
Важно: написать человеку бот может, пока заявка не обработана (до 5 минут после неё),
поэтому сначала приветствие, потом одобрение."""
from __future__ import annotations

from . import store
from .api import ApiError


def handle_update(bot, db, cfg: dict, upd: dict, at: str, log=print) -> str | None:
    r = upd.get("chat_join_request")
    if not r:
        return None
    chat_id = r["chat"]["id"]
    ch = next((c for c in cfg.get("channels", []) if int(c["chat_id"]) == int(chat_id)), None)
    if ch is None:
        return "чужой чат"
    user = r["from"]
    invite = (r.get("invite_link") or {}).get("name")
    welcomed = approved = False
    detail = ""
    try:
        bot.call("sendMessage", chat_id=r["user_chat_id"], text=ch["welcome"], disable_web_page_preview=True)
        welcomed = True
    except ApiError as e:
        detail = f"welcome: {e}"
    if ch.get("approve", True):
        try:
            bot.call("approveChatJoinRequest", chat_id=chat_id, user_id=user["id"])
            approved = True
        except ApiError as e:
            detail += f" approve: {e}"
    store.add_join(db, chat_id, user["id"], invite, at, welcomed, approved, detail)
    log(f"заявка в {ch.get('title', chat_id)} по ссылке «{invite}»: приветствие={welcomed} одобрено={approved}")
    return "ok"


def poll_once(bot, db, cfg: dict, at: str, timeout: int = 25, log=print) -> int:
    offset = int(store.kv_get(db, "tg_offset", "0"))
    ups = bot.call("getUpdates", offset=offset, timeout=timeout, allowed_updates=["chat_join_request"])
    for u in ups:
        handle_update(bot, db, cfg, u, at, log)
        store.kv_set(db, "tg_offset", str(u["update_id"] + 1))
    return len(ups)


def make_invite(bot, chat_id, name: str) -> str:
    """Ссылка-приглашение с заявкой (для подсчёта источника и приветствия)."""
    r = bot.call("createChatInviteLink", chat_id=chat_id, name=name[:32], creates_join_request=True)
    return r["invite_link"]
