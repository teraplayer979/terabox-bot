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

# Auto-posting settings (USERNAME METHOD)
SOURCE_GROUP = "terabox_movies_hub0"   # without @
TARGET_CHANNEL = "@terabox_directlinks"

# --------------- LOGGING ----------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if not BOT_TOKEN or not XAPIVERSE_KEY:
    logger.error("CRITICAL: BOT_TOKEN or XAPIVERSE_KEY missing!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# ---------------- HELPERS ----------------

def is_user_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Membership check error: {e}")
        return False


def get_link_data(url):
    """Fetch stream and download links"""
    try:
        api_url = "https://xapiverse.com/api/terabox"
        headers = {
            "Content-Type": "application/json",
            "xAPIverse-Key": XAPIVERSE_KEY
        }
        payload = {"url": url}

        response = requests.post(api_url, headers=headers, json=payload, timeout=60)

        if response.status_code == 200:
            json_data = response.json()
            file_list = json_data.get("list", [])

            if file_list:
                info = file_list[0]
                fast = info.get("fast_stream_url", {})

                watch = (
                    fast.get("720p")
                    or fast.get("480p")
                    or fast.get("360p")
                    or info.get("stream_url")
                    or info.get("download_link")
                )

                download = info.get("download_link")
                name = info.get("name", "Movie")

                return name, watch, download

    except Exception as e:
        logger.error(f"API Error: {e}")

    return None, None, None


# ---------------- AUTO POST HANDLER ----------------

@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'])
def auto_post_handler(message):
    try:
        if not message.chat.username:
            return

        # Match source group username
        if message.chat.username.lower() != SOURCE_GROUP.lower():
            return

        if not message.text:
            return

        url_text = message.text.strip()

        if "terabox" not in url_text and "1024tera" not in url_text:
            return

        logger.info("Auto-post triggered")

        name, watch, download = get_link_data(url_text)

        if not watch:
            return

        encoded_watch = quote_plus(watch)
        player_url = f"{PLAYER_BASE}?url={encoded_watch}"

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("▶️ Watch Online", url=player_url))

        if download:
            markup.add(types.InlineKeyboardButton("⬇️ Download", url=download))

        bot.send_message(
            chat_id=TARGET_CHANNEL,
            text=f"🎬 {name}\n\n▶️ Watch Online\n⬇️ Download",
            reply_markup=markup
        )

        logger.info(f"Posted: {name}")

    except Exception as e:
        logger.error(f"Auto-post error: {e}")


# ---------------- PRIVATE CHAT HANDLER ----------------

@bot.message_handler(func=lambda m: m.chat.type == 'private')
def private_handler(message):
    try:
        user_id = message.from_user.id

        if not message.text:
            return

        # Force subscribe
        if not is_user_joined(user_id):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
            bot.reply_to(
                message,
                "🚫 Join our channel first to use this bot.",
                reply_markup=markup
            )
            return

        url_text = message.text.strip()

        if "terabox" not in url_text and "1024tera" not in url_text:
            return

        status_msg = bot.reply_to(message, "⏳ Generating links...")

        name, watch, download = get_link_data(url_text)

        if not watch:
            bot.edit_message_text(
                "❌ No playable stream found.",
                message.chat.id,
                status_msg.message_id
            )
            return

        encoded_watch = quote_plus(watch)
        player_url = f"{PLAYER_BASE}?url={encoded_watch}"

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("▶️ Watch Online", url=player_url))

        if download:
            markup.add(types.InlineKeyboardButton("⬇️ Download", url=download))

        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            text=f"✅ Ready!\n\n📦 {name}\n\n📢 Join: {CHANNEL_USERNAME}",
            reply_markup=markup
        )

    except Exception as e:
        logger.error(f"Private handler error: {e}")


# ---------------- RUNNER ----------------

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
