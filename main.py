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
SOURCE_GROUP = "terabox_movies_hub0"  # No @ symbol for safer comparison
TARGET_CHANNEL = "@terabox_directlinks"

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if not BOT_TOKEN or not XAPIVERSE_KEY:
    logger.error("CRITICAL: Missing BOT_TOKEN or XAPIVERSE_KEY")
    exit(1)

# --- FIX: Single-Threaded Mode ---
# We disable threading here. This works on pyTelegramBotAPI 4.14.0.
# This ensures errors are caught in our main loop, preventing crashes.
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# --- 2. CORE LOGIC ---

def check_sub(user_id):
    """Verifies if the user is a member of the required channel."""
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        # If bot is not admin, this fails. We default to False to be safe.
        return False

def get_link_data(url):
    """Calls xAPIverse API to get video details."""
    try:
        api_url = "https://xapiverse.com/api/terabox"
        headers = {"Content-Type": "application/json", "xAPIverse-Key": XAPIVERSE_KEY}
        payload = {"url": url}
        
        # Increased timeout for slow API responses
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

# --- 3. HANDLERS ---

# Debug Handler: Logs ALL text messages to verify visibility
@bot.message_handler(func=lambda m: True, content_types=['text'])
def debug_logger(message):
    # This function runs for every text message. We use it to route traffic manually
    # to ensure strict filtering doesn't accidentally block messages.
    
    chat_type = message.chat.type
    user_id = message.from_user.id
    text = message.text.strip()
    
    logger.info(f"MSG RECEIVED: [{chat_type}] from {user_id}: {text[:20]}...")

    # ROUTE 1: PRIVATE CHAT
    if chat_type == 'private':
        handle_private(message)
        return

    # ROUTE 2: SOURCE GROUP
    if chat_type in ['group', 'supergroup']:
        # Safe username comparison
        if message.chat.username and message.chat.username.lower() == SOURCE_GROUP.lower():
            handle_group_auto_post(message)
        return

def handle_private(message):
    """Logic for Private Chat interactions."""
    if "terabox" not in message.text.lower() and "1024tera" not in message.text.lower():
        if message.text == "/start":
            bot.reply_to(message, "👋 **Bot is Online!**\nSend me a Terabox link.")
        return

    # Force Subscribe Check
    if not check_sub(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
        bot.reply_to(
            message, 
            "🚫 **Access Denied**\n\nPlease join our channel first.", 
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return

    # Process Link
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

def handle_group_auto_post(message):
    """Logic for Auto-Posting from Group -> Channel."""
    if "terabox" not in message.text.lower() and "1024tera" not in message.text.lower():
        return

    logger.info("🔗 Terabox link detected in Source Group!")
    name, watch, download = get_link_data(message.text.strip())
    
    if watch:
        markup = create_markup(watch, download)
        try:
            bot.send_message(
                TARGET_CHANNEL,
                f"🎬 {name}\n\n▶️ Watch Online\n⬇️ Download",
                reply_markup=markup
            )
            logger.info(f"✅ Auto-posted '{name}' to {TARGET_CHANNEL}")
        except Exception as e:
            logger.error(f"❌ Auto-post failed: {e}")

# --- 4. PRODUCTION RUNNER (CONFLICT PROOF) ---

def run_bot():
    print("--- STARTING BOT PROTECTION SEQUENCE ---")
    
    # 1. Force Clear Webhook
    # We use the safe method without arguments to support all library versions
    try:
        bot.remove_webhook()
        time.sleep(1)
    except Exception as e:
        logger.warning(f"Webhook check: {e}")

    # 2. Conflict-Proof Polling Loop
    while True:
        try:
            logger.info("Connecting to Telegram...")
            
            # timeout=60 keeps connection open longer (efficient)
            # long_polling_timeout=60 ensures we wait for data
            # allowed_updates ensures we listen to everything
            bot.infinity_polling(
                timeout=60, 
                long_polling_timeout=60, 
                allowed_updates=['message', 'edited_message', 'channel_post']
            )
            
        except Exception as e:
            err_str = str(e)
            if "Conflict" in err_str or "409" in err_str:
                logger.warning("!!! CONFLICT DETECTED (409) !!!")
                logger.warning("Another instance is running. Waiting 20s for it to close...")
                time.sleep(20) # VITAL: Wait for the old container to die
            else:
                logger.error(f"Polling Error: {e}")
                time.sleep(5)

if __name__ == "__main__":
    run_bot()
