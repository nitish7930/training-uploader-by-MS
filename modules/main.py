import os
import re
import sys
import json
import time
import asyncio
import random
import requests
import subprocess
import urllib.parse
import yt_dlp
import cloudscraper
import m3u8
import core as helper
from utils import progress_bar
from vars import API_ID, API_HASH, BOT_TOKEN, OWNER, AUTH_USERS as VARS_AUTH_USERS
from aiohttp import ClientSession
from pyromod import listen
from subprocess import getstatusoutput
from pytube import YouTube
from aiohttp import web

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from pyrogram.errors.exceptions.bad_request_400 import StickerEmojiInvalid
from pyrogram.types.messages_and_media import message
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# ── Owner ID (update this with your actual owner Telegram ID) ────────────────
OWNER = int(os.environ.get("OWNER", "8446475678"))
# ─────────────────────────────────────────────────────────────────────────────

# ── Live-changeable PW API endpoints (/changeapi command updates both) ───────
PWAPI1 = os.environ.get("PWAPI1", "https://anonymouspwplayerrrrr-e0949ecca662.herokuapp.com/pw")
PWAPI2 = os.environ.get("PWAPI2", "https://anonymouspwplayerrrrr-e0949ecca662.herokuapp.com/pw")
# ─────────────────────────────────────────────────────────────────────────────

# ── Persistent Auth Users (JSON-backed, survives bot restart) ────────────────
AUTH_FILE = "auth_users.json"

def _load_auth_users():
    try:
        with open(AUTH_FILE, "r") as f:
            return set(json.load(f))
    except Exception:
        return set()

def _save_auth_users(users: set):
    try:
        with open(AUTH_FILE, "w") as f:
            json.dump(list(users), f)
    except Exception:
        pass

auth_users: set = _load_auth_users()
# ── Also include AUTH_USERS from vars.py (env variable, comma-separated) ─────
auth_users.update(VARS_AUTH_USERS)
# ─────────────────────────────────────────────────────────────────────────────

# ── Persistent Broadcast Users (JSON-backed, survives bot restart) ───────────
BROADCAST_FILE = "broadcast_users.json"

def _load_broadcast_users():
    try:
        with open(BROADCAST_FILE, "r") as f:
            return set(json.load(f))
    except Exception:
        return set()

def _save_broadcast_users(users: set):
    try:
        with open(BROADCAST_FILE, "w") as f:
            json.dump(list(users), f)
    except Exception:
        pass

broadcast_users: set = _load_broadcast_users()
# ─────────────────────────────────────────────────────────────────────────────

# ── Random image list ────────────────────────────────────────────────────────
image_list = [
    "https://graph.org/file/0ffe5c1245b874d4a9bf1-3b2481397f6f380c85.jpg",
    "https://graph.org/file/fae9ed988db074ba5c2f5-ad0a0037cc1bdddbdd.jpg",
    "https://graph.org/file/d24b9bd4d0592a07ad746-de047531c5efafafce.jpg",
    "https://graph.org/file/30b2b264822802cfca0e5-955b8cb8bd0ef5da16.jpg",
    "https://graph.org/file/06d5077e2fe5442e1dbb4-77cb51eecc0aab0608.jpg",
    "https://graph.org/file/47792b7d2acd7ab812e65-ae8e8c3b1071eb2b23.jpg",
    "https://graph.org/file/8ea482ae6278601bae5c5-b1475ac9b0622a6cd7.jpg",
    "https://graph.org/file/648d50f45bf0dd06cd12a-129509de7ebc2c6036.jpg",
    "https://graph.org/file/5312e32455e56860c75cb-b56bedb77b7cf93227.jpg",
    "https://graph.org/file/977afb0f88089d227a19d-443ba34add7d83a182.jpg",
]
# ─────────────────────────────────────────────────────────────────────────────

# ── Failed/Skipped download notice ───────────────────────────────────────────
async def send_failed_notice(bot, chat_id, vid_id, title, url, reason):
    """Send a formatted failed-download notice message."""
    msg = (
        "**🥺𝐒𝐨𝐫𝐫𝐲 𝐢 𝐜𝐚𝐧'𝐭 𝐚𝐛𝐥𝐞 𝐭𝐨 𝐝𝐨𝐰𝐧𝐥𝐨𝐚𝐝 𝐭𝐡𝐢𝐬:**\n\n"
        + "** 🖲️𝐕𝐈𝐃_𝐈𝐃:** `" + str(vid_id).zfill(3) + "`\n\n"
        + "**📝 𝐓𝐢𝐭𝐥𝐞:** " + str(title) + "\n\n"
        + "**𝐔𝐑𝐋:** " + str(url) + "\n\n"
        + "**𝐑𝐞𝐚𝐬𝐨𝐧:** `" + str(reason) + "`\n\n"
        + "__𝐈𝐟 𝐲𝐨𝐮 𝐭𝐡𝐢𝐧𝐤 𝐢𝐭'𝐬 𝐒𝐡𝐨𝐮𝐥𝐝 𝐛𝐞 𝐝𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐞𝐝 𝐬𝐨 𝐜𝐨𝐧𝐭𝐚𝐜𝐭 𝐭𝐨 𝐎𝐰𝐧𝐞𝐫.__"
    )
    try:
        await bot.send_message(
            chat_id,
            msg,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(text="👑𝐎𝐖𝐍𝐄𝐑", url="https://t.me/SmartBoy_ApnaMS")]
            ])
        )
    except Exception as e:
        print(f"send_failed_notice error: {e}")
# ─────────────────────────────────────────────────────────────────────────────

# Initialize the bot
bot = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

my_name = "SK"

cookies_file_path = os.getenv("COOKIES_FILE_PATH", "/modules/youtube_cookies.txt")

# Define aiohttp routes
routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response("https://text-leech-bot-for-render.onrender.com/")

async def web_server():
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    return web_app

async def start_bot():
    await bot.start()
    print("Bot is up and running")

async def stop_bot():
    await bot.stop()

