"""Ссылка «оба канала сразу»: папка Telegram «PAPA» (через профиль владельца, по его разрешению).
Повторный запуск не создаёт новую папку, а выводит существующую ссылку."""
import asyncio
import sys

sys.path.insert(0, "/opt/papa/modules/razvedka")
from razvedka.telegram import client_from_env  # noqa: E402
from telethon.tl import types  # noqa: E402
from telethon.tl.functions.chatlists import ExportChatlistInviteRequest, GetExportedInvitesRequest  # noqa: E402
from telethon.tl.functions.messages import GetDialogFiltersRequest, UpdateDialogFilterRequest  # noqa: E402

TITLE = "PAPA"
CHATS = ["xojaobodcity24", "ozodjamoll"]


def ttl(f):
    t = getattr(f, "title", "")
    return getattr(t, "text", t)


async def main():
    c = client_from_env()
    await c.connect()
    if not await c.is_user_authorized():
        raise SystemExit("NOT_AUTHORIZED")
    try:
        r = await c(GetDialogFiltersRequest())
        filters = getattr(r, "filters", r)
        mine = next((f for f in filters if isinstance(f, types.DialogFilterChatlist) and ttl(f) == TITLE), None)
        if mine:
            inv = await c(GetExportedInvitesRequest(chatlist=types.InputChatlistDialogFilter(filter_id=mine.id)))
            if inv.invites:
                print(f"FOLDER_LINK {inv.invites[0].url}")
                return
            fid = mine.id
        else:
            used = {getattr(f, "id", 0) for f in filters}
            fid = next(i for i in range(2, 255) if i not in used)
        peers = [await c.get_input_entity(u) for u in CHATS]
        try:
            flt = types.DialogFilterChatlist(id=fid, title=types.TextWithEntities(text=TITLE, entities=[]),
                                             include_peers=peers, pinned_peers=[], emoticon="⭐")
        except TypeError:
            flt = types.DialogFilterChatlist(id=fid, title=TITLE, include_peers=peers, pinned_peers=[], emoticon="⭐")
        await c(UpdateDialogFilterRequest(id=fid, filter=flt))
        res = await c(ExportChatlistInviteRequest(chatlist=types.InputChatlistDialogFilter(filter_id=fid),
                                                  title=TITLE, peers=peers))
        print(f"FOLDER_LINK {res.invite.url}")
    finally:
        await c.disconnect()


asyncio.run(main())
