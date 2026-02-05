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

# Force subscribe settings
CHANNEL_USERNAME = "@terabox_directlinks"   # apna channel username
CHANNEL_LINK = "https://t.me/terabox_directlinks"

PLAYER_BASE = "https://teraplayer979.github.io/stream-player/"

# --------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not BOT_TOKEN or not XAPIVERSE_KEY:
    logger.error("Missing BOT_TOKEN or XAPIVERSE_KEY")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# --------------- FORCE SUBSCRIBE CHECK ---------------
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
    if not is_user_joined(message.from_user.id):
        bot.reply_to(
            message,
            "🚫 You must join our channel to use this bot.",
            reply_markup=join_markup()
        )
        return

    bot.reply_to(message, "Send a Terabox link to stream or download.")

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

        file_list = json_data.get("list", [])
        if not file_list:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=status_msg.message_id,
                text="❌ No file data found."
            )
            return

        file_info = file_list[0]
        file_name = file_info.get("name", "File Ready")
        download_url = file_info.get("download_link")

        fast_streams = file_info.get("fast_stream_url", {})

        # Create buttons
        markup = types.InlineKeyboardMarkup()

        # Multi-quality HLS buttons
        for quality in ["720p", "480p", "360p"]:
            stream = fast_streams.get(quality)
            if stream:
                encoded = quote_plus(stream)
                player_url = f"{PLAYER_BASE}?url={encoded}"
                markup.add(
                    types.InlineKeyboardButton(
                        f"▶️ Watch {quality}",
                        url=player_url
                    )
                )

        # Fallback if no HLS
        if not fast_streams:
            fallback = file_info.get("stream_url") or download_url
            if fallback:
                encoded = quote_plus(fallback)
                player_url = f"{PLAYER_BASE}?url={encoded}"
                markup.add(
                    types.InlineKeyboardButton(
                        "▶️ Watch Online",
                        url=player_url
                    )
                )

        # Download button
        if download_url:
            markup.add(types.InlineKeyboardButton("⬇️ Download", url=download_url))

        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            text=f"✅ Ready!\n\n📦 {file_name}",
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
