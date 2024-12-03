import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler
import os
from pymongo import MongoClient
from datetime import datetime
import random

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Replace this with your bot's token from BotFather
TELEGRAM_TOKEN = "7955924885:AAE-dBnJeTYKu0vFSmF7AAYS0IZOlHeQNsg"

# MongoDB URL
MONGO_URL = "mongodb+srv://Teamsanki:Teamsanki@cluster0.jxme6.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Replace this with your logger group chat ID (it should be negative for groups)
LOGGER_GROUP_CHAT_ID = "-1002100433415"

# Replace with your support channel link and owner's Telegram ID
OWNER_SUPPORT_CHANNEL = "https://t.me/matalbi_duniya"
OWNER_TELEGRAM_ID = "7877197608"

# MongoDB Client and Database
client = MongoClient(MONGO_URL)
db = client['bot_database']
users_collection = db['users']
private_groups_collection = db['private_groups']
requests_collection = db['requests']

# Bot start time (used for uptime calculation)
bot_start_time = datetime.now()

# Function to increment the user count in MongoDB
def increment_user_count(user_id):
    users_collection.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)

# Function to calculate uptime
def get_uptime():
    delta = datetime.now() - bot_start_time
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"

async def start(update: Update, context: CallbackContext) -> None:
    """Sends an attractive welcome message with a photo when the bot is started, and logs to the logger group."""

    # Attractive welcome message with a photo
    welcome_text = (
        "*🎉 Welcome to Our Bot, {user_name}! 🎉*\n\n"
        "Hello, *{user_name}* 👋\n\n"
        "Thank you for starting the bot! We're here to help you.\n\n"
        "🔹 Click below to access support or contact the owner directly!\n\n"
        "*Enjoy your experience! 🚀*"
    ).format(user_name=update.message.from_user.first_name)

    # Send welcome message with photo and Markdown formatting
    photo_url = "https://graph.org/file/6c0db28a848ed4dacae56-93b1bc1873b2494eb2.jpg"  # Replace with actual photo URL
    media = InputMediaPhoto(media=photo_url, caption=welcome_text, parse_mode='Markdown')
    await update.message.reply_media_group([media])

    # Create an inline keyboard with a link to the owner's support channel and owner's Telegram ID
    keyboard = [
        [InlineKeyboardButton("🛠 Contact Support", url=OWNER_SUPPORT_CHANNEL)],
        [InlineKeyboardButton("💬 Message Owner", url=f"tg://user?id={OWNER_TELEGRAM_ID}")],
        [InlineKeyboardButton("Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the message with the inline keyboard
    await update.message.reply_text('Tap below to get support or contact the owner:', reply_markup=reply_markup)

    # Get user details
    user_name = update.message.from_user.first_name  # User's first name
    user_username = update.message.from_user.username  # User's username
    user_id = update.message.from_user.id  # User's ID

    # Prepare the log message
    log_message = f"◈𝐍𝐀𝐌𝐄 {user_name} \n\n(◈𝐔𝐒𝐄𝐑𝐍𝐀𝐌𝐄: @{user_username if user_username else 'No Username'}, \n\n◈𝐈𝐃: {user_id}) ʜᴀs sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ"
    
    # Log the user who started the bot (but without sending a message to the logger group on VPS startup)
    if not os.environ.get("IS_VPS"):
        await context.bot.send_message(chat_id=LOGGER_GROUP_CHAT_ID, text=log_message)

    # Increment the user count in MongoDB
    increment_user_count(user_id)

async def help_command(update: Update, context: CallbackContext) -> None:
    """Shows available commands to the user."""
    help_text = (
        "*Available Commands:*\n\n"
        "*User Commands:*\n"
        "1. /start - Start the bot\n"
        "2. /getpvt - Get random private group links\n\n"
        "3. /stats - Get bot Stats\n"
        "4. /req - Send your private group link request to the owner\n\n"
        "*Owner Commands:*\n"
        "1. /for <user_id> <message> - Send a message to a specific user"
    )

    keyboard = [
        [InlineKeyboardButton("🛠 Contact Support", url=OWNER_SUPPORT_CHANNEL)],
        [InlineKeyboardButton("💬 Message Owner", url=f"tg://user?id={OWNER_TELEGRAM_ID}")],
        [InlineKeyboardButton("Back", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(help_text, reply_markup=reply_markup)

async def getpvt(update: Update, context: CallbackContext) -> None:
    """Fetches 10 random private group links."""
    group_links = private_groups_collection.find()
    group_links_list = list(group_links)

    if len(group_links_list) >= 10:
        random_links = random.sample(group_links_list, 10)
        keyboard = [
            [InlineKeyboardButton(f"Group {i+1}", url=random_links[i]['link']) for i in range(5)],
            [InlineKeyboardButton(f"Group {i+6}", url=random_links[i+5]['link']) for i in range(5)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Here are 10 random private group links:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("No private group links available yet. Please try again later.")

async def req(update: Update, context: CallbackContext) -> None:
    """Allows users to request to add their private group link."""
    user_id = update.message.from_user.id
    if not context.args:
        await update.message.reply_text("Please provide your private group link. Usage: /req <link>")
        return

    group_link = context.args[0]
    request_message = f"User ID: {user_id}\nRequested Link: {group_link}"

    # Save the request to MongoDB
    try:
        requests_collection.insert_one({"user_id": user_id, "message": request_message})
        await update.message.reply_text(f"Your request has been sent to the owner.")
        # Send the request to the owner
        await context.bot.send_message(chat_id=OWNER_TELEGRAM_ID, text=request_message)
    except Exception as e:
        await update.message.reply_text(f"Failed to send your request. Error: {e}")

async def for_command(update: Update, context: CallbackContext) -> None:
    """Owner command to forward message to a user."""
    if update.message.from_user.id != int(OWNER_TELEGRAM_ID):
        await update.message.reply_text("This command is restricted to the owner only.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Please provide the user ID and message. Usage: /for <user_id> <message>")
        return

    user_id = int(context.args[0])
    message = " ".join(context.args[1:])

    try:
        await context.bot.send_message(user_id, message)
        await update.message.reply_text(f"Message sent to user {user_id}.")
    except Exception as e:
        await update.message.reply_text(f"Failed to send message. Error: {e}")

async def ping(update: Update, context: CallbackContext) -> None:
    """Respond with the bot's uptime."""
    uptime = get_uptime()
    await update.message.reply_text(f"Bot Uptime: {uptime}")

def main():
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addgc", add_group))
    application.add_handler(CommandHandler("req", req))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("getpvt", getpvt))
    application.add_handler(CommandHandler("stats", ping))
    application.add_handler(CommandHandler("for", for_command))

    application.run_polling()

if __name__ == '__main__':
    main()
