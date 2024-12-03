import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackContext
import os
from pymongo import MongoClient
from datetime import datetime
import random

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Replace with your bot's token, MongoDB URL, logger group chat ID, and support channel link
TELEGRAM_TOKEN = "7955924885:AAE-dBnJeTYKu0vFSmF7AAYS0IZOlHeQNsg"
MONGO_URL = "mongodb+srv://Teamsanki:Teamsanki@cluster0.jxme6.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
LOGGER_GROUP_CHAT_ID = "-1002100433415"
OWNER_SUPPORT_CHANNEL = "https://t.me/matalbi_duniya"
OWNER_TELEGRAM_ID = "7877197608"

# MongoDB Client and Database
client = MongoClient(MONGO_URL)
db = client['bot_database']
users_collection = db['users']
private_groups_collection = db['private_groups']

# Bot start time (used for uptime calculation)
bot_start_time = datetime.now()

# Function to calculate uptime
def get_uptime():
    delta = datetime.now() - bot_start_time
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"

# Increment user count and track usage
def increment_user_count(user_id, command=None):
    users_collection.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)
    if command:
        users_collection.update_one({"user_id": user_id}, {"$inc": {f"{command}_count": 1}}, upsert=True)

# Get total user count
def get_total_users():
    return users_collection.count_documents({})

# Get total command usage
def get_command_usage(command):
    return sum(user.get(f"{command}_count", 0) for user in users_collection.find())

# Start Command
async def start(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    user_name = user.first_name
    user_id = user.id
    increment_user_count(user_id)

    # Log user start
    log_message = (
        f"◈ *User Started Bot* ◈\n"
        f"Name: {user_name}\n"
        f"ID: `{user_id}`\n"
        f"Username: @{user.username if user.username else 'No Username'}"
    )
    await context.bot.send_message(chat_id=LOGGER_GROUP_CHAT_ID, text=log_message, parse_mode="Markdown")

    # Welcome Message
    welcome_text = (
        f"*🎉 Welcome, {user_name}! 🎉*\n\n"
        "Thank you for starting our bot! Use the buttons below to navigate.\n\n"
        "🔹 *Click on 'Help' for commands.*\n"
        "🔹 *Tap 'Support' to contact us!*\n\n"
        "*Enjoy your experience!* 🚀"
    )
    photo_url = "https://graph.org/file/6c0db28a848ed4dacae56-93b1bc1873b2494eb2.jpg"
    media = InputMediaPhoto(media=photo_url, caption=welcome_text, parse_mode='Markdown')

    keyboard = [
        [InlineKeyboardButton("🆘 Help", callback_data="help"),
         InlineKeyboardButton("📞 Support", url=OWNER_SUPPORT_CHANNEL)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_media_group([media])
    await update.message.reply_text("👇 Use the buttons below:", reply_markup=reply_markup)

# Help Command
async def help_command(update: Update, context: CallbackContext) -> None:
    commands = [
        ("Start", "/start"),
        ("Ping", "/ping"),
        ("Get Private Group", "/getpvt"),
        ("Broadcast (Owner)", "/broadcast <message>")
    ]
    keyboard = [[InlineKeyboardButton(f"➤ {name}", callback_data=cmd)] for name, cmd in commands]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Here are the available commands:", reply_markup=reply_markup)

# Ping Command
async def ping(update: Update, context: CallbackContext) -> None:
    total_users = get_total_users()
    uptime = get_uptime()
    await update.message.reply_text(f"Bot Uptime: {uptime}\nTotal Users: {total_users}")

# Add Private Group Links Categorically
async def addgc(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id != int(OWNER_TELEGRAM_ID):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addgc <alphabet> <group_link>")
        return

    alphabet, link = context.args[0].upper(), context.args[1]
    if alphabet not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        await update.message.reply_text("Please provide a valid alphabet (A-Z).")
        return

    private_groups_collection.update_one({"alphabet": alphabet}, {"$addToSet": {"links": link}}, upsert=True)
    await update.message.reply_text(f"Link added under {alphabet}.")

# Get Private Group Links
async def getpvt(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    increment_user_count(user_id, command="getpvt")

    alphabets = private_groups_collection.find({}, {"alphabet": 1})
    buttons = [
        InlineKeyboardButton(letter["alphabet"], callback_data=f"get_{letter['alphabet']}")
        for letter in alphabets
    ]
    keyboard = [buttons[:13], buttons[13:]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose an alphabet:", reply_markup=reply_markup)

# Broadcast Message
async def broadcast(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id != int(OWNER_TELEGRAM_ID):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    message = " ".join(context.args)
    if not message:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    users = users_collection.find()
    count = 0
    for user in users:
        try:
            await context.bot.send_message(chat_id=user["user_id"], text=message)
            count += 1
        except:
            continue

    await update.message.reply_text(f"Broadcast sent to {count} users.")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("addgc", addgc))
    application.add_handler(CommandHandler("getpvt", getpvt))
    application.add_handler(CommandHandler("broadcast", broadcast))

    application.run_polling()

if __name__ == '__main__':
    main()
