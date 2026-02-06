import os
import time
import logging
import requests
import telebot
from telebot import types
from urllib.parse import quote_plus

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
XAPIVERSE_KEY = os.getenv("XAPIVERSE_KEY")

FORCE_CHANNEL = "@terabox_directlinks"
SOURCE_GROUP = "@terabox_movies_hub0"
TARGET_CHANNEL = "@terabox_directlinks"

PLAYER_BASE = "https://teraplayer979.github.io/stream-player/"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not BOT_TOKEN or not XAPIVERSE_KEY:
    logger.error("Missing BOT_TOKEN or XAPIVERSE_KEY")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ---------------- HELPERS ----------------

def check_sub(user_id):
    try:
        member = bot.get_chat_member(FORCE_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def get_data(url):
    try:
        api = "https://xapiverse.com/api/terabox"
        headers = {
            "Content-Type": "application/json",
            "xAPIverse-Key": XAPIVERSE_KEY
        }
        r = requests.post(api, headers=headers, json={"url": url}, timeout=40)
        if r.status_code == 200:
            data = r.json().get("list", [])
            if data:
                f = data[0]
                fast = f.get("fast_stream_url", {})
                stream = (
                    fast.get("720p") or
                    fast.get("480p") or
                    fast.get("360p") or
                    f.get("stream_url") or
                    f.get("download_link")
                )
                return {
                    "name": f.get("name", "Movie"),
                    "stream": stream,
                    "download": f.get("download_link")
                }
    except Exception as e:
        logger.error(e)
    return None

# ---------------- GROUP AUTO POST ----------------
@bot.message_handler(func=lambda m: m.chat.type in ["group", "supergroup"])
def group_handler(message):
    if not message.text:
        return

    if message.chat.username != SOURCE_GROUP.replace("@", ""):
        return

    text = message.text.strip()
    if "terabox" not in text and "1024tera" not in text:
        return

    data = get_data(text)
    if not data:
        return

    encoded = quote_plus(data["stream"])
    player = f"{PLAYER_BASE}?url={encoded}"

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("▶️ Watch Online", url=player))

    if data["download"]:
        markup.add(types.InlineKeyboardButton("⬇️ Download", url=data["download"]))

    bot.send_message(
        TARGET_CHANNEL,
        f"🎬 {data['name']}\n\n▶️ Watch Online\n⬇️ Download",
        reply_markup=markup
    )

# ---------------- PRIVATE HANDLER ----------------
@bot.message_handler(func=lambda m: m.chat.type == "private")
def private_handler(message):
    if not message.text:
        return

    user_id = message.from_user.id
    text = message.text.strip()

    if not check_sub(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Join Channel", url="https://t.me/terabox_directlinks"))
        bot.reply_to(message, "Join our channel first.", reply_markup=markup)
        return

    if "terabox" not in text and "1024tera" not in text:
        return

    msg = bot.reply_to(message, "Generating link...")

    data = get_data(text)
    if not data:
        bot.edit_message_text("Failed to fetch link.", message.chat.id, msg.message_id)
        return

    encoded = quote_plus(data["stream"])
    player = f"{PLAYER_BASE}?url={encoded}"

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("▶️ Watch Online", url=player))

    if data["download"]:
        markup.add(types.InlineKeyboardButton("⬇️ Download", url=data["download"]))

    bot.edit_message_text(
        f"✅ <b>{data['name']}</b>",
        message.chat.id,
        msg.message_id,
        reply_markup=markup
    )

# ---------------- SAFE RUNNER ----------------
def run_bot():
    logger.info("Starting bot...")

    # HARD RESET TELEGRAM SESSION
    try:
        bot.delete_webhook()
    except:
        pass

    time.sleep(2)

    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=10)
        except Exception as e:
            logger.error(f"Crash: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_bot()
