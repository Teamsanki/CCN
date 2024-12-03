import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackContext
from pymongo import MongoClient
from datetime import datetime
import random

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Token and Database Configuration
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
MONGO_URL = "YOUR_MONGO_URL"
LOGGER_GROUP_CHAT_ID = "YOUR_LOGGER_GROUP_CHAT_ID"
OWNER_SUPPORT_CHANNEL = "YOUR_SUPPORT_CHANNEL"
OWNER_TELEGRAM_ID = "YOUR_OWNER_TELEGRAM_ID"

# MongoDB setup
client = MongoClient(MONGO_URL)
db = client['bot_database']
users_collection = db['users']
private_groups_collection = db['private_groups']

# Bot start time
bot_start_time = datetime.now()

# Helper Functions
def increment_user_count(user_id):
    """Adds a user to the database or updates their existing record."""
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id}, "$setOnInsert": {"getpvt_count": 0, "received_links": []}},
        upsert=True
    )

def increment_getpvt_usage(user_id):
    """Increments the `/getpvt` usage count for a user."""
    users_collection.update_one({"user_id": user_id}, {"$inc": {"getpvt_count": 1}})

def get_bot_stats():
    """Returns total users and `/getpvt` usage stats."""
    total_users = users_collection.count_documents({})
    total_getpvt_usage = users_collection.aggregate([{"$group": {"_id": None, "total": {"$sum": "$getpvt_count"}}}])
    total_getpvt_usage = next(total_getpvt_usage, {}).get("total", 0)
    return total_users, total_getpvt_usage

def get_uptime():
    """Calculates bot uptime."""
    delta = datetime.now() - bot_start_time
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"

# Command Handlers
async def start(update: Update, context: CallbackContext) -> None:
    """Handles the `/start` command."""
    user = update.message.from_user
    welcome_text = (
        f"*🎉 Welcome to Our Bot, {user.first_name}! 🎉*\n\n"
        "Hello, *{user.first_name}* 👋\n\n"
        "Thank you for starting the bot! We're here to help you.\n\n"
        "🔹 Click below to access support or contact the owner directly!\n\n"
        "*Enjoy your experience! 🚀*"
    )
    photo_url = "https://example.com/photo.jpg"  # Replace with actual photo URL

    await update.message.reply_photo(photo_url, caption=welcome_text, parse_mode='Markdown')
    keyboard = [
        [InlineKeyboardButton("🛠 Contact Support", url=OWNER_SUPPORT_CHANNEL)],
        [InlineKeyboardButton("💬 Message Owner", url=f"tg://user?id={OWNER_TELEGRAM_ID}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Tap below to get support or contact the owner:", reply_markup=reply_markup)

    increment_user_count(user.id)

async def addgc(update: Update, context: CallbackContext) -> None:
    """Handles the `/addgc` command for the owner."""
    if update.message.from_user.id != int(OWNER_TELEGRAM_ID):
        await update.message.reply_text("This command is restricted to the owner only.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /addgc <group_link>")
        return

    group_link = context.args[0]
    private_groups_collection.insert_one({"link": group_link})
    await update.message.reply_text(f"Group link added: {group_link}")

async def deletegc(update: Update, context: CallbackContext) -> None:
    """Handles the `/deletegc` command for the owner."""
    if update.message.from_user.id != int(OWNER_TELEGRAM_ID):
        await update.message.reply_text("This command is restricted to the owner only.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /deletegc <group_link>")
        return

    group_link = context.args[0]
    result = private_groups_collection.delete_one({"link": group_link})
    if result.deleted_count > 0:
        await update.message.reply_text(f"Deleted group link: {group_link}")
    else:
        await update.message.reply_text("Group link not found.")

async def getpvt(update: Update, context: CallbackContext) -> None:
    """Handles the `/getpvt` command to fetch a unique group link."""
    user_id = update.message.from_user.id
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        increment_user_count(user_id)
        user = users_collection.find_one({"user_id": user_id})

    received_links = user.get("received_links", [])
    all_links = list(private_groups_collection.find())
    available_links = [link for link in all_links if link['link'] not in received_links]

    if available_links:
        selected_link = random.choice(available_links)
        users_collection.update_one({"user_id": user_id}, {"$push": {"received_links": selected_link['link']}})
        increment_getpvt_usage(user_id)

        log_message = f"User @{update.message.from_user.username} ({user_id}) used `/getpvt`."
        await context.bot.send_message(chat_id=LOGGER_GROUP_CHAT_ID, text=log_message)

        await update.message.reply_text(f"Here is your private group link: {selected_link['link']}")
    else:
        await update.message.reply_text("No unique group links are currently available.")

async def stats(update: Update, context: CallbackContext) -> None:
    """Handles the `/stats` command for the owner."""
    if update.message.from_user.id != int(OWNER_TELEGRAM_ID):
        await update.message.reply_text("This command is restricted to the owner only.")
        return

    total_users, total_getpvt_usage = get_bot_stats()
    uptime = get_uptime()
    await update.message.reply_text(
        f"📊 *Bot Stats:*\n\n"
        f"👥 Total Users: {total_users}\n"
        f"🔄 Total `/getpvt` Uses: {total_getpvt_usage}\n"
        f"⏱ Uptime: {uptime}",
        parse_mode='Markdown'
    )

async def broadcast(update: Update, context: CallbackContext) -> None:
    """Handles the `/broadcast` command for the owner."""
    if update.message.from_user.id != int(OWNER_TELEGRAM_ID):
        await update.message.reply_text("This command is restricted to the owner only.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    message = " ".join(context.args)
    users = users_collection.find()
    count = 0
    for user in users:
        try:
            await context.bot.send_message(chat_id=user["user_id"], text=message)
            count += 1
        except Exception as e:
            logger.error(f"Failed to send message to {user['user_id']}: {e}")

    await update.message.reply_text(f"Broadcast sent to {count} users.")

async def help_command(update: Update, context: CallbackContext) -> None:
    """Provides a list of all public commands."""
    help_text = (
        "Here are the available commands:\n\n"
        "/start - Start the bot and receive a welcome message\n"
        "/getpvt - Get a unique private group link\n"
        "/stats - View bot stats (owner only)\n"
        "/broadcast - Broadcast a message to all users (owner only)\n"
        "For support, contact the owner or visit our support channel."
    )
    await update.message.reply_text(help_text)

# Main Function
def main():
    """Run the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Command Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addgc", addgc))  # Owner command
    application.add_handler(CommandHandler("deletegc", deletegc))  # Owner command
    application.add_handler(CommandHandler("getpvt", getpvt))
    application.add_handler(CommandHandler("stats", stats))  # Owner command
    application.add_handler(CommandHandler("broadcast", broadcast))  # Owner command
    application.add_handler(CommandHandler("help", help_command))

    application.run_polling()

if __name__ == "__main__":
    main()
