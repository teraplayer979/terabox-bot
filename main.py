import telebot

TOKEN = "8469056505:AAGXw6db-IgoH9XiY77x2_EOf5gWHijzwuw"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Send your Terabox link.")

@bot.message_handler(func=lambda m: True)
def handle(message):
    bot.reply_to(message, "Processing your link...")

print("Bot is running...")
bot.infinity_polling()
