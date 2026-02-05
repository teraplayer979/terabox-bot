import os
import time
import logging
import requests
import telebot
from telebot import types

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
XAPIVERSE_KEY = os.getenv("XAPIVERSE_KEY")

# Safety Check: Ensure tokens exist before starting
if not BOT_TOKEN:
    logger.error("ERROR: BOT_TOKEN not found in environment variables.")
    exit(1)
if not XAPIVERSE_KEY:
    logger.error("ERROR: XAPIVERSE_KEY not found in environment variables.")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "👋 Welcome! Send me a Terabox link, and I will fetch the download data for you.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.strip()
    
    # Simple validation for Terabox links
    if "terabox" not in text:
        bot.reply_to(message, "❌ Please send a valid Terabox link.")
        return

    processing_msg = bot.reply_to(message, "🔍 Processing your link... Please wait.")
    
    try:
        # xAPIverse API endpoint
        api_url = "https://xapiverse.com/api/terabox"
        params = {
            "url": text,
            "key": XAPIVERSE_KEY
        }
        
        response = requests.get(api_url, params=params, timeout=30)
        data = response.json()

        if response.status_code == 200 and data:
            # Format the response based on typical xAPIverse output
            # You can customize this based on the exact JSON structure returned
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=processing_msg.message_id,
                text=f"✅ **Data Retrieved Successfully!**\n\n`{data}`",
                parse_mode="Markdown"
            )
        else:
            error_msg = data.get("message", "Unknown error from API")
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=processing_msg.message_id,
                text=f"❌ **API Error:** {error_msg}"
            )

    except Exception as e:
        logger.error(f"Error processing link: {e}")
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=processing_msg.message_id,
            text="⚠️ An internal error occurred while fetching the data."
        )

def run_bot():
    while True:
        try:
            logger.info("Bot is starting...")
            # Remove webhooks to prevent 409 Conflict
            bot.remove_webhook()
            # Start polling
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            # Wait 5 seconds before restarting to avoid rapid crash loops
            time.sleep(5)

if __name__ == "__main__":
    run_bot()
