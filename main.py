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

PLAYER_BASE = "https://teraplayer979.github.io/stream-player/"

# Force subscribe settings
CHANNEL_USERNAME = "@terabox_directlinks"
CHANNEL_LINK = "https://t.me/terabox_directlinks"

# Auto-posting settings
UPLOAD_GROUP = "@terabox_movies_hub0"
TARGET_CHANNEL = "@terabox_directlinks"

# --------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not BOT_TOKEN or not XAPIVERSE_KEY:
    logger.error("Missing BOT_TOKEN or XAPIVERSE_KEY")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# ----------- FORCE SUBSCRIBE FUNCTIONS ----------
def is_user_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def join_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
    return markup

# --------------- START ------------------
@bot.message_handler(commands=["start", "help"])
def start(message):
    bot.reply_to(message, "Send a Terabox link to stream or download.")

# --------------- AUTO POSTING HANDLER -----------
@bot.message_handler(func=lambda message: message.chat.type in ['group', 'supergroup'])
def handle_group_autopost(message):
    try:
        # Check correct group username
        if not message.chat.username:
            return

        if f"@{message.chat.username}" != UPLOAD_GROUP:
            return

        url_text = message.text.strip()
        if "terabox" not in url_text and "1024tera" not in url_text:
            return

        api_url = "https://xapiverse.com/api/terabox"
        headers = {
            "Content-Type": "application/json",
            "xAPIverse-Key": XAPIVERSE_KEY
        }
        payload = {"url": url_text}

        response = requests.post(api_url, headers=headers, json=payload, timeout=60)

        if response.status_code == 200:
            json_data = response.json()
            file_list = json_data.get("list", [])
            if not file_list:
                return

            file_info = file_list[0]
            fast_streams = file_info.get("fast_stream_url", {})

            watch_url = (
                fast_streams.get("720p")
                or fast_streams.get("480p")
                or fast_streams.get("360p")
                or file_info.get("stream_url")
                or file_info.get("download_link")
            )

            download_url = file_info.get("download_link")
            file_name = file_info.get("name", "File Ready")

            if not watch_url:
                return

            encoded_watch = quote_plus(watch_url)
            final_player_url = f"{PLAYER_BASE}?url={encoded_watch}"

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("▶️ Watch Online", url=final_player_url))

            if download_url:
                markup.add(types.InlineKeyboardButton("⬇️ Download", url=download_url))

            bot.send_message(
                chat_id=TARGET_CHANNEL,
                text=f"🎬 {file_name}",
                reply_markup=markup
            )

    except Exception as e:
        logger.error(f"Auto-post Error: {e}")

# --------------- MAIN HANDLER -----------
@bot.message_handler(func=lambda message: True)
def handle_link(message):
    user_id = message.from_user.id

    # Force subscribe check
    if not is_user_joined(user_id):
        bot.reply_to(
            message,
            "🚫 Join our channel first to use this bot.",
            reply_markup=join_markup()
        )
        return

    url_text = message.text.strip()

    if "terabox" not in url_text and "1024tera" not in url_text:
        return

    status_msg = bot.reply_to(message, "⏳ Generating links...")

    try:
        api_url = "https://xapiverse.com/api/terabox"
        headers = {
            "Content-Type": "application/json",
            "xAPIverse-Key": XAPIVERSE_KEY
        }
        payload = {"url": url_text}

        response = requests.post(api_url, headers=headers, json=payload, timeout=60)

        if response.status_code != 200:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=status_msg.message_id,
                text=f"❌ API Error: {response.status_code}"
            )
            return

        json_data = response.json()
        logger.info(json_data)

        file_list = json_data.get("list", [])
        if not file_list:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=status_msg.message_id,
                text="❌ No file data found."
            )
            return

        file_info = file_list[0]
        fast_streams = file_info.get("fast_stream_url", {})

        watch_url = (
            fast_streams.get("720p")
            or fast_streams.get("480p")
            or fast_streams.get("360p")
            or file_info.get("stream_url")
            or file_info.get("download_link")
        )

        download_url = file_info.get("download_link")
        file_name = file_info.get("name", "File Ready")

        if not watch_url:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=status_msg.message_id,
                text="❌ No playable stream found."
            )
            return

        encoded_watch = quote_plus(watch_url)
        final_player_url = f"{PLAYER_BASE}?url={encoded_watch}"

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("▶️ Watch Online", url=final_player_url))

        if download_url:
            markup.add(types.InlineKeyboardButton("⬇️ Download", url=download_url))

        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            text=f"✅ Ready!\n\n📦 {file_name}\n\n📢 Join: {CHANNEL_USERNAME}",
            reply_markup=markup
        )

    except Exception as e:
        logger.error(f"Error: {e}")
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            text="⚠️ Something went wrong."
        )

# --------------- SAFE RUNNER ------------
def run_bot():
    logger.info("Bot starting...")
    try:
        bot.remove_webhook()
        time.sleep(3)
    except:
        pass

    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            logger.error(f"Polling crashed: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_bot()
