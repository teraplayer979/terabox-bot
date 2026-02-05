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

# Load Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
XAPIVERSE_KEY = os.getenv("XAPIVERSE_KEY")

if not BOT_TOKEN or not XAPIVERSE_KEY:
    logger.error("CRITICAL: BOT_TOKEN or XAPIVERSE_KEY is missing!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# --- 2. DATA EXTRACTION LOGIC ---

def format_size(size_bytes):
    """Converts bytes to a readable MB/GB format."""
    try:
        size_bytes = int(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
    except:
        return "Unknown Size"

def extract_best_link(data):
    """
    Parses xAPIverse response specifically looking for stable download URLs.
    """
    try:
        # Log the full response for debugging in Railway
        logger.info(f"API RESPONSE: {data}")

        # xAPIverse usually returns data inside a 'data' object
        info = data.get("data", {}) if isinstance(data.get("data"), dict) else data
        
        # 1. Get File Metadata
        file_name = info.get("file_name") or info.get("filename") or "File_Generated"
        raw_size = info.get("size") or info.get("filesize") or 0
        readable_size = format_size(raw_size)

        # 2. Get the Link (Priority: download_link > direct_link > dlink > url)
        # xAPIverse often provides a 'download_link' which is more stable than the worker URL
        dl_link = (
            info.get("download_link") or 
            info.get("direct_link") or 
            info.get("dlink") or 
            info.get("url")
        )

        if not dl_link:
            return "❌ No valid download link was found in the API response."

        # 3. Message Formatting & Length Protection
        if len(file_name) > 100:
            file_name = file_name[:97] + "..."

        msg = (
            f"✅ **Link Generated!**\n\n"
            f"📦 **File:** `{file_name}`\n"
            f"⚖️ **Size:** {readable_size}\n\n"
            f"🚀 **Download Link:**\n`{dl_link}`\n\n"
            f"⚠️ *Note: If the link shows 'Forbidden', try opening it in an Incognito window or a different browser.*"
        )
        
        return msg[:4000] # Telegram limit safety

    except Exception as e:
        logger.error(f"Extraction Error: {e}")
        return "⚠️ Failed to parse API response. Please check Railway logs."

# --- 3. BOT HANDLERS ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "👋 **Terabox Downloader**\n\nSend me any Terabox link and I will generate a direct download link for you.")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    url = message.text.strip()
    
    if "terabox" not in url and "1024tera" not in url:
        return

    status = bot.reply_to(message, "⏳ *Requesting direct access from xAPIverse...*", parse_mode="Markdown")

    try:
        # xAPIverse API endpoint
        api_url = "https://xapiverse.com/api/terabox"
        
        headers = {
            "Content-Type": "application/json",
            "xAPIverse-Key": XAPIVERSE_KEY
        }
        
        payload = {"url": url}

        # Higher timeout for Terabox link generation
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            json_data = response.json()
            
            # Check for API-side errors
            if json_data.get("status") == "error":
                result_text = f"❌ **API Error:** {json_data.get('message', 'Link generation failed')}"
            else:
                result_text = extract_best_link(json_data)
        
        elif response.status_code == 401:
            result_text = "❌ **Invalid API Key.** Please check your XAPIVERSE_KEY environment variable."
        else:
            result_text = f"❌ **Server Error:** API returned status `{response.status_code}`"

        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status.message_id,
            text=result_text,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

    except requests.exceptions.Timeout:
        bot.edit_message_text(chat_id=message.chat.id, message_id=status.message_id, text="⏰ **Timeout:** The API took too long to respond.")
    except Exception as e:
        logger.error(f"General Error: {e}")
        bot.edit_message_text(chat_id=message.chat.id, message_id=status.message_id, text="⚠️ An unexpected error occurred.")

# --- 4. PRODUCTION POLLING LOOP ---

def start_bot():
    logger.info("Bot is starting...")
    
    # Force clean start for Railway
    try:
        bot.remove_webhook()
        time.sleep(2)
    except:
        pass

    while True:
        try:
            logger.info("Polling for messages...")
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    start_bot()
