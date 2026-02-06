import os
import time
import logging
import requests
import telebot
from telebot import types, apihelper
from urllib.parse import quote_plus

# --- 1. CONFIGURATION ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
XAPIVERSE_KEY = os.getenv("XAPIVERSE_KEY")

# Constants
PLAYER_BASE = "https://teraplayer979.github.io/stream-player/"
CHANNEL_USERNAME = "@terabox_directlinks"
CHANNEL_LINK = "https://t.me/terabox_directlinks"
SOURCE_GROUP = "@terabox_movies_hub0"
TARGET_CHANNEL = "@terabox_directlinks"

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if not BOT_TOKEN or not XAPIVERSE_KEY:
    logger.error("CRITICAL: Missing BOT_TOKEN or XAPIVERSE_KEY")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# --- 2. CORE LOGIC (HANDLERS) ---

def check_sub(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

def get_link_data(url):
    try:
        api_url = "https://xapiverse.com/api/terabox"
        headers = {"Content-Type": "application/json", "xAPIverse-Key": XAPIVERSE_KEY}
        payload = {"url": url}
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("list", [])
            if items:
                info = items[0]
                fast = info.get("fast_stream_url", {})
                watch = (fast.get("720p") or fast.get("480p") or fast.get("360p") or 
                         info.get("stream_url") or info.get("download_link"))
                return info.get("name", "File"), watch, info.get("download_link")
    except Exception as e:
        logger.error(f"API Error: {e}")
    return None, None, None

def create_markup(watch, download):
    markup = types.InlineKeyboardMarkup()
    if watch:
        encoded = quote_plus(watch)
        markup.add(types.InlineKeyboardButton("▶️ Watch Online", url=f"{PLAYER_BASE}?url={encoded}"))
    if download:
        markup.add(types.InlineKeyboardButton("⬇️ Download", url=download))
    return markup

# Handler 1: Auto-Post (Groups)
@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'])
def auto_post(message):
    if not message.text: return
    
    # Strict Username Check (Case-insensitive)
    if not message.chat.username or message.chat.username.lower() != SOURCE_GROUP.replace('@', '').lower():
        return

    if "terabox" not in message.text and "1024tera" not in message.text:
        return

    logger.info(f"Auto-post detected from {SOURCE_GROUP}")
    name, watch, download = get_link_data(message.text.strip())
    
    if watch:
        markup = create_markup(watch, download)
        try:
            bot.send_message(
                TARGET_CHANNEL,
                f"🎬 {name}\n\n▶️ Watch Online\n⬇️ Download",
                reply_markup=markup
            )
            logger.info("Auto-posted successfully.")
        except Exception as e:
            logger.error(f"Auto-post failed: {e}")

# Handler 2: Private Chat
@bot.message_handler(func=lambda m: m.chat.type == 'private')
def private_chat(message):
    if not message.text or ("terabox" not in message.text and "1024tera" not in message.text):
        return

    if not check_sub(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
        bot.reply_to(message, "🚫 **Access Denied**\n\nPlease join our channel first.", reply_markup=markup, parse_mode="Markdown")
        return

    status = bot.reply_to(message, "⏳ Processing...")
    name, watch, download = get_link_data(message.text.strip())

    if watch:
        markup = create_markup(watch, download)
        bot.edit_message_text(
            f"✅ **Ready!**\n📦 `{name}`",
            message.chat.id,
            status.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    else:
        bot.edit_message_text("❌ No playable links found.", message.chat.id, status.message_id)

# --- 3. ROBUST STARTUP & POLLING LOGIC ---

# --- 3. FINAL PRODUCTION RUNNER (MANUAL LOOP) ---

def run_production_bot():
    print("--- STARTING BOT PROTECTION SEQUENCE ---")
    logger.info("Bot starting...")

    # 1. Force Clear Webhook
    # This prevents "Conflict: terminated by other getUpdates request"
    # caused by a stuck webhook from a previous run.
    try:
        bot.remove_webhook()
        time.sleep(2) 
    except Exception as e:
        logger.warning(f"Webhook removal check: {e}")

    # 2. Manual Pulse Loop
    # We use manual bot.polling() instead of infinity_polling() 
    # so we can explicitly catch the 409 error and sleep.
    while True:
        try:
            logger.info("Connecting to Telegram...")
            
            # non_stop=True keeps it running. 
            # timeout=60 keeps the connection open longer (less frequent requests).
            bot.polling(non_stop=True, interval=0, timeout=60)
            
        except apihelper.ApiTelegramException as e:
            # THIS CATCHES THE 409 ERROR SPECIFICALLY
            if e.error_code == 409:
                logger.error("!!! CONFLICT DETECTED (409) !!!")
                logger.error("Another bot instance is running with this token.")
                logger.error("Sleeping for 15 seconds to let the old instance die...")
                time.sleep(15)  # The important pause
            else:
                logger.error(f"Telegram API Error: {e}")
                time.sleep(5)
                
        except Exception as e:
            # Catches network errors, timeouts, etc.
            logger.error(f"Network/General Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    # This ensures the script handles the restart loop internally
    run_production_bot()
