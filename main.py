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

CHANNEL_USERNAME = "@terabox_directlinks"
CHANNEL_LINK = "https://t.me/terabox_directlinks"

SOURCE_GROUP = "@terabox_movies_hub0"
TARGET_CHANNEL = "@terabox_directlinks"

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not BOT_TOKEN or not XAPIVERSE_KEY:
    logger.error("Missing BOT_TOKEN or XAPIVERSE_KEY")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# ---------------- HELPERS ----------------

def is_user_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


def get_link_data(url):
    try:
        api_url = "https://xapiverse.com/api/terabox"
        headers = {
            "Content-Type": "application/json",
            "xAPIverse-Key": XAPIVERSE_KEY
        }
        payload = {"url": url}

        r = requests.post(api_url, headers=headers, json=payload, timeout=40)

        if r.status_code == 200:
            data = r.json()
            items = data.get("list", [])
            if items:
                info = items[0]
                fast = info.get("fast_stream_url", {})

                watch = (
                    fast.get("720p") or
                    fast.get("480p") or
                    fast.get("360p") or
                    info.get("stream_url") or
                    info.get("download_link")
                )

                download = info.get("download_link")
                name = info.get("name", "File Ready")

                return name, watch, download
    except Exception as e:
        logger.error(e)

    return None, None, None


def create_markup(watch, download):
    markup = types.InlineKeyboardMarkup()

    if watch:
        encoded = quote_plus(watch)
        markup.add(
            types.InlineKeyboardButton(
                "▶️ Watch Online",
                url=f"{PLAYER_BASE}?url={encoded}"
            )
        )

    if download:
        markup.add(
            types.InlineKeyboardButton(
                "⬇️ Download",
                url=download
            )
        )

    return markup


# ---------------- AUTO POST ----------------
@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'])
def group_handler(message):
    if not message.text:
        return

    if not message.chat.username:
        return

    if message.chat.username.lower() != SOURCE_GROUP.replace("@", "").lower():
        return

    if "terabox" not in message.text and "1024tera" not in message.text:
        return

    name, watch, download = get_link_data(message.text.strip())

    if watch:
        markup = create_markup(watch, download)
        bot.send_message(
            TARGET_CHANNEL,
            f"🎬 {name}\n\n▶️ Watch Online\n⬇️ Download",
            reply_markup=markup
        )


# ---------------- PRIVATE HANDLER ----------------
@bot.message_handler(func=lambda m: m.chat.type == "private")
def private_handler(message):
    if not message.text:
        return

    if "terabox" not in message.text and "1024tera" not in message.text:
        return

    user_id = message.from_user.id

    if not is_user_joined(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
        bot.reply_to(message, "Join channel first.", reply_markup=markup)
        return

    status = bot.reply_to(message, "Processing...")

    name, watch, download = get_link_data(message.text.strip())

    if watch:
        markup = create_markup(watch, download)
        bot.edit_message_text(
            f"Ready:\n{name}",
            message.chat.id,
            status.message_id,
            reply_markup=markup
        )
    else:
        bot.edit_message_text(
            "Failed to extract link.",
            message.chat.id,
            status.message_id
        )


# ---------------- SAFE RUNNER ----------------
def run():
    logger.info("Bot starting...")

    try:
        bot.remove_webhook()
        time.sleep(2)
    except:
        pass

    while True:
        try:
            bot.polling(non_stop=True, timeout=60)
        except Exception as e:
            logger.error(e)
            time.sleep(5)


if __name__ == "__main__":
    run()
