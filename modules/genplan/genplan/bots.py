"""Несколько ботов-пультов, один мозг (решение владельца 16.10).

У каждого канала может быть свой бот-пульт (config: channels.X.bot_token_env = "PAPARAZZI_BOT_TOKEN").
Пост, брошенный в бот канала, идёт в этот канал. Главный бот (GENPLAN_BOT_TOKEN) — КАТТА ДАВРА и общие функции.
Ключ бота: "main" или код канала."""
from __future__ import annotations

REG: dict[str, object] = {}       # ключ → функция вызова Bot API
TOKENS: dict[str, str] = {}


def setup(cfg: dict, env: dict, make_bot) -> dict[str, object]:
    REG.clear(); TOKENS.clear()
    REG["main"] = make_bot(env["GENPLAN_BOT_TOKEN"]); TOKENS["main"] = env["GENPLAN_BOT_TOKEN"]
    for c, ch in cfg["channels"].items():
        tok = env.get(ch.get("bot_token_env") or "")
        if tok:
            REG[c] = make_bot(tok); TOKENS[c] = tok
    return REG


def for_channel(channel: str | None, default=None):
    """Бот-пульт канала; нет своего — главный (или default)."""
    return REG.get(channel or "") or default or REG.get("main")


def key_of(bot) -> str:
    return next((k for k, b in REG.items() if b is bot), "main")


def token_of(bot, env: dict) -> str:
    return TOKENS.get(key_of(bot)) or env["GENPLAN_BOT_TOKEN"]


def channel_of(bot) -> str | None:
    """Канал, за который отвечает этот бот (None — главный бот: канал угадывается)."""
    k = key_of(bot)
    return None if k == "main" else k
