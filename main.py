import os
import time
import logging
import requests
import telebot

# --- 1. CONFIGURATION & LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
XAPIVERSE_KEY = os.getenv("XAPIVERSE_KEY")

if not BOT_TOKEN or not XAPIVERSE_KEY:
    logger.error("CRITICAL: BOT_TOKEN or XAPIVERSE_KEY missing!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# --- 2. ADVANCED DATA EXTRACTION ---

def recursive_search(data, target_key):
    """
    Deeply searches for a specific key in any nested dictionary or list.
    """
    if isinstance(data, dict):
        if target_key in data:
            return data[target_key]
        for key, value in data.items():
            result = recursive_search(value, target_key)
            if result:
                return result
    elif isinstance(data, list):
        for item in data:
            result = recursive_search(item, target_key)
            if result:
                return result
    return None

def extract_download_info(json_data):
    """
    Extracts name, size, and link by checking multiple known structures
    and falling back to a deep recursive search.
    """
    try:
        # Log the full response for debugging in Railway logs
        logger.info(f"FULL API RESPONSE: {json_data}")

        # 1. Try to find the data container
        content = json_data.get("data") or json_data.get("result") or json_data
        
        # 2. Extract File Name
        file_name = (
            content.get("file_name") or 
            content.get("filename") or 
            recursive_search(json_data, "file_name") or 
            "Unknown_File"
        )

        # 3. Extract Size
        file_size = (
            content.get("size") or 
            content.get("filesize") or 
            recursive_search(json_data, "size") or 
            "Unknown"
        )

        # 4. Extract Direct Link (Priority list)
        # We check specific common keys first, then search everywhere
        dl_link = (
            content.get("direct_link") or 
            content.get("download_link") or 
            content.get("url") or 
            content.get("dlink") or
            recursive_search(json_data, "direct_link") or
            recursive_search(json_data, "download_link") or
            recursive_search(json_data, "url")
        )

        if not dl_link:
            return "❌ Download link not found in the API response structure."

        # Safety: Ensure name isn't too long for Telegram
        if len(str(file_name)) > 150:
            file_name = str(file_name)[:147] + "..."

        message = (
            f"📦 **File:** `{file_name}`\n"
            f"⚖️ **Size:** {file_size}\n\n"
            f"🚀 **Direct Link:**\n`{dl_link}`"
        )
        
        # Telegram Message Length Protection (4096 limit)
        return message[:4000]

    except Exception as e:
        logger.error(f"Extraction Error: {e}")
        return "⚠️ Failed to parse response. Check logs for the JSON structure."

# --- 3. BOT HANDLERS ---

@bot.message_handler(commands=['start', 'help'])
def welcome(message):
    bot.reply_to(message, "✅ **Terabox Link Downloader Ready**\nSend a link to get the direct download data.")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    url_text = message.text.strip()
    
    if "terabox" not in url_text and "1024tera" not in url_text:
        return

    wait_msg = bot.reply_to(message, "⏳ *Processing link...*", parse_mode="Markdown")

    try:
        api_url = "https://xapiverse.com/api/terabox"
        headers = {
            "Content-Type": "application/json",
            "xAPIverse-Key": XAPIVERSE_KEY
        }
        payload = {"url": url_text}

        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            # Pass data to the deep extraction function
            final_text = extract_download_info(data)
            
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=wait_msg.message_id,
                text=final_text,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        else:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=wait_msg.message_id,
                text=f"❌ **API Server Error:** Status code {response.status_code}"
            )

    except Exception as e:
        logger.error(f"Handler Error: {e}")
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=wait_msg.message_id,
            text="⚠️ An unexpected error occurred. Connection timed out or structure changed."
        )

# --- 4. PRODUCTION RUNNER ---

def run_production():
    logger.info("Bot starting up...")
    
    # Pre-start: Clean up previous sessions to avoid 409 Conflict
    try:
        bot.remove_webhook()
        time.sleep(2)
    except:
        pass

    while True:
        try:
            logger.info("Bot is polling...")
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            logger.error(f"Polling Restarting due to: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_production()
