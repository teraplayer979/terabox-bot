import os
import time
import logging
import requests
import telebot
from telebot import types, apihelper
from urllib.parse import quote_plus

# ---------------- CONFIG ----------------
# REFRESH YOUR TOKEN IN RAILWAY VARIABLES BEFORE RUNNING THIS
BOT_TOKEN = os.getenv("BOT_TOKEN")
XAPIVERSE_KEY = os.getenv("XAPIVERSE_KEY")

# Force Subscribe Config
FS_CHANNEL_USERNAME = "@terabox_directlinks"
FS_CHANNEL_LINK = "https://t.me/terabox_directlinks"

# Auto-Posting Config
SOURCE_GROUP_USERNAME = "terabox_movies_hub0" 
TARGET_CHANNEL_USERNAME = "@terabox_directlinks" 

PLAYER_BASE = "https://teraplayer979.github.io/stream-player/"

# --------------- LOGGING ----------------
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

if not BOT_TOKEN or not XAPIVERSE_KEY:
    logger.error("❌ CRITICAL: Missing BOT_TOKEN or XAPIVERSE_KEY")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# --------------- SHARED API LOGIC ------------------
def fetch_terabox_data(url_text):
    """
    Core logic to fetch data from API.
    """
    try:
        api_url = "https://xapiverse.com/api/terabox"
        headers = {
            "Content-Type": "application/json",
            "xAPIverse-Key": XAPIVERSE_KEY
        }
        payload = {"url": url_text}

        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"API Error: {response.status_code}")
            return None

        json_data = response.json()
        file_list = json_data.get("list", [])
        
        if not file_list:
            return None

        file_info = file_list[0]
        fast_streams = file_info.get("fast_stream_url", {})

        watch_url = (
            fast_streams.get("720p")
            or fast_streams.get("480p")
            or fast_streams.get("360p")
            or file_info.get("stream_url")
            or file_info.get("download_link")
        )

        download_url = file_info.get("download_link")
        file_name = file_info.get("name", "File Ready")

        if not watch_url:
            return None

        encoded_watch = quote_plus(watch_url)
        final_player_url = f"{PLAYER_BASE}?url={encoded_watch}"

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("▶️ Watch Online", url=final_player_url))

        if download_url:
            markup.add(types.InlineKeyboardButton("⬇️ Download", url=download_url))
            
        final_text = f"✅ Ready!\n\n📦 {file_name}"
        
        return final_text, markup

    except Exception as e:
        logger.error(f"API Exception: {e}")
        return None


# --------------- START COMMAND ------------------
@bot.message_handler(commands=["start", "help"])
def start(message):
    try:
        # Simple health check response
        bot.reply_to(message, "✅ Bot is Online!\nSend a Terabox link to stream or download.")
        logger.info(f"Start command received from user {message.from_user.id}")
    except Exception as e:
        logger.error(f"Error in /start: {e}")


# --------------- AUTO-POST HANDLER (GROUP) -----------
@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'], content_types=['text'])
def handle_group_message(message):
    try:
        if not message.text: return

        # 1. Check if we are in the correct group
        # We handle cases where username might be None or have casing differences
        if message.chat.username:
            current_chat = message.chat.username.replace("@", "").lower()
            target_chat = SOURCE_GROUP_USERNAME.replace("@", "").lower()
            
            if current_chat != target_chat:
                return # Ignore other groups silently
        else:
            return # Ignore groups without usernames

        # 2. Check for Terabox link
        url_text = message.text.strip()
        if "terabox" not in url_text and "1024tera" not in url_text:
            return

        logger.info(f"⚡ Link Detected in Source Group: {url_text}")

        # 3. Process API
        result = fetch_terabox_data(url_text)

        if result:
            text, markup = result
            try:
                # 4. Post to Target Channel
                bot.send_message(
                    chat_id=TARGET_CHANNEL_USERNAME,
                    text=text,
                    reply_markup=markup
                )
                logger.info(f"✅ Auto-Posted to {TARGET_CHANNEL_USERNAME}")
            except Exception as e:
                logger.error(f"❌ Failed to post to channel. Is bot Admin? Error: {e}")
        else:
            logger.warning("⚠️ API returned no result. Link might be invalid.")

    except Exception as e:
        logger.error(f"Group Handler Error: {e}")


# --------------- PRIVATE HANDLER (USER) -----------
@bot.message_handler(func=lambda m: m.chat.type == 'private', content_types=['text'])
def handle_private_link(message):
    url_text = message.text.strip()

    if "terabox" not in url_text and "1024tera" not in url_text:
        return

    # --- FORCE SUBSCRIBE CHECK ---
    user_id = message.from_user.id
    try:
        member_status = bot.get_chat_member(FS_CHANNEL_USERNAME, user_id).status
        if member_status not in ['creator', 'administrator', 'member']:
            fs_markup = types.InlineKeyboardMarkup()
            btn_join = types.InlineKeyboardButton("📢 Join Channel to Use", url=FS_CHANNEL_LINK)
            fs_markup.add(btn_join)
            bot.reply_to(
                message, 
                "⚠️ **Access Denied**\n\nYou must join our update channel to use this bot.",
                parse_mode="Markdown",
                reply_markup=fs_markup
            )
            return
    except Exception as e:
        logger.error(f"FS Check Error: {e}")
        # If check fails (e.g. bot not admin), we default to allowing the user
        # to prevent locking everyone out due to a config error.
        
    # --- END CHECK ---

    status_msg = bot.reply_to(message, "⏳ Generating links...")

    result = fetch_terabox_data(url_text)

    if result:
        text, markup = result
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            text=text,
            reply_markup=markup
        )
    else:
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            text="❌ Failed. Link might be broken or private."
        )


# --------------- ROBUST RUNNER ------------
def run_bot():
    print("--- STARTING BOT PRODUCTION BUILD ---")
    
    # 1. Kill any existing webhook interactions
    try:
        logger.info("Clearing previous updates...")
        bot.delete_webhook(drop_pending_updates=True)
        time.sleep(1)
    except Exception as e:
        logger.warning(f"Webhook clear warning: {e}")

    # 2. Main Loop
    while True:
        try:
            logger.info("Polling started...")
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        
        except apihelper.ApiTelegramException as e:
            if e.error_code == 409:
                logger.critical("❌ ERROR 409: CONFLICT DETECTED")
                logger.critical("Another bot instance is active. REVOKE YOUR TOKEN IN BOTFATHER.")
                time.sleep(20) # Wait longer to avoid log spam
            else:
                logger.error(f"Telegram API Error: {e}")
                time.sleep(5)
        
        except Exception as e:
            logger.error(f"Crash: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_bot()
