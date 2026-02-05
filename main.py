import telebot
import os

TOKEN = os.environ.get("8469056505:AAF5sUmwOFivt2fQ4oJHxARZMiIgW2orXVI")

if not TOKEN:
    print("BOT_TOKEN missing")
    exit()

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg, "Bot is working!")

print("Bot started")
bot.infinity_polling()
