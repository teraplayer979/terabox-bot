import os
import requests
import telebot

# Load environment variables
BOT_TOKEN = os.getenv("8469056505:AAHykdxXeNfLYOEQ85ETsPXJv06ZoP6Q0fs")
API_KEY = os.getenv("sk_8c0eeebef5d2e808af9e554ef1f6b908")

# Safety check
if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN not found. Set it in Railway variables.")
    exit()

if not API_KEY:
    print("ERROR: XAPIVERSE_KEY not found. Set it in Railway variables.")
    exit()

bot = telebot.TeleBot(BOT_TOKEN)

API_URL = "https://xapiverse.com/api/terabox"


@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Send a TeraBox link to download.")


@bot.message_handler(func=lambda m: True)
def handle_link(message):
    link = message.text.strip()

    if "terabox" not in link:
        bot.reply_to(message, "Please send a valid TeraBox link.")
        return

    bot.reply_to(message, "Processing link...")

    try:
        response = requests.post(
            API_URL,
            headers={
                "Content-Type": "application/json",
                "xAPIverse-Key": API_KEY
            },
            json={"url": link},
            timeout=30
        )

        data = response.json()

        if data.get("status") != "success":
            bot.reply_to(message, "Failed to extract link.")
            return

        file = data["list"][0]
        name = file["name"]
        size = file["size_formatted"]
        download = file["download_link"]

        msg = f"Name: {name}\nSize: {size}\nDownload:\n{download}"
        bot.reply_to(message, msg)

    except Exception as e:
        print("Error:", e)
        bot.reply_to(message, "Error processing link.")


print("Bot is running...")
bot.infinity_polling()
