import os
import time
import logging
import requests
import telebot

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
XAPIVERSE_KEY = os.getenv("XAPIVERSE_KEY")

if not BOT_TOKEN or not XAPIVERSE_KEY:
    logger.error("Missing BOT_TOKEN or XAPIVERSE_KEY")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)


def format_size(size_bytes):
    try:
        size_bytes = int(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
    except:
        return "Unknown Size"


def extract_data(data):
    try:
        info = data.get("data", {}) if isinstance(data.get("data"), dict) else data

        file_name = info.get("file_name") or info.get("filename") or "File"
        size = format_size(info.get("size") or info.get("filesize") or 0)

        link = (
            info.get("download_link")
            or info.get("direct_link")
            or info.get("dlink")
            or info.get("url")
        )

        if not link:
            return "❌ Download link not found."

        return (
            f"✅ **Download Ready**\n\n"
            f"📦 **File:** `{file_name}`\n"
            f"⚖️ **Size:** {size}\n\n"
            f"🚀 **Link:**\n`{link}`"
        )

    except Exception as e:
        logger.error(f"Parse error: {e}")
        return "⚠️ Failed to read API response."


@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Send any Terabox link.")


@bot.message_handler(func=lambda message: True)
def handle_link(message):
    url_text = message.text.strip()
    if "terabox" not in url_text and "1024tera" not in url_text:
        return

    wait_msg = bot.reply_to(message, "⏳ Direct link found. Sending now...")

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

            download_url = json_data.get("list", [{}])[0].get("download_link")

            if download_url:
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=wait_msg.message_id,
                    text=f"✅ Download Link:\n{download_url}",
                    disable_web_page_preview=True
                )
            else:
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=wait_msg.message_id,
                    text="❌ Download link not found in API response."
                )
        else:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=wait_msg.message_id,
                text=f"❌ API Error: {response.status_code}"
            )

    except Exception as e:
        logger.error(f"Request Failure: {e}")
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=wait_msg.message_id,
            text="⚠️ Service unavailable. Please try again later."
        )


def run():
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling()


if __name__ == "__main__":
    run()
