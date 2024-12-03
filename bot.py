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

# Replace this with your bot's token from BotFather
TELEGRAM_TOKEN = "7955924885:AAE-dBnJeTYKu0vFSmF7AAYS0IZOlHeQNsg"

# MongoDB URL
MONGO_URL = "mongodb+srv://Teamsanki:Teamsanki@cluster0.jxme6.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Replace this with your logger group chat ID (it should be negative for groups)
LOGGER_GROUP_CHAT_ID = "-1002100433415"  # Example: @loggroupname or chat_id

# Replace with your support channel link and owner's Telegram ID
OWNER_SUPPORT_CHANNEL = "https://t.me/matalbi_duniya"
OWNER_TELEGRAM_ID = "7877197608"  # Example: "123456789" or "@username"

# MongoDB Client and Database
client = MongoClient(MONGO_URL)
db = client['bot_database']
users_collection = db['users']
private_groups_collection = db['private_groups']

# Bot start time (used for uptime calculation)
bot_start_time = datetime.now()

# Function to increment the user count in MongoDB
def increment_user_count(user_id):
    users_collection.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)

# Function to get the total number of unique users
def get_user_count():
    return users_collection.count_documents({})

# Function to calculate uptime
def get_uptime():
    delta = datetime.now() - bot_start_time
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"

async def start(update: Update, context: CallbackContext) -> None:
    """Handles the /start command."""
    user = update.message.from_user

    # Welcome message with a photo
    welcome_text = (
        f"*🎉 Welcome to Our Bot, {user.first_name}! 🎉*\n\n"
        "Hello, *{user.first_name}* 👋\n\n"
        "Thank you for starting the bot! We're here to help you.\n\n"
        "🔹 Click below to access support or contact the owner directly!\n\n"
        "*Enjoy your experience! 🚀*"
    )
    photo_url = "https://graph.org/file/6c0db28a848ed4dacae56-93b1bc1873b2494eb2.jpg"  # Replace with actual photo URL

    # Send welcome photo
    await update.message.reply_photo(photo_url, caption=welcome_text, parse_mode='Markdown')
    
    # Inline keyboard for support and owner contact
    keyboard = [
        [InlineKeyboardButton("🛠 Contact Support", url=OWNER_SUPPORT_CHANNEL)],
        [InlineKeyboardButton("💬 Message Owner", url=f"tg://user?id={OWNER_TELEGRAM_ID}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Tap below to get support or contact the owner:", reply_markup=reply_markup)

    # Log the start event to the logger group
    log_message = f"User @{user.username} (ID: {user.id}) started the bot."

    # Sending the log message to the logger group
    try:
        await context.bot.send_message(chat_id=LOGGER_GROUP_CHAT_ID, text=log_message)
    except Exception as e:
        logger.error(f"Failed to send log message to the logger group: {e}")

    # Increment user count in the database
    increment_user_count(user.id)

async def addgc(update: Update, context: CallbackContext) -> None:
    """Owner-only command to add a private group link."""
    if update.message.from_user.id != int(OWNER_TELEGRAM_ID):
        await update.message.reply_text("This command is restricted to the owner only.")
        return

    if not context.args:
        await update.message.reply_text("Please provide the private group link. Usage: /addgc <group_link>")
        return

    group_link = context.args[0]
    private_groups_collection.insert_one({"link": group_link})

    await update.message.reply_text(f"Group link added: {group_link}")

async def getpvt(update: Update, context: CallbackContext) -> None:
    """Fetches a random private group link."""
    group_links = list(private_groups_collection.find())

    if len(group_links) > 0:
        # Select a random group link
        random_group = random.choice(group_links)
        link = random_group['link']
        await update.message.reply_text(f"Here is a private group link: {link}")
        
        # Log the user's action of using getpvt command to the logger group
        user = update.message.from_user
        log_message = f"User @{user.username} (ID: {user.id}) used the /getpvt command and got the link: {link}."
        try:
            await context.bot.send_message(chat_id=LOGGER_GROUP_CHAT_ID, text=log_message)
        except Exception as e:
            logger.error(f"Failed to send log message to the logger group: {e}")
    else:
        await update.message.reply_text("Be patient! Latest link is coming soon.")

async def reset(update: Update, context: CallbackContext) -> None:
    """Owner-only command to reset (delete) all private group links."""
    if update.message.from_user.id != int(OWNER_TELEGRAM_ID):
        await update.message.reply_text("This command is restricted to the owner only.")
        return

    private_groups_collection.delete_many({})  # Delete all group links

    await update.message.reply_text("All group links have been reset.")

async def delete_gc(update: Update, context: CallbackContext) -> None:
    """Owner-only command to delete a specific group link."""
    if update.message.from_user.id != int(OWNER_TELEGRAM_ID):
        await update.message.reply_text("This command is restricted to the owner only.")
        return

    if not context.args:
        await update.message.reply_text("Please provide the group link to delete. Usage: /deletegc <group_link>")
        return

    group_link_to_delete = context.args[0]
    result = private_groups_collection.delete_one({"link": group_link_to_delete})

    if result.deleted_count > 0:
        await update.message.reply_text(f"Group link deleted: {group_link_to_delete}")
    else:
        await update.message.reply_text(f"Group link not found: {group_link_to_delete}")

async def help_command(update: Update, context: CallbackContext) -> None:
    """Shows available commands to the user, excluding owner-only commands."""
    help_text = (
        "Here are the available commands:\n\n"
        "/start - Start the bot\n"
        "/getpvt - Get a private group link\n"
        "/help - Show this help message\n"
        "/ping - Get bot uptime"
    )
    await update.message.reply_text(help_text)

async def ping(update: Update, context: CallbackContext) -> None:
    """Respond with the bot's uptime."""
    uptime = get_uptime()
    await update.message.reply_text(f"Bot Uptime: {uptime}")

async def stats(update: Update, context: CallbackContext) -> None:
    """Show bot statistics."""
    total_users = get_user_count()
    total_getpvt_uses = users_collection.aggregate([{"$group": {"_id": None, "total": {"$sum": 1}}}]).next()['total']
    stats_message = f"Total Users: {total_users}\nTotal /getpvt uses: {total_getpvt_uses}"
    await update.message.reply_text(stats_message)

def main():
    """Start the bot."""
    # Use the new Application class to replace the old Updater class
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addgc", addgc))  # Command to add a private group link
    application.add_handler(CommandHandler("getpvt", getpvt))  # Command to get private group links
    application.add_handler(CommandHandler("reset", reset))  # Command to reset private group links
    application.add_handler(CommandHandler("deletegc", delete_gc))  # Command to delete a group link
    application.add_handler(CommandHandler("help", help_command))  # Command for showing help
    application.add_handler(CommandHandler("ping", ping))  # Command for checking uptime
    application.add_handler(CommandHandler("stats", stats))  # Command to show bot stats

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
