import os
import time
import logging
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- CONFIG ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
XAPIVERSE_KEY = os.getenv("XAPIVERSE_KEY")
CHANNEL_USERNAME = "@terabox_directlinks"  # apna channel username

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN)

# --- FORCE SUBSCRIBE CHECK ---
def is_user_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# --- START COMMAND ---
@bot.message_handler(commands=['start'])
def start(message):
    if not is_user_joined(message.from_user.id):
        bot.reply_to(
            message,
            f"🚫 Please join our channel first:\nhttps://t.me/{CHANNEL_USERNAME.replace('@','')}"
        )
        return

    bot.reply_to(message, "Send any Terabox link.")

# --- MAIN LINK HANDLER ---
@bot.message_handler(func=lambda message: True)
def handle_link(message):
    if not is_user_joined(message.from_user.id):
        bot.reply_to(
            message,
            f"🚫 Please join our channel first:\nhttps://t.me/{CHANNEL_USERNAME.replace('@','')}"
        )
        return

    url_text = message.text.strip()
    if "terabox" not in url_text and "1024tera" not in url_text:
        return

    wait_msg = bot.reply_to(message, "⏳ Generating links...")

    try:
        api_url = "https://xapiverse.com/api/terabox"
        headers = {
            "Content-Type": "application/json",
            "xAPIverse-Key": XAPIVERSE_KEY
        }
        payload = {"url": url_text}

        response = requests.post(api_url, headers=headers, json=payload, timeout=60)

        if response.status_code == 200:
            json_data = response.json()
            file_data = json_data.get("list", [{}])[0]

            download_url = file_data.get("download_link")

            # Real streaming extraction
            stream_url = (
                file_data.get("stream_url")
                or file_data.get("stream_link")
            )

            if not stream_url:
                fast_stream = file_data.get("fast_stream_url", {})
                stream_url = fast_stream.get("720p") or fast_stream.get("480p")

            if download_url:
                markup = InlineKeyboardMarkup()

                if stream_url:
                    markup.add(
                        InlineKeyboardButton(
                            "▶️ Watch Online",
                            url=stream_url
                        )
                    )

                markup.add(
                    InlineKeyboardButton(
                        "⬇️ Download",
                        url=download_url
                    )
                )

                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=wait_msg.message_id,
                    text="✅ Your links are ready:",
                    reply_markup=markup
                )
            else:
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=wait_msg.message_id,
                    text="❌ Download link not found."
                )
        else:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=wait_msg.message_id,
                text=f"❌ API Error: {response.status_code}"
            )

    except Exception as e:
        logger.error(e)
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=wait_msg.message_id,
            text="⚠️ Error processing link."
        )

# --- SAFE STARTUP ---
def run():
    time.sleep(5)
    bot.remove_webhook()
    bot.infinity_polling()

if __name__ == "__main__":
    run()
