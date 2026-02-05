import telebot
import os

TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    print("BOT_TOKEN missing")
    exit()

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg, "Bot is working!")

print("Bot started")
bot.infinity_polling()