async def main():
    if WEBHOOK:
        # Start the web server
        app_runner = web.AppRunner(await web_server())
        await app_runner.setup()
        site = web.TCPSite(app_runner, "0.0.0.0", PORT)
        await site.start()
        print(f"Web server started on port {PORT}")

    # Start the bot
    await start_bot()

    # Keep the program running
    try:
        while True:
            await bot.polling()  # Run forever, or until interrupted
    except (KeyboardInterrupt, SystemExit):
        await stop_bot()
    

async def start_bot():
    await bot.start()
    print("Bot is up and running")

async def stop_bot():
    await bot.stop()

async def main():
    if WEBHOOK:
        # Start the web server
        app_runner = web.AppRunner(await web_server())
        await app_runner.setup()
        site = web.TCPSite(app_runner, "0.0.0.0", PORT)
        await site.start()
        print(f"Web server started on port {PORT}")

    # Start the bot
    await start_bot()

    # Keep the program running
    try:
        while True:
            await asyncio.sleep(3600)  # Run forever, or until interrupted
    except (KeyboardInterrupt, SystemExit):
        await stop_bot()
        
class Data:
    START = (
        "🌟 Welcome Darling 😘🙈 {0}! 🌟\n\n"
    )
# Define the start command handler
@bot.on_message(filters.command("start"))
async def start(client: Client, msg: Message):
    user = await client.get_me()
    mention = user.mention
    start_message = await client.send_message(
        msg.chat.id,
        Data.START.format(msg.from_user.mention)
    )

    await asyncio.sleep(1)
    await start_message.edit_text(
        Data.START.format(msg.from_user.mention) +
        "Initializing Uploader bot... 🤖\n\n"
        "Progress: [⬜⬜⬜⬜⬜⬜⬜⬜⬜] 0%\n\n"
    )

    await asyncio.sleep(1)
    await start_message.edit_text(
        Data.START.format(msg.from_user.mention) +
        "Loading features... ⏳\n\n"
        "Progress: [🟥🟥🟥⬜⬜⬜⬜⬜⬜] 25%\n\n"
    )
    
    await asyncio.sleep(1)
    await start_message.edit_text(
        Data.START.format(msg.from_user.mention) +
        "This may take a moment, sit back and relax! 🥵\n\n"
        "Progress: [🟧🟧🟧🟧🟧⬜⬜⬜⬜] 50%\n\n"
    )

    await asyncio.sleep(1)
    await start_message.edit_text(
        Data.START.format(msg.from_user.mention) +
        "Checking Bot Status... 🔍\n\n"
        "Progress: [🟨🟨🟨🟨🟨🟨🟨⬜⬜] 75%\n\n"
    )

    await asyncio.sleep(1)
    await start_message.edit_text(
        Data.START.format(msg.from_user.mention) +
        "Checking status Okay... Command is Private Dear.🌚**Bot Made BY @SunilChoudhary08**🔍\n\n"
        "Progress:[🟩🟩🟩🟩🟩🟩🟩🟩🟩] 100%\n\n"
    )

    # ── Register user for broadcast ───────────────────────────────────────────
    broadcast_users.add(msg.chat.id)
    _save_broadcast_users(broadcast_users)
    # ─────────────────────────────────────────────────────────────────────────

    # ── Send random welcome image ─────────────────────────────────────────────
    try:
        if msg.chat.id in auth_users:
            caption = (
                f"🌚 𝐇𝐞𝐥𝐥𝐨 𝐁𝐚𝐛𝐲!\n\n"
                f"⬩➤𝐈𝐦 𝐚 𝐀𝐝𝐚𝐯𝐚𝐧𝐜𝐞𝐝 𝐔𝐩𝐥𝐨𝐚𝐝𝐞𝐫 𝐁𝐨𝐭\n\n"
                f"⬩➤𝐈 𝐂𝐚𝐧 𝐄𝐱𝐭𝐫𝐚𝐜𝐭 𝐕𝐢𝐝𝐞𝐨𝐬 & 𝐏𝐃𝐅𝐬 𝐅𝐫𝐨𝐦 𝐘𝐨𝐮𝐫 𝐓𝐞𝐱𝐭 𝐅𝐢𝐥𝐞 𝐚𝐧𝐝 𝐒𝐞𝐧𝐭 𝐭𝐨 𝐲𝐨𝐮!\n\n"
                f"⬩➤𝐅𝐨𝐫 𝐆𝐮𝐢𝐝𝐞 𝐒𝐞𝐧𝐝 /The08 𝐜𝐨𝐦𝐦𝐚𝐧𝐝 📖\n\n"
                f"⬩➤𝐌𝐚𝐝𝐞 𝐁𝐲 : @SmartBoy_ApnaMS 🗿."
            )
        else:
            caption = (
                f"💘 𝐇𝐞𝐥𝐥𝐨 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 **{msg.from_user.first_name}** !\n\n"
                f"⬩➤𝐈𝐦 𝐚 𝐀𝐝𝐚𝐯𝐚𝐧𝐜𝐞𝐝 𝐔𝐩𝐥𝐨𝐚𝐝𝐞𝐫 𝐁𝐨𝐭\n\n"
                f"⬩➤ 𝐈 𝐂𝐚𝐧 𝐄𝐱𝐭𝐫𝐚𝐜𝐭 𝐕𝐢𝐝𝐞𝐨𝐬 & 𝐏𝐃𝐅𝐬 𝐅𝐫𝐨𝐦 𝐘𝐨𝐮𝐫 𝐓𝐞𝐱𝐭 𝐅𝐢𝐥𝐞 𝐚𝐧𝐝 𝐒𝐞𝐧𝐭 𝐭𝐨 𝐲𝐨𝐮!\n\n"
                f"⬩➤🆓𝐘𝐨𝐮 𝐚𝐫𝐞 𝐜𝐮𝐫𝐫𝐞𝐧𝐭𝐥𝐲 𝐮𝐬𝐢𝐧𝐠 𝐭𝐡𝐞 𝕗𝕣𝕖𝕖 𝐯𝐞𝐫𝐬𝐢𝐨𝐧!\n"
                f"⬩➤𝐖𝐚𝐧𝐭 𝐏𝐫𝐞𝐦𝐢𝐮𝐦? 𝐂𝐨𝐧𝐭𝐚𝐜𝐭: @SmartBoy_ApnaMS 💎\n"
            )
        await client.send_photo(chat_id=msg.chat.id, photo=random.choice(image_list), caption=caption)
    except Exception:
        pass
    # ─────────────────────────────────────────────────────────────────────────

