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

# Load and Verify Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
XAPIVERSE_KEY = os.getenv("XAPIVERSE_KEY")

if not BOT_TOKEN or not XAPIVERSE_KEY:
    logger.error("CRITICAL: BOT_TOKEN or XAPIVERSE_KEY is missing!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# --- 2. BOT HANDLERS ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🚀 **Terabox Downloader Active**\n\nSend me a Terabox link to get the direct download data.")

@bot.message_handler(func=lambda message: True)
def handle_terabox_link(message):
    url = message.text.strip()
    
    # Basic Validation
    if "terabox" not in url and "1024tera" not in url:
        bot.reply_to(message, "❌ Please send a valid Terabox link.")
        return

    status_msg = bot.reply_to(message, "⏳ Fetching data from xAPIverse...")

    try:
        # xAPIverse API Request (POST with Headers)
        api_url = "https://xapiverse.com/api/terabox"
        headers = {
            "Content-Type": "application/json",
            "xAPIverse-Key": XAPIVERSE_KEY
        }
        payload = {"url": url}

        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            # Send the result back to the user
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=status_msg.message_id,
                text=f"✅ **Data Retrieved:**\n\n`{data}`",
                parse_mode="Markdown"
            )
        else:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=status_msg.message_id,
                text=f"❌ **API Error ({response.status_code}):** {response.text}"
            )

    except Exception as e:
        logger.error(f"Request Error: {e}")
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            text="⚠️ Connection error. Please try again later."
        )

# --- 3. PRODUCTION-READY STARTUP ---

def run_bot():
    logger.info("Starting bot...")
    
    # Force remove any existing webhooks or conflicting sessions
    try:
        bot.remove_webhook()
        time.sleep(2) # Give Telegram time to clear the session
    except Exception as e:
        logger.warning(f"Could not remove webhook: {e}")

    while True:
        try:
            logger.info("Bot is now polling for messages.")
            bot.polling(none_stop=True, interval=1, timeout=20)
        except Exception as e:
            logger.error(f"Polling conflict or error: {e}")
            # Wait 5 seconds before restarting to prevent rapid crash loops
            time.sleep(5)

if __name__ == "__main__":
    run_bot()
