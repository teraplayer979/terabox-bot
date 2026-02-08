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

# --------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not BOT_TOKEN or not XAPIVERSE_KEY:
    logger.error("Missing BOT_TOKEN or XAPIVERSE_KEY")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# --------------- START ------------------
@bot.message_handler(commands=["start", "help"])
def start(message):
    bot.reply_to(message, "Send a Terabox link to stream or download.")

# --------------- MAIN HANDLER -----------
@bot.message_handler(func=lambda message: True)
def handle_link(message):
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
        logger.info(json_data)  # Debug log

        # ----------- SAFE EXTRACTION -----------
        file_list = json_data.get("list", [])
        if not file_list:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=status_msg.message_id,
                text="❌ No file data found."
            )
            return

        file_info = file_list[0]

        # --- INTELLIGENT STREAM SELECTION ---
        fast_streams = file_info.get("fast_stream_url", {})

        watch_url = (
            fast_streams.get("720p")
            or fast_streams.get("480p")
            or fast_streams.get("360p")
            or file_info.get("stream_url")  # fallback
            or file_info.get("download_link")  # last fallback
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

        # Encode for player
        encoded_watch = quote_plus(watch_url)
        final_player_url = f"{PLAYER_BASE}?url={encoded_watch}"

        # Create buttons
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("▶️ Watch Online", url=final_player_url))

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
# ---------------- WEBSITE API ----------------
from flask import Flask, request, jsonify
import threading

app = Flask(__name__)

@app.route("/api/terabox", methods=["POST"])
def website_api():
    try:
        data = request.json
        url_text = data.get("url")

        api_url = "https://xapiverse.com/api/terabox"
        headers = {
            "Content-Type": "application/json",
            "xAPIverse-Key": XAPIVERSE_KEY
        }
        payload = {"url": url_text}

        response = requests.post(api_url, headers=headers, json=payload, timeout=60)

        if response.status_code != 200:
            return jsonify({"error": "API error"}), 500

        json_data = response.json()
        file_list = json_data.get("list", [])

        if not file_list:
            return jsonify({"error": "No file found"}), 404

        file_info = file_list[0]
        fast_streams = file_info.get("fast_stream_url", {})

        video_url = (
            fast_streams.get("720p")
            or fast_streams.get("480p")
            or fast_streams.get("360p")
            or file_info.get("stream_url")
            or file_info.get("download_link")
        )

        return jsonify({
            "video": video_url,
            "name": file_info.get("name")
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def run_api():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


# Run API in background thread
api_thread = threading.Thread(target=run_api)
api_thread.start()
