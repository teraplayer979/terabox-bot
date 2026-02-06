import os
import time
import logging
import requests
import telebot
from telebot import types, apihelper
from urllib.parse import quote_plus

# --- CONFIGURATION & LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
XAPIVERSE_KEY = os.getenv("XAPIVERSE_KEY")

# Constants
CHANNEL_USERNAME = "@terabox_directlinks"
SOURCE_GROUP = "@terabox_movies_hub0"
TARGET_CHANNEL = "@terabox_directlinks"

if not BOT_TOKEN or not XAPIVERSE_KEY:
    logger.error("Missing BOT_TOKEN or XAPIVERSE_KEY in environment variables!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# --- HELPERS ---

def is_subscribed(user_id):
    """Checks if the user is a member of the required channel."""
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Subscription check error: {e}")
        return False

def get_terabox_data(url):
    """Calls xAPIverse API to fetch stream and download links."""
    try:
        api_url = "https://xapiverse.com/api/terabox"
        headers = {"xapiverse-key": XAPIVERSE_KEY, "Content-Type": "application/json"}
        payload = {"url": url}
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            # Extract links safely based on typical xapiverse response structure
            # Note: Adjust keys if your specific API response differs
            return {
                "file_name": data.get("file_name", "Video File"),
                "direct_link": data.get("direct_link"),
                "stream_link": data.get("stream_link")
            }
    except Exception as e:
        logger.error(f"API Error: {e}")
    return None

def process_and_send(chat_id, url, reply_to_id=None):
    """Reusable logic for both private and group messages."""
    data = get_terabox_data(url)
    if not data:
        return

    markup = types.InlineKeyboardMarkup()
    if data['stream_link']:
        markup.add(types.InlineKeyboardButton("▶️ Watch Online", url=data['stream_link']))
    if data['direct_link']:
        markup.add(types.InlineKeyboardButton("⬇️ Download", url=data['direct_link']))

    caption = f"🎬 **{data['file_name']}**\n\n📥 **Source:** Terabox"
    bot.send_message(chat_id, caption, reply_markup=markup, parse_mode="Markdown", reply_to_message_id=reply_to_id)

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 Welcome! Send me a Terabox link to get started.")

# Group Auto-Post Feature
@bot.message_handler(func=lambda m: m.chat.username == SOURCE_GROUP.replace('@', '') or m.chat.title == SOURCE_GROUP)
def handle_group(message):
    if message.text and "terabox" in message.text.lower():
        # Post directly to the Target Channel
        process_and_send(TARGET_CHANNEL, message.text.strip())

# Private Chat Handler
@bot.message_handler(func=lambda m: m.chat.type == 'private')
def handle_private(message):
    if not message.text or "terabox" not in message.text.lower():
        return

    if not is_subscribed(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"))
        bot.reply_to(message, "❌ **Access Denied!**\n\nYou must join our channel to use this bot.", reply_markup=markup, parse_mode="Markdown")
        return

    bot.send_chat_action(message.chat.id, 'typing')
    process_and_send(message.chat.id, message.text.strip(), reply_to_id=message.message_id)

# --- PRODUCTION POLLING LOOP ---

def run_bot():
    """Main polling loop with conflict handling and auto-restart."""
    logger.info("Bot is starting...")
    
    # Crucial: Remove webhook before starting polling to avoid 409 Conflict
    try:
        bot.remove_webhook()
        time.sleep(1) # Small delay for Telegram to process the removal
    except Exception as e:
        logger.warning(f"Failed to remove webhook: {e}")

    while True:
        try:
            logger.info("Bot polling started.")
            bot.polling(none_stop=True, interval=0, timeout=40)
        except apihelper.ApiException as e:
            if "Conflict" in str(e):
                logger.error("409 Conflict detected. Another instance might be running. Retrying in 5s...")
            else:
                logger.error(f"Telegram API Error: {e}")
            time.sleep(5)
        except Exception as e:
            logger.error(f"General error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_bot()
