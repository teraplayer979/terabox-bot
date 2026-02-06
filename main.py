import os
import time
import logging
import telebot

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")

# --------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not BOT_TOKEN:
    logger.error("Missing BOT_TOKEN")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# --------------- START ------------------
@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "Bot is running. Send any message in group to get group ID.")

# --------------- GROUP DEBUG HANDLER -----------
@bot.message_handler(func=lambda message: True)
def debug_group(message):
    chat = message.chat
    
    logger.info("----- GROUP DEBUG -----")
    logger.info(f"Chat Title: {chat.title}")
    logger.info(f"Chat ID: {chat.id}")
    logger.info(f"Chat Type: {chat.type}")
    logger.info("-----------------------")

# --------------- SAFE RUNNER ------------
def run_bot():
    logger.info("Debug bot starting...")
    try:
        bot.remove_webhook()
        time.sleep(3)
    except:
        pass

    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            logger.error(f"Polling crashed: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_bot()