@bot.on_message(filters.command(["stop"]) )
async def restart_handler(_, m):
    await m.reply_text("♥️**STOPPED**♥️", True)
    os.execl(sys.executable, sys.executable, *sys.argv)

# ══════════════════════════════════════════════════════════════════════════════
# ── AUTH SYSTEM (Owner only — JSON-backed, survives restarts) ────────────────
# ══════════════════════════════════════════════════════════════════════════════

@bot.on_message(filters.command(["addauth"]))
async def addauth_handler(client: Client, m: Message):
    if m.from_user.id != OWNER:
        return await m.reply_text("❌ Only owner can use this command.")
    parts = m.text.split()
    if len(parts) < 2:
        return await m.reply_text("Usage: `/addauth <user_id>`")
    try:
        uid = int(parts[1])
    except ValueError:
        return await m.reply_text("❌ Invalid user ID.")
    auth_users.add(uid)
    _save_auth_users(auth_users)
    await m.reply_text(f"✅ User `{uid}` added to authorized list.\n💾 Saved to JSON.")

@bot.on_message(filters.command(["rmauth"]))
async def rmauth_handler(client: Client, m: Message):
    if m.from_user.id != OWNER:
        return await m.reply_text("❌ Only owner can use this command.")
    parts = m.text.split()
    if len(parts) < 2:
        return await m.reply_text("Usage: `/rmauth <user_id>`")
    try:
        uid = int(parts[1])
    except ValueError:
        return await m.reply_text("❌ Invalid user ID.")
    auth_users.discard(uid)
    _save_auth_users(auth_users)
    await m.reply_text(f"✅ User `{uid}` removed from authorized list.\n💾 Saved to JSON.")

@bot.on_message(filters.command(["users"]))
async def allusers_handler(client: Client, m: Message):
    if m.from_user.id != OWNER:
        return await m.reply_text("❌ Only owner can use this command.")
    if not auth_users:
        return await m.reply_text("📋 No authorized users yet.")
    user_list = "\n".join([f"• `{uid}`" for uid in auth_users])
    await m.reply_text(f"👥 **Authorized Users ({len(auth_users)}):**\n\n{user_list}")

# ══════════════════════════════════════════════════════════════════════════════
# ── BROADCAST SYSTEM (Owner only — JSON-backed) ───────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

@bot.on_message(filters.command(["broadcast"]))
async def broadcast_handler(client: Client, m: Message):
    if m.from_user.id != OWNER:
        return await m.reply_text("❌ Only owner can use this command.")
    if not m.reply_to_message:
        return await m.reply_text("📢 Reply to a message to broadcast it.")
    
    total = len(broadcast_users)
    if total == 0:
        return await m.reply_text("No users to broadcast to yet.")
    
    status = await m.reply_text(f"📢 Broadcasting to {total} users...")
    success, failed = 0, 0
    for uid in list(broadcast_users):
        try:
            await m.reply_to_message.copy(uid)
            success += 1
            await asyncio.sleep(0.05)  # flood prevention
        except Exception:
            failed += 1
    await status.edit_text(
        f"📢 **Broadcast Complete!**\n\n"
        f"✅ Success: {success}\n"
        f"❌ Failed: {failed}\n"
        f"👥 Total: {total}"
    )

@bot.on_message(filters.command(["broadusers"]))
async def broadusers_handler(client: Client, m: Message):
    if m.from_user.id != OWNER:
        return await m.reply_text("❌ Only owner can use this command.")
    total = len(broadcast_users)
    if total == 0:
        return await m.reply_text("📋 No broadcast users registered yet.")
    uid_list = "\n".join([f"• `{uid}`" for uid in list(broadcast_users)[:50]])
    suffix = f"\n\n...and {total - 50} more." if total > 50 else ""
    await m.reply_text(f"👥 **Broadcast Users ({total}):**\n\n{uid_list}{suffix}")

# ══════════════════════════════════════════════════════════════════════════════
# ── /changeapi COMMAND (Owner only — updates PWAPI1 & PWAPI2 live) ────────────
# ══════════════════════════════════════════════════════════════════════════════

@bot.on_message(filters.command(["changeapi"]))
async def changeapi_handler(client: Client, m: Message):
    global PWAPI1, PWAPI2
    if m.from_user.id != OWNER:
        return await m.reply_text(
            "To change your Api in your Repository in this format👇🏻.\n\n"
            "/changeapi New Api Here\n**https... to .com/pw** tak Only😁.\n\n"
            "But But But🫡\n"
            "Sorry you are not my owner😒."
        )
    parts = m.text.split(None, 1)
    if len(parts) < 2 or not parts[1].strip():
        return await m.reply_text(
            "Welcome Boss! Change your API in this format:\n\n"
            "/changeapi New Api Here\n**https... to .com/pw** tak Only😁.\n\n"
            "Send me and I will change it.✨"
        )
    new_api = parts[1].strip()
    PWAPI1 = new_api
    PWAPI2 = new_api
    await m.reply_text(
        f"**💕𝐀𝐩𝐢 𝐒𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲 𝐂𝐡𝐚𝐧𝐠𝐞𝐝!**\n\n"
        f"🔗 **𝐍𝐞𝐰 𝐀𝐩𝐢:**\n`{PWAPI1}`\n\n"
        f"⚡ 𝐂𝐡𝐚𝐧𝐠𝐞𝐝 𝐋𝐢𝐯𝐞 𝐍𝐨𝐰 — 𝐍𝐨 𝐁𝐨𝐭 𝐫𝐞𝐬𝐭𝐚𝐫𝐭 𝐧𝐞𝐞𝐝𝐞𝐝 𝐔𝐬𝐞 𝐍𝐨𝐰🚀."
    )

# ══════════════════════════════════════════════════════════════════════════════

