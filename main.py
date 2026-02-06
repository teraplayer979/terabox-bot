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

# Force Subscribe Config
FS_CHANNEL_USERNAME = "@terabox_directlinks"
FS_CHANNEL_LINK = "https://t.me/terabox_directlinks"

# Auto-Posting Config
# distinct from the link, just the username string for comparison
SOURCE_GROUP_USERNAME = "terabox_movies_hub0" 
TARGET_CHANNEL_USERNAME = "@terabox_directlinks" 

PLAYER_BASE = "https://teraplayer979.github.io/stream-player/"

# --------------- LOGGING ----------------
# Set to DEBUG to see all internal details if needed, but INFO is good for general use
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

if not BOT_TOKEN or not XAPIVERSE_KEY:
    logger.error("Missing BOT_TOKEN or XAPIVERSE_KEY")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# --------------- SHARED API LOGIC ------------------
def fetch_terabox_data(url_text):
    """
    Helper function to process API logic. 
    Returns (text, markup) on success, or None on failure.
    """
    try:
        api_url = "https://xapiverse.com/api/terabox"
        headers = {
            "Content-Type": "application/json",
            "xAPIverse-Key": XAPIVERSE_KEY
        }
        payload = {"url": url_text}

        # logger.info(f"API Request: {payload}") # Uncomment for deep debugging
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        
        if response.status_code != 200:
            logger.error(f"API Error: {response.status_code}")
            return None

        json_data = response.json()
        file_list = json_data.get("list", [])
        
        if not file_list:
            logger.warning("API returned success but 'list' was empty.")
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
            logger.warning("No watchable URL found in API response.")
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


# --------------- START ------------------
@bot.message_handler(commands=["start", "help"])
def start(message):
    bot.reply_to(message, "Send a Terabox link to stream or download.")


# --------------- AUTO-POST HANDLER (GROUP) -----------
# Triggers for ANY text message in a group/supergroup
@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'], content_types=['text'])
def handle_group_message(message):
    try:
        # 1. LOGGING: Check what the bot sees
        chat_username = message.chat.username or ""
        text_preview = message.text[:20] if message.text else "No Text"
        logger.info(f"Group Msg Detected | Chat: @{chat_username} | ID: {message.chat.id} | Text: {text_preview}...")

        # 2. VALIDATION: Check if this is the correct source group
        # Normalize both to lowercase and remove '@' for comparison
        clean_chat_username = chat_username.replace("@", "").lower()
        clean_target_group = SOURCE_GROUP_USERNAME.replace("@", "").lower()

        if clean_chat_username != clean_target_group:
            # Silence this log if you are in many groups to avoid spam
            logger.info(f"Ignored message from wrong group: {clean_chat_username}")
            return

        # 3. LINK CHECK: Check for keywords
        url_text = message.text.strip()
        if "terabox" not in url_text and "1024tera" not in url_text:
            logger.info("Message ignored: No Terabox keyword found.")
            return

        logger.info(f"✅ VALID LINK in Source Group! Processing: {url_text}")

        # 4. PROCESSING
        result = fetch_terabox_data(url_text)

        if result:
            text, markup = result
            try:
                # Post to Target Channel
                bot.send_message(
                    chat_id=TARGET_CHANNEL_USERNAME,
                    text=text,
                    reply_markup=markup
                )
                logger.info(f"🚀 SUCCESS: Auto-posted '{text.splitlines()[2]}' to {TARGET_CHANNEL_USERNAME}")
            except Exception as e:
                logger.error(f"❌ FAILED to post to channel: {e}")
        else:
            logger.warning("❌ Failed to fetch data from API (Result was None).")

    except Exception as e:
        logger.error(f"CRITICAL ERROR in Group Handler: {e}")


# --------------- PRIVATE HANDLER (USER) -----------
# Triggers for Private Chats Only
@bot.message_handler(func=lambda m: m.chat.type == 'private', content_types=['text'])
def handle_private_link(message):
    url_text = message.text.strip()

    if "terabox" not in url_text and "1024tera" not in url_text:
        return

    # --- FORCE SUBSCRIBE CHECK ---
    user_id = message.from_user.id
    try:
        member_status = bot.get_chat_member(FS_CHANNEL_USERNAME, user_id).status
        # Valid statuses: creator, administrator, member
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
        logger.error(f"Force Subscribe Check Failed: {e}")
        bot.reply_to(message, "⚠️ Error verifying subscription.")
        return
    # --- END FORCE SUBSCRIBE CHECK ---

    status_msg = bot.reply_to(message, "⏳ Generating links...")

    # Process with visual feedback
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
            text=f"❌ Failed to generate link or no file found.\n(API Key: {XAPIVERSE_KEY[:4]}***)"
        )


# --------------- SAFE RUNNER ------------
def run_bot():
    logger.info("Bot starting... Waiting for messages...")
    try:
        bot.remove_webhook()
        time.sleep(1)
    except:
        pass

    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            logger.error(f"Polling crashed: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_bot()
