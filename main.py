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

# --- FIX: Single-Threaded Mode ---
# This prevents the 409 error loop and ensures stability on Railway.
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# --- 2. CORE LOGIC ---

def check_sub(user_id):
    """Verifies if the user is a member of the required channel."""
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.warning(f"Sub check failed for {user_id}: {e}")
        return False

def get_link_data(url):
    """Calls xAPIverse API to get video details."""
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

# --- 3. HANDLERS (STRICTLY SEPARATED) ---

# Handler 1: /start command (Always replies)
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    logger.info(f"Command /start received from {message.from_user.id}")
    bot.reply_to(message, "👋 **Bot is Online!**\n\nSend me a Terabox link to generate buttons.")

# Handler 2: Auto-Post (Groups only)
# We use chat_types=['group', 'supergroup'] to ensure we catch everything.
@bot.message_handler(chat_types=['group', 'supergroup'])
def handle_group_message(message):
    if not message.text:
        return

    # Check if this is the correct source group
    if not message.chat.username:
        return
        
    current_group = f"@{message.chat.username}"
    if current_group.lower() != SOURCE_GROUP.lower():
        # Ignore messages from other random groups
        return

    # Check for Terabox link
    if "terabox" not in message.text.lower() and "1024tera" not in message.text.lower():
        return

    logger.info(f"🔗 Link detected in source group: {SOURCE_GROUP}")
    
    # Process the link
    name, watch, download = get_link_data(message.text.strip())
    
    if watch:
        markup = create_markup(watch, download)
        try:
            bot.send_message(
                TARGET_CHANNEL,
                f"🎬 {name}\n\n▶️ Watch Online\n⬇️ Download",
                reply_markup=markup
            )
            logger.info("✅ Auto-posted successfully to target channel.")
        except Exception as e:
            logger.error(f"❌ Auto-post failed: {e}")

# Handler 3: Private Chat (Terabox Links)
@bot.message_handler(chat_types=['private'])
def handle_private_message(message):
    if not message.text:
        return

    # Only process Terabox links
    if "terabox" not in message.text.lower() and "1024tera" not in message.text.lower():
        return

    logger.info(f"📩 Private link received from {message.from_user.id}")

    # Force Subscribe Check
    if not check_sub(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
        bot.reply_to(
            message, 
            "🚫 **Access Denied**\n\nPlease join our channel first to use this bot.", 
            reply_markup=markup,
            parse_mode="Markdown"
        )
        logger.info(f"User {message.from_user.id} denied (not subscribed).")
        return

    # Send "Processing" status
    status = bot.reply_to(message, "⏳ Processing...")
    
    # Fetch Data
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
        logger.info("✅ Private link processed successfully.")
    else:
        bot.edit_message_text("❌ No playable links found.", message.chat.id, status.message_id)

# --- 4. PRODUCTION RUNNER ---

def run_bot():
    print("--- STARTING BOT SEQUENCE ---")
    logger.info("Bot starting...")

    # 1. Force Clear Webhook
    try:
        bot.remove_webhook()
        time.sleep(1)
    except Exception as e:
        logger.warning(f"Webhook check: {e}")

    # 2. Infinity Polling (Stable Mode)
    # allowed_updates ensures we receive text messages correctly
    while True:
        try:
            logger.info("Connecting to Telegram...")
            bot.infinity_polling(
                timeout=60, 
                long_polling_timeout=60, 
                allowed_updates=['message', 'edited_message']
            )
        except Exception as e:
            logger.error(f"Polling crashed: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_bot()