@bot.on_message(filters.command(["The08"]) )
async def txt_handler(bot: Client, m: Message):
    # ── Auth Check ────────────────────────────────────────────────────────────
    if m.chat.id not in auth_users:
        return await m.reply_text(
            f"<blockquote>🤣😘 **Please Upgrade Your Plan to Become Owner then Use Me!**\n\n"
            f"__Oopss! You are not a Premium member__\n"
            f"__Want to use this? Contact owner first!__\n\n"
            f"**Your User ID:** `{m.chat.id}`</blockquote>\n\n"
            f"👉 Contact: @SmartBoy_ApnaMS"
        )
    # ─────────────────────────────────────────────────────────────────────────
    editable = await m.reply_text(f"**🔹Hi I am Poweful Lovely TXT Downloader📥 Bot.**\n🔹**Send me the TXT file and Just wait and Watch😚.**")
    input: Message = await bot.listen(editable.chat.id)
    x = await input.download()
    await input.delete(True)
    file_name, ext = os.path.splitext(os.path.basename(x))
    credit = f"@SmartBoy_ApnaMS"
    token = f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MzYxNTE3MzAuMTI2LCJkYXRhIjp7Il9pZCI6IjYzMDRjMmY3Yzc5NjBlMDAxODAwNDQ4NyIsInVzZXJuYW1lIjoiNzc2MTAxNzc3MCIsImZpcnN0TmFtZSI6IkplZXYgbmFyYXlhbiIsImxhc3ROYW1lIjoic2FoIiwib3JnYW5pemF0aW9uIjp7Il9pZCI6IjVlYjM5M2VlOTVmYWI3NDY4YTc5ZDE4OSIsIndlYnNpdGUiOiJwaHlzaWNzd2FsbGFoLmNvbSIsIm5hbWUiOiJQaHlzaWNzd2FsbGFoIn0sImVtYWlsIjoiV1dXLkpFRVZOQVJBWUFOU0FIQEdNQUlMLkNPTSIsInJvbGVzIjpbIjViMjdiZDk2NTg0MmY5NTBhNzc4YzZlZiJdLCJjb3VudHJ5R3JvdXAiOiJJTiIsInR5cGUiOiJVU0VSIn0sImlhdCI6MTczNTU0NjkzMH0.iImf90mFu_cI-xINBv4t0jVz-rWK1zeXOIwIFvkrS0M"
    try:    
        with open(x, "r") as f:
            content = f.read()
        content = content.split("\n")
        links = []
        for i in content:
            links.append(i.split("://", 1))
        os.remove(x)
    except:
        await m.reply_text("Ohho Mera Bachcha 🫂🌚🤣.")
        os.remove(x)
        return
   
    await editable.edit(f"Total links found are **{len(links)}**\n\nSend From where you want to download🤔 initial is **1**")
    input0: Message = await bot.listen(editable.chat.id)
    raw_text = input0.text
    await input0.delete(True)
    try:
        arg = int(raw_text)
    except:
        arg = 1
    await editable.edit("**Enter Your Batch Name or send '/up' for grabing from text filename.😉**")
    input1: Message = await bot.listen(editable.chat.id)
    raw_text0 = input1.text
    await input1.delete(True)
    if raw_text0 == '/up':
        b_name = file_name
    else:
        b_name = raw_text0

    await editable.edit("**Enter resolution.\n Eg : 144, 250, 360, 480, 720 or 1080😚**")
    input2: Message = await bot.listen(editable.chat.id)
    raw_text2 = input2.text
    await input2.delete(True)
    try:
        if raw_text2 == "144":
            res = "256x144"
        elif raw_text2 == "240":
            res = "426x240"
        elif raw_text2 == "360":
            res = "640x360"
        elif raw_text2 == "480":
            res = "854x480"
        elif raw_text2 == "720":
            res = "1280x720"
        elif raw_text2 == "1080":
            res = "1920x1080" 
        else: 
            res = "UN"
    except Exception:
            res = "UN"
    
    await editable.edit("**Enter Your Name or send '/SK' for use default.🌚\n Eg :@SunilChoudhary08 **")
    input3: Message = await bot.listen(editable.chat.id)
    raw_text3 = input3.text
    await input3.delete(True)
    if raw_text3 == '/SK':
        CR = credit
    else:
        CR = raw_text3
        
    await editable.edit("**Enter Your PW Token For 𝐌𝐏𝐃 𝐔𝐑𝐋  or send '/VIP' for use default🎀**")
    input4: Message = await bot.listen(editable.chat.id)
    raw_text4 = input4.text
    await input4.delete(True)
    if raw_text4 == '/VIP':
        MR = token
    else:
        MR = raw_text4
        
    await editable.edit("Now send the **Thumb url**\n**Eg: Who's End With .jpg** ``\n\nor Send `no`")
    input6 = message = await bot.listen(editable.chat.id)
    raw_text6 = input6.text
    await input6.delete(True)
    await editable.delete()

    thumb = input6.text
    if thumb.startswith("http://") or thumb.startswith("https://"):
        getstatusoutput(f"wget '{thumb}' -O 'thumb.jpg'")
        thumb = "thumb.jpg"
    else:
        thumb == "no"

    count =int(raw_text)    
    try:
        for i in range(arg-1, len(links)):

            Vxy = links[i][1].replace("file/d/","uc?export=download&id=").replace("www.youtube-nocookie.com/embed", "youtu.be").replace("?modestbranding=1", "").replace("/view?usp=sharing","")
            url = "https://" + Vxy
            if "visionias" in url:
                async with ClientSession() as session:
                    async with session.get(url, headers={'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 'Accept-Language': 'en-US,en;q=0.9', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'Pragma': 'no-cache', 'Referer': 'http://www.visionias.in/', 'Sec-Fetch-Dest': 'iframe', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'cross-site', 'Upgrade-Insecure-Requests': '1', 'User-Agent': 'Mozilla/5.0 (Linux; Android 12; RMX2121) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36', 'sec-ch-ua': '"Chromium";v="107", "Not=A?Brand";v="24"', 'sec-ch-ua-mobile': '?1', 'sec-ch-ua-platform': '"Android"',}) as resp:
                        text = await resp.text()
                        url = re.search(r"(https://.*?playlist.m3u8.*?)\"", text).group(1)

            if "acecwply" in url:
                cmd = f'yt-dlp -o "{name}.%(ext)s" -f "bestvideo[height<={raw_text2}]+bestaudio" --hls-prefer-ffmpeg --no-keep-video --remux-video mkv --no-warning "{url}"'
                

            if "visionias" in url:
                async with ClientSession() as session:
                    async with session.get(url, headers={'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 'Accept-Language': 'en-US,en;q=0.9', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'Pragma': 'no-cache', 'Referer': 'http://www.visionias.in/', 'Sec-Fetch-Dest': 'iframe', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'cross-site', 'Upgrade-Insecure-Requests': '1', 'User-Agent': 'Mozilla/5.0 (Linux; Android 12; RMX2121) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36', 'sec-ch-ua': '"Chromium";v="107", "Not=A?Brand";v="24"', 'sec-ch-ua-mobile': '?1', 'sec-ch-ua-platform': '"Android"',}) as resp:
                        text = await resp.text()
                        url = re.search(r"(https://.*?playlist.m3u8.*?)\"", text).group(1)

            elif 'videos.classplusapp' in url or "tencdn.classplusapp" in url or "webvideos.classplusapp.com" in url or "media-cdn-alisg.classplusapp.com" in url or "videos.classplusapp" in url or "videos.classplusapp.com" in url or "media-cdn-a.classplusapp" in url or "media-cdn.classplusapp" in url:
             url = requests.get(f'https://api.classplusapp.com/cams/uploader/video/jw-signed-url?url={url}', headers={'x-access-token': 'eyJjb3Vyc2VJZCI6IjQ1NjY4NyIsInR1dG9ySWQiOm51bGwsIm9yZ0lkIjo0ODA2MTksImNhdGVnb3J5SWQiOm51bGx9r'}).json()['url']

            
            #elif '/master.mpd' in url:
             #id =  url.split("/")[-2]
             #url = f"https://player.muftukmall.site/?id={id}"
            #elif '/master.mpd' in url:
             #id =  url.split("/")[-2]
             #url = f"https://anonymouspwplayerrr-31d6706c7a3b.herokuapp.com/pw?url={url}?token={raw_text4}"
            #url = f"https://madxapi-d0cbf6ac738c.herokuapp.com/{id}/master.m3u8?token={raw_text4}"
            elif"d1d34p8vz63oiq" in url or "sec1.pw.live" in url:
             url = f"{PWAPI1}?url={url}&token={raw_text4}"
                     
                                                         
            name1 = links[i][0].replace("\t", "").replace(":", "").replace("/", "").replace("+", "").replace("#", "").replace("|", "").replace("@", "").replace("*", "").replace(".", "").replace("https", "").replace("http", "").strip()
            name = f'{str(count).zfill(3)}) {name1[:60]} {my_name}'
                      
            
            if "edge.api.brightcove.com" in url:
                bcov = 'bcov_auth=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpYXQiOjE3MjQyMzg3OTEsImNvbiI6eyJpc0FkbWluIjpmYWxzZSwiYXVzZXIiOiJVMFZ6TkdGU2NuQlZjR3h5TkZwV09FYzBURGxOZHowOSIsImlkIjoiZEUxbmNuZFBNblJqVEROVmFWTlFWbXhRTkhoS2R6MDkiLCJmaXJzdF9uYW1lIjoiYVcxV05ITjVSemR6Vm10ak1WUlBSRkF5ZVNzM1VUMDkiLCJlbWFpbCI6Ik5Ga3hNVWhxUXpRNFJ6VlhiR0ppWTJoUk0wMVdNR0pVTlU5clJXSkRWbXRMTTBSU2FHRnhURTFTUlQwPSIsInBob25lIjoiVUhVMFZrOWFTbmQ1ZVcwd1pqUTViRzVSYVc5aGR6MDkiLCJhdmF0YXIiOiJLM1ZzY1M4elMwcDBRbmxrYms4M1JEbHZla05pVVQwOSIsInJlZmVycmFsX2NvZGUiOiJOalZFYzBkM1IyNTBSM3B3VUZWbVRtbHFRVXAwVVQwOSIsImRldmljZV90eXBlIjoiYW5kcm9pZCIsImRldmljZV92ZXJzaW9uIjoiUShBbmRyb2lkIDEwLjApIiwiZGV2aWNlX21vZGVsIjoiU2Ftc3VuZyBTTS1TOTE4QiIsInJlbW90ZV9hZGRyIjoiNTQuMjI2LjI1NS4xNjMsIDU0LjIyNi4yNTUuMTYzIn19.snDdd-PbaoC42OUhn5SJaEGxq0VzfdzO49WTmYgTx8ra_Lz66GySZykpd2SxIZCnrKR6-R10F5sUSrKATv1CDk9ruj_ltCjEkcRq8mAqAytDcEBp72-W0Z7DtGi8LdnY7Vd9Kpaf499P-y3-godolS_7ixClcYOnWxe2nSVD5C9c5HkyisrHTvf6NFAuQC_FD3TzByldbPVKK0ag1UnHRavX8MtttjshnRhv5gJs5DQWj4Ir_dkMcJ4JaVZO3z8j0OxVLjnmuaRBujT-1pavsr1CCzjTbAcBvdjUfvzEhObWfA1-Vl5Y4bUgRHhl1U-0hne4-5fF0aouyu71Y6W0eg'
                url = url.split("bcov_auth")[0]+bcov
                
            if "youtu" in url:
                ytf = f"b[height<={raw_text2}][ext=mp4]/bv[height<={raw_text2}][ext=mp4]+ba[ext=m4a]/b[ext=mp4]"
            else:
                ytf = f"b[height<={raw_text2}]/bv[height<={raw_text2}]+ba/b/bv+ba"
            
            if "jw-prod" in url:
                cmd = f'yt-dlp -o "{name}.mp4" "{url}"'

            elif "youtube.com" in url or "youtu.be" in url:
                cmd = f'yt-dlp --cookies youtube_cookies.txt -f "{ytf}" "{url}" -o "{name}".mp4'

            else:
                cmd = f'yt-dlp -f "{ytf}" "{url}" -o "{name}.mp4"'

            try:  
                
                cc = f'**📹 VID_ID: {str(count).zfill(3)}.\n\n📝 Title: {name1} {res}.mkv\n\n<pre><code>📚 Batch Name: {b_name}</code></pre>\n\n📥 Extracted By♠ :\n {CR}\n\n**👑━━━💙 𝑻𝒉𝒆 𝑺𝑲 🩷━━━👑**'
                cc1 = f'**💾 PDF_ID: {str(count).zfill(3)}.\n\n📝 Title: {name1} .pdf\n\n<pre><code>📚 Batch Name: {b_name}</code></pre>\n\n📥 Extracted By♠ :\n {CR}\n\n**👑━━━💚 𝑻𝒉𝒆 𝑺𝑲 ❤️━━━👑**'
                    
                
                if "drive" in url:
                    try:
                        ka = await helper.download(url, name)
                        copy = await bot.send_document(chat_id=m.chat.id,document=ka, caption=cc1)
                        count+=1
                        os.remove(ka)
                        time.sleep(1)
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue

                elif ".pdf" in url:
                    try:
                        await asyncio.sleep(4)
        # Replace spaces with %20 in the URL
                        url = url.replace(" ", "%20")
 
        # Create a cloudscraper session
                        scraper = cloudscraper.create_scraper()

        # Send a GET request to download the PDF
                        response = scraper.get(url)

        # Check if the response status is OK
                        if response.status_code == 200:
            # Write the PDF content to a file
                            with open(f'{name}.pdf', 'wb') as file:
                                file.write(response.content)

            # Send the PDF document
                            await asyncio.sleep(4)
                            copy = await bot.send_document(chat_id=m.chat.id, document=f'{name}.pdf', caption=cc1)
                            count += 1

            # Remove the PDF file after sending
                            os.remove(f'{name}.pdf')
                        else:
                            await m.reply_text(f"Failed to download PDF: {response.status_code} {response.reason}")

                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue

                elif ".pdf" in url:
                    try:
                        cmd = f'yt-dlp -o "{name}.pdf" "{url}"'
                        download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                        os.system(download_cmd)
                        copy = await bot.send_document(chat_id=m.chat.id, document=f'{name}.pdf', caption=cc1)
                        count += 1
                        os.remove(f'{name}.pdf')
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue                       
                          
                else:
                    Show = f"✰🖥️ 𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐢𝐧𝐠 𝗪𝗮𝗶𝘁..🤖🚀 »\n\n📝 Title:- `{name}\n\n📹 𝐐𝐮𝐥𝐢𝐭𝐲 » {raw_text2}`\n\n**🔗 𝐔𝐑𝐋 »** `{url}`\n\n**𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲🧸: ✦ @SunilChoudhary08 ❖"
                    prog = await m.reply_text(Show)
                    res_file = await helper.download_video(url, cmd, name)
                    filename = res_file
                    await prog.delete(True)
                    await helper.send_vid(bot, m, cc, filename, thumb, name, prog)
                    count += 1
                    time.sleep(1)

            except Exception as e:
                await send_failed_notice(bot, m.chat.id, count, name, url, str(e))
                continue

    except Exception as e:
        await m.reply_text(e)
    await m.reply_text("𝐀𝐋𝐋 𝐃𝐎𝐍𝐄 Reaction khud de doge ya kahna padega ✅🔸")

# Advance

@bot.on_message(filters.command(["Sobi"]) )
async def txt_handler(bot: Client, m: Message):
    # ── Auth Check ────────────────────────────────────────────────────────────
    if m.chat.id not in auth_users:
        return await m.reply_text(
            f"<blockquote>🤣😘 **Please Upgrade Your Plan to Become Owner then Use Me!**\n\n"
            f"__Oopss! You are not a Premium member__\n"
            f"__Want to use this? Contact owner first!__\n\n"
            f"**Your User ID:** `{m.chat.id}`</blockquote>\n\n"
            f"👉 Contact: @SmartBoy_ApnaMS"
        )
    # ─────────────────────────────────────────────────────────────────────────
    editable = await m.reply_text(f"**🔹Hi I am Poweful Lovely TXT Downloader📥 Bot.**\n🔹**Send me the TXT file and Just wait and Watch🥵.**")
    input: Message = await bot.listen(editable.chat.id)
    x = await input.download()
    await input.delete(True)
    file_name, ext = os.path.splitext(os.path.basename(x))
    credit = f"@SmartBoy_ApnaMS"
    token = f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MzYxNTE3MzAuMTI2LCJkYXRhIjp7Il9pZCI6IjYzMDRjMmY3Yzc5NjBlMDAxODAwNDQ4NyIsInVzZXJuYW1lIjoiNzc2MTAxNzc3MCIsImZpcnN0TmFtZSI6IkplZXYgbmFyYXlhbiIsImxhc3ROYW1lIjoic2FoIiwib3JnYW5pemF0aW9uIjp7Il9pZCI6IjVlYjM5M2VlOTVmYWI3NDY4YTc5ZDE4OSIsIndlYnNpdGUiOiJwaHlzaWNzd2FsbGFoLmNvbSIsIm5hbWUiOiJQaHlzaWNzd2FsbGFoIn0sImVtYWlsIjoiV1dXLkpFRVZOQVJBWUFOU0FIQEdNQUlMLkNPTSIsInJvbGVzIjpbIjViMjdiZDk2NTg0MmY5NTBhNzc4YzZlZiJdLCJjb3VudHJ5R3JvdXAiOiJJTiIsInR5cGUiOiJVU0VSIn0sImlhdCI6MTczNTU0NjkzMH0.iImf90mFu_cI-xINBv4t0jVz-rWK1zeXOIwIFvkrS0M"
    try:    
        with open(x, "r") as f:
            content = f.read()
        content = content.split("\n")
        links = []
        for i in content:
            links.append(i.split("://", 1))
        os.remove(x)
    except:
        await m.reply_text("Hii Cutie.🌚😘")
        os.remove(x)
        return
   
    await editable.edit(f"Total links found are **{len(links)}**\n\nSend From where you want to download🤔 initial is **1**")
    input0: Message = await bot.listen(editable.chat.id)
    raw_text = input0.text
    await input0.delete(True)
    try:
        arg = int(raw_text)
    except:
        arg = 1
    await editable.edit("**Enter Your Batch Name or send '/SK' for grabing from text filename.🌚**")
    input1: Message = await bot.listen(editable.chat.id)
    raw_text0 = input1.text
    await input1.delete(True)
    if raw_text0 == '/SK':
        b_name = file_name
    else:
        b_name = raw_text0

    await editable.edit("**Enter resolution.\n Eg : 144, 240, 360, 480, 720 or 1080😚**")
    input2: Message = await bot.listen(editable.chat.id)
    raw_text2 = input2.text
    await input2.delete(True)
    try:
        if raw_text2 == "144":
            res = "256x144"
        elif raw_text2 == "240":
            res = "426x240"
        elif raw_text2 == "360":
            res = "640x360"
        elif raw_text2 == "480":
            res = "854x480"
        elif raw_text2 == "720":
            res = "1280x720"
        elif raw_text2 == "1080":
            res = "1920x1080" 
        else: 
            res = "UN"
    except Exception:
            res = "UN"
    
    await editable.edit("**Enter Your Name or send '/SK' for use default.😗\n Eg : @SunilChoudhary08**")
    input3: Message = await bot.listen(editable.chat.id)
    raw_text3 = input3.text
    await input3.delete(True)
    if raw_text3 == '/SK':
        CR = credit
    else:
        CR = raw_text3
        
       
    await editable.edit("Now send the **Thumb url**\n**Eg Who's End With .jpg:** ``\n\nor Send `no`")
    input6 = message = await bot.listen(editable.chat.id)
    raw_text6 = input6.text
    await input6.delete(True)
    await editable.delete()

    thumb = input6.text
    if thumb.startswith("http://") or thumb.startswith("https://files.catbox.moe/mwhput.jpg"):
        getstatusoutput(f"wget '{thumb}' -O 'thumb.jpg'")
        thumb = "thumb.jpg"
    else:
        thumb == "no"

    count =int(raw_text)    
    try:
        for i in range(arg-1, len(links)):

            Vxy = links[i][1].replace("file/d/","uc?export=download&id=").replace("www.youtube-nocookie.com/embed", "youtu.be").replace("?modestbranding=1", "").replace("/view?usp=sharing","")
            url = "https://" + Vxy
            if "visionias" in url:
                async with ClientSession() as session:
                    async with session.get(url, headers={'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 'Accept-Language': 'en-US,en;q=0.9', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'Pragma': 'no-cache', 'Referer': 'http://www.visionias.in/', 'Sec-Fetch-Dest': 'iframe', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'cross-site', 'Upgrade-Insecure-Requests': '1', 'User-Agent': 'Mozilla/5.0 (Linux; Android 12; RMX2121) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36', 'sec-ch-ua': '"Chromium";v="107", "Not=A?Brand";v="24"', 'sec-ch-ua-mobile': '?1', 'sec-ch-ua-platform': '"Android"',}) as resp:
                        text = await resp.text()
                        url = re.search(r"(https://.*?playlist.m3u8.*?)\"", text).group(1)

            if "acecwply" in url:
                cmd = f'yt-dlp -o "{name}.%(ext)s" -f "bestvideo[height<={raw_text2}]+bestaudio" --hls-prefer-ffmpeg --no-keep-video --remux-video mkv --no-warning "{url}"'
                

            if "visionias" in url:
                async with ClientSession() as session:
                    async with session.get(url, headers={'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 'Accept-Language': 'en-US,en;q=0.9', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'Pragma': 'no-cache', 'Referer': 'http://www.visionias.in/', 'Sec-Fetch-Dest': 'iframe', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'cross-site', 'Upgrade-Insecure-Requests': '1', 'User-Agent': 'Mozilla/5.0 (Linux; Android 12; RMX2121) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36', 'sec-ch-ua': '"Chromium";v="107", "Not=A?Brand";v="24"', 'sec-ch-ua-mobile': '?1', 'sec-ch-ua-platform': '"Android"',}) as resp:
                        text = await resp.text()
                        url = re.search(r"(https://.*?playlist.m3u8.*?)\"", text).group(1)

            elif 'videos.classplusapp' in url or "tencdn.classplusapp" in url or "webvideos.classplusapp.com" in url or "media-cdn-alisg.classplusapp.com" in url or "videos.classplusapp" in url or "videos.classplusapp.com" in url or "media-cdn-a.classplusapp" in url or "media-cdn.classplusapp" in url:
             url = requests.get(f'https://api.classplusapp.com/cams/uploader/video/jw-signed-url?url={url}', headers={'x-access-token': 'eyJjb3Vyc2VJZCI6IjQ1NjY4NyIsInR1dG9ySWQiOm51bGwsIm9yZ0lkIjo0ODA2MTksImNhdGVnb3J5SWQiOm51bGx9r'}).json()['url']

            elif "apps-s3-jw-prod.utkarshapp.com" in url:
                if 'enc_plain_mp4' in url:
                    url = url.replace(url.split("/")[-1], res+'.mp4')
                    
                elif 'Key-Pair-Id' in url:
                    url = None
                    
                elif '.m3u8' in url:
                    q = ((m3u8.loads(requests.get(url).text)).data['playlists'][1]['uri']).split("/")[0]
                    x = url.split("/")[5]
                    x = url.replace(x, "")
                    url = ((m3u8.loads(requests.get(url).text)).data['playlists'][1]['uri']).replace(q+"/", x)
                    
            elif '/master.mpd' in url:
             vid_id =  url.split("/")[-2]
             url =  f"{PWAPI2}?url=https://sec1.pw.live/{vid_id}/master.mpd&quality={raw_text2}"

            name1 = links[i][0].replace("\t", "").replace(":", "").replace("/", "").replace("+", "").replace("#", "").replace("|", "").replace("@", "").replace("*", "").replace(".", "").replace("https", "").replace("http", "").strip()
            name = f'{str(count).zfill(3)}) {name1[:60]} {my_name}'
          

            if "edge.api.brightcove.com" in url:
                bcov = 'bcov_auth=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpYXQiOjE3MjQyMzg3OTEsImNvbiI6eyJpc0FkbWluIjpmYWxzZSwiYXVzZXIiOiJVMFZ6TkdGU2NuQlZjR3h5TkZwV09FYzBURGxOZHowOSIsImlkIjoiZEUxbmNuZFBNblJqVEROVmFWTlFWbXhRTkhoS2R6MDkiLCJmaXJzdF9uYW1lIjoiYVcxV05ITjVSemR6Vm10ak1WUlBSRkF5ZVNzM1VUMDkiLCJlbWFpbCI6Ik5Ga3hNVWhxUXpRNFJ6VlhiR0ppWTJoUk0wMVdNR0pVTlU5clJXSkRWbXRMTTBSU2FHRnhURTFTUlQwPSIsInBob25lIjoiVUhVMFZrOWFTbmQ1ZVcwd1pqUTViRzVSYVc5aGR6MDkiLCJhdmF0YXIiOiJLM1ZzY1M4elMwcDBRbmxrYms4M1JEbHZla05pVVQwOSIsInJlZmVycmFsX2NvZGUiOiJOalZFYzBkM1IyNTBSM3B3VUZWbVRtbHFRVXAwVVQwOSIsImRldmljZV90eXBlIjoiYW5kcm9pZCIsImRldmljZV92ZXJzaW9uIjoiUShBbmRyb2lkIDEwLjApIiwiZGV2aWNlX21vZGVsIjoiU2Ftc3VuZyBTTS1TOTE4QiIsInJlbW90ZV9hZGRyIjoiNTQuMjI2LjI1NS4xNjMsIDU0LjIyNi4yNTUuMTYzIn19.snDdd-PbaoC42OUhn5SJaEGxq0VzfdzO49WTmYgTx8ra_Lz66GySZykpd2SxIZCnrKR6-R10F5sUSrKATv1CDk9ruj_ltCjEkcRq8mAqAytDcEBp72-W0Z7DtGi8LdnY7Vd9Kpaf499P-y3-godolS_7ixClcYOnWxe2nSVD5C9c5HkyisrHTvf6NFAuQC_FD3TzByldbPVKK0ag1UnHRavX8MtttjshnRhv5gJs5DQWj4Ir_dkMcJ4JaVZO3z8j0OxVLjnmuaRBujT-1pavsr1CCzjTbAcBvdjUfvzEhObWfA1-Vl5Y4bUgRHhl1U-0hne4-5fF0aouyu71Y6W0eg'
                url = url.split("bcov_auth")[0]+bcov
                
            if "youtu" in url:
                ytf = f"b[height<={raw_text2}][ext=mp4]/bv[height<={raw_text2}][ext=mp4]+ba[ext=m4a]/b[ext=mp4]"
            else:
                ytf = f"b[height<={raw_text2}]/bv[height<={raw_text2}]+ba/b/bv+ba"
            
            if "jw-prod" in url:
                cmd = f'yt-dlp -o "{name}.mp4" "{url}"'

            elif "youtube.com" in url or "youtu.be" in url:
                cmd = f'yt-dlp --cookies youtube_cookies.txt -f "{ytf}" "{url}" -o "{name}".mp4'

            else:
                cmd = f'yt-dlp -f "{ytf}" "{url}" -o "{name}.mp4"'

            try:  
        
                cc = f'**📹 VID_ID: {str(count).zfill(3)}.\n\nTitle: {name1} STUDENTS💛{res}.mkv\n\n📚 Batch Name: {b_name}\n\n📥 Extracted By♠ : {CR}\n\n**👑━━━🩷 𝑻𝒉𝒆 𝑺𝑲 💙━━━👑**'
                cc1 = f'**💾 PDF_ID: {str(count).zfill(3)}.\n\nTitle: {name1} STUDENTS💛.pdf\n\n📚 Batch Name: {b_name}\n\n📥 Extracted By♠ : {CR}\n\n**👑━━━🖤 𝑻𝒉𝒆 𝑺𝑲 🧡━━━👑**'
                    
                
                if "drive" in url:
                    try:
                        ka = await helper.download(url, name)
                        copy = await bot.send_document(chat_id=m.chat.id,document=ka, caption=cc1)
                        count+=1
                        os.remove(ka)
                        time.sleep(1)
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue

                elif ".pdf" in url:
                    try:
                        await asyncio.sleep(4)
        # Replace spaces with %20 in the URL
                        url = url.replace(" ", "%20")
 
        # Create a cloudscraper session
                        scraper = cloudscraper.create_scraper()

        # Send a GET request to download the PDF
                        response = scraper.get(url)

        # Check if the response status is OK
                        if response.status_code == 200:
            # Write the PDF content to a file
                            with open(f'{name}.pdf', 'wb') as file:
                                file.write(response.content)

            # Send the PDF document
                            await asyncio.sleep(4)
                            copy = await bot.send_document(chat_id=m.chat.id, document=f'{name}.pdf', caption=cc1)
                            count += 1

            # Remove the PDF file after sending
                            os.remove(f'{name}.pdf')
                        else:
                            await m.reply_text(f"Failed to download PDF: {response.status_code} {response.reason}")

                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue

                elif ".pdf" in url:
                    try:
                        cmd = f'yt-dlp -o "{name}.pdf" "{url}"'
                        download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                        os.system(download_cmd)
                        copy = await bot.send_document(chat_id=m.chat.id, document=f'{name}.pdf', caption=cc1)
                        count += 1
                        os.remove(f'{name}.pdf')
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue                       
                          
                else:
                    Show = f"✰🖥️𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐢𝐧𝐠 𝗪𝗮𝗶𝘁..🤖🚀»\n\n📝 Title:- `{name}\n\n🖥️ 𝐐𝐮𝐥𝐢𝐭𝐲 » {raw_text2}`\n\n**🔗 𝐔𝐑𝐋 »** `{url}`\n\n**𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲🧸: ✦ @SunilChoudhary08✰"
                    prog = await m.reply_text(Show)
                    res_file = await helper.download_video(url, cmd, name)
                    filename = res_file
                    await prog.delete(True)
                    await helper.send_vid(bot, m, cc, filename, thumb, name, prog)
                    count += 1
                    time.sleep(1)

            except Exception as e:
                await send_failed_notice(bot, m.chat.id, count, name, url, str(e))
                continue

    except Exception as e:
        await m.reply_text(e)
    await m.reply_text("𝐀𝐋𝐋 𝐃𝐎𝐍𝐄 REACTIONS khud doge ya kahna padega .✅🔸")



bot.run()
if __name__ == "__main__":
    asyncio.run(main())
