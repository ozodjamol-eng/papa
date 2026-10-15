"""Главный канал «Katta Davra» (по решению владельца): бывший @XOJAOBODLIKLARIMIZ (3,4 тыс.) →
новое название, юзернейм, описание; @PapaGenplanBot — публикации, @PapaUzBot — приглашения;
ссылка-заявка для панели; папка «PAPA» = Katta Davra + PaparazziUZ. Посты канала не удаляются. Повтор безопасен."""
import asyncio
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, "/opt/papa/modules/razvedka")
from razvedka.telegram import client_from_env  # noqa: E402
from telethon.errors import UsernameNotModifiedError  # noqa: E402
from telethon.tl import types  # noqa: E402
from telethon.tl.functions.channels import (CheckUsernameRequest, EditAdminRequest, EditTitleRequest,  # noqa: E402
                                            UpdateUsernameRequest)
from telethon.tl.functions.chatlists import EditExportedInviteRequest, GetExportedInvitesRequest  # noqa: E402
from telethon.tl.functions.messages import EditChatAboutRequest, GetDialogFiltersRequest, UpdateDialogFilterRequest  # noqa: E402

OLD = "kattadavrauz"   # владелец уже переименовал (было @XOJAOBODLIKLARIMIZ)
TITLE = "КАТТА ДАВРА"
USERNAMES = ["kattadavrauz", "kattadavra", "katta_davra", "kattadavra_uz", "kattadavra24"]
ABOUT = ("🎉 Katta Davra — бутун Ўзбекистон бир даврада!\n"
         "🎵 Мусиқа • 😂 ҳажвия • 💡 фойдали ва қизиқарли видеолар • 🔥 энг долзарб янгиликлар\n"
         "📩 Реклама: @Ozodjamol")
STATE = Path("/etc/papa-genplan/davra.id")


def rd(p):
    p = Path(p)
    return dict(l.split("=", 1) for l in p.read_text().splitlines() if "=" in l) if p.exists() else {}


def bot_api(token, method, **p):
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=json.dumps(p).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}")


async def main():
    gp, vb = rd("/etc/papa-genplan/genplan.env"), rd("/etc/papa-voronka/bot.env")
    c = client_from_env()
    await c.connect()
    try:
        ch = await c.get_entity(int(STATE.read_text()) if STATE.exists() else OLD)
        STATE.write_text(str(int(f"-100{ch.id}")))
        if ch.title != TITLE:
            await c(EditTitleRequest(ch, TITLE))
        print(f"название: {TITLE} (подписчиков {getattr(await c.get_entity(ch), 'participants_count', '?')})")
        uname = (ch.username or "").lower()
        if uname not in USERNAMES:
            for u in USERNAMES:
                try:
                    if await c(CheckUsernameRequest(ch, u)):
                        await c(UpdateUsernameRequest(ch, u))
                        uname = u
                        break
                except UsernameNotModifiedError:
                    uname = u
                    break
                except Exception as e:  # noqa: BLE001 — занят/недоступен → следующий
                    print(f"  @{u}: {type(e).__name__}")
        print(f"USERNAME @{uname}")
        # описание и аватарку владелец ставит сам
        ch = await c.get_entity(ch)
        await c(EditAdminRequest(channel=ch, user_id=await c.get_entity(gp["GENPLAN_BOT_USERNAME"]), rank="PAPA",
                                 admin_rights=types.ChatAdminRights(post_messages=True, edit_messages=True, delete_messages=True)))
        await c(EditAdminRequest(channel=ch, user_id=await c.get_entity(vb["VORONKA_BOT_USERNAME"]), rank="PAPA",
                                 admin_rights=types.ChatAdminRights(invite_users=True)))
        print("боты: @%s — публикации, @%s — приглашения" % (gp["GENPLAN_BOT_USERNAME"], vb["VORONKA_BOT_USERNAME"]))
        await asyncio.sleep(3)
        r = bot_api(vb["VORONKA_BOT_TOKEN"], "createChatInviteLink", chat_id=f"@{uname}", name="panel",
                    creates_join_request=True)
        print(f"PANEL_LINK davra {r['result']['invite_link']}" if r.get("ok") else f"INVITE_FAILED {r.get('description')}")
        # папка «PAPA»: Katta Davra + PaparazziUZ
        try:
            res = await c(GetDialogFiltersRequest())
            flt = next(f for f in getattr(res, "filters", res) if isinstance(f, types.DialogFilterChatlist)
                       and getattr(getattr(f, "title", ""), "text", getattr(f, "title", "")) == "PAPA")
            peers = [await c.get_input_entity(ch), await c.get_input_entity("ozodjamoll")]
            flt.include_peers = peers
            await c(UpdateDialogFilterRequest(id=flt.id, filter=flt))
            inv = await c(GetExportedInvitesRequest(chatlist=types.InputChatlistDialogFilter(filter_id=flt.id)))
            for i in inv.invites:
                await c(EditExportedInviteRequest(chatlist=types.InputChatlistDialogFilter(filter_id=flt.id),
                                                  slug=i.url.rsplit("/", 1)[-1], peers=peers))
            print(f"папка PAPA: КАТТА ДАВРА + PaparazziUZ ({inv.invites[0].url if inv.invites else 'нет ссылки'})")
        except Exception as e:  # noqa: BLE001
            print(f"папка — {type(e).__name__}: {e}")
        print("== DAVRA_DONE")
    finally:
        await c.disconnect()


asyncio.run(main())
