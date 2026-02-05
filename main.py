import os
import time
import logging
import requests
import telebot
from telebot import types
from urllib.parse import quote_plus

# --- CONFIGURATION ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
XAPIVERSE_KEY = os.getenv("XAPIVERSE_KEY")

if not BOT_TOKEN or not XAPIVERSE_KEY:
    logger.error("Missing BOT_TOKEN or XAPIVERSE_KEY")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# --- START COMMAND ---
@bot.message_handler(commands=['start'])
def start_command(message):
    bot.reply_to(
        message,
        "👋 Send any Terabox link.\nI will generate Watch & Download buttons."
    )

# --- MAIN HANDLER ---
@bot.message_handler(func=lambda message: True)
def handle_terabox(message):
    text = message.text.strip()

    # Validate link
    if "terabox" not in text and "1024tera" not in text:
        bot.reply_to(message, "❌ Please send a valid Terabox link.")
        return

    status_msg = bot.reply_to(message, "⏳ Generating links...")

    try:
        # API request
        api_url = "https://xapiverse.com/api/terabox"
        headers = {
            "Content-Type": "application/json",
            "xAPIverse-Key": XAPIVERSE_KEY
        }
        payload = {"url": text}

        response = requests.post(api_url, headers=headers, json=payload, timeout=60)

       # --- Extraction and Button Creation Logic ---

try:
    file_info = json_data.get("list", [{}])[0]
    
    fast_streams = file_info.get("fast_stream_url", {})
    watch_url = fast_streams.get("720p") or file_info.get("stream_url")
    
    download_url = file_info.get("download_link")
    file_name = file_info.get("name") or "File Ready"

    if watch_url:
        encoded_watch = quote_plus(watch_url)
        final_player_url = f"https://teraplayer979.github.io/stream-player/?url={encoded_watch}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("▶️ Watch Online", url=final_player_url))
        
        if download_url:
            markup.add(types.InlineKeyboardButton("⬇️ Download", url=download_url))

        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            text=f"✅ **Links Generated!**\n\n📦 `{file_name}`",
            parse_mode="Markdown",
            reply_markup=markup
        )
    else:
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            text="❌ Streaming Error: No playable stream found."
        )

except (IndexError, KeyError, TypeError) as e:
    logger.error(f"Extraction failed: {e}")
    bot.edit_message_text(
        chat_id=message.chat.id, 
        message_id=status_msg.message_id, 
        text="❌ Error: Failed to parse stream data."
    )

# --- RUNNER ---
def run_bot():
    try:
        bot.remove_webhook()
    except:
        pass

    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=20)
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_bot()
