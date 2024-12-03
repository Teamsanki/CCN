import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    CallbackContext,
)
import os
from pymongo import MongoClient
from datetime import datetime

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Replace these placeholders with your actual tokens and IDs
TELEGRAM_TOKEN = "7955924885:AAE-dBnJeTYKu0vFSmF7AAYS0IZOlHeQNsg"
MONGO_URL = "mongodb+srv://Teamsanki:Teamsanki@cluster0.jxme6.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
LOGGER_GROUP_CHAT_ID = "-1002100433415"
OWNER_SUPPORT_CHANNEL = "https://t.me/matalbi_duniya"
OWNER_TELEGRAM_ID = "7877197608"

# Secure password for admin access
ADMIN_PASSWORD = "SK112566#"

# MongoDB Client and Database
client = MongoClient(MONGO_URL)
db = client["bot_database"]
users_collection = db["users"]
private_groups_collection = db["private_groups"]

# Bot start time (used for uptime calculation)
bot_start_time = datetime.now()

# Store admin password verification status
admin_verifications = {}


def get_uptime():
    """Calculate the bot's uptime."""
    delta = datetime.now() - bot_start_time
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"


def increment_user_count(user_id):
    """Increment user count in MongoDB."""
    users_collection.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)


async def start(update: Update, context: CallbackContext) -> None:
    """Send a welcome message with inline buttons for support, owner, and help."""
    user = update.message.from_user
    photo_url = "https://graph.org/file/6c0db28a848ed4dacae56-93b1bc1873b2494eb2.jpg"
    welcome_text = (
        f"*🎉 Welcome to the Bot, {user.first_name}! 🎉*\n\n"
        "Thank you for starting the bot. Explore the commands using the buttons below!"
    )

    # Inline keyboard
    keyboard = [
        [InlineKeyboardButton("🛠 Support", url=OWNER_SUPPORT_CHANNEL)],
        [InlineKeyboardButton("💬 Owner", url=f"tg://user?id={OWNER_TELEGRAM_ID}")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send welcome photo and buttons
    await update.message.reply_photo(photo=photo_url, caption=welcome_text, parse_mode="Markdown", reply_markup=reply_markup)

    # Log user details
    log_message = (
        f"◈𝐍𝐀𝐌𝐄: {user.first_name} \n"
        f"◈𝐔𝐒𝐄𝐑𝐍𝐀𝐌𝐄: @{user.username if user.username else 'No Username'} \n"
        f"◈𝐈𝐃: {user.id} has started the bot."
    )
    if not os.environ.get("IS_VPS"):
        await context.bot.send_message(chat_id=LOGGER_GROUP_CHAT_ID, text=log_message)

    # Increment user count
    increment_user_count(user.id)


async def handle_help(update: Update, context: CallbackContext) -> None:
    """Show inline help menu with options for users and admin."""
    query = update.callback_query
    await query.answer()

    # Display user and admin options
    keyboard = [
        [InlineKeyboardButton("👤 User Commands", callback_data="help_user")],
        [InlineKeyboardButton("🔒 Admin Commands", callback_data="help_admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Choose an option:", reply_markup=reply_markup)


async def handle_user_help(update: Update, context: CallbackContext) -> None:
    """Show user commands."""
    query = update.callback_query
    await query.answer()

    user_help_text = (
        "👤 *User Commands*:\n\n"
        "/start - Start the bot\n"
        "/getpvt - Get private group links\n"
        "/help - View this help menu\n"
        "/ping - Check bot uptime"
    )
    await query.edit_message_text(user_help_text, parse_mode="Markdown")


async def handle_admin_help(update: Update, context: CallbackContext) -> None:
    """Ask for admin password to access admin commands."""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    # Check if the user has already verified
    if admin_verifications.get(user_id) == ADMIN_PASSWORD:
        await display_admin_commands(query)
        return

    # Ask for admin password
    await query.edit_message_text("🔒 Please enter the admin password:")
    admin_verifications[user_id] = None


async def handle_admin_password(update: Update, context: CallbackContext) -> None:
    """Validate the admin password and display admin commands."""
    user = update.message.from_user
    user_id = user.id
    if admin_verifications.get(user_id) is None:
        if update.message.text.strip() == ADMIN_PASSWORD:
            admin_verifications[user_id] = ADMIN_PASSWORD
            await update.message.reply_text("✅ Password verified!")
            await display_admin_commands(update.message)
        else:
            await update.message.reply_text("❌ Invalid password. Try again.")
    else:
        await update.message.reply_text("You are already verified as an admin!")


async def display_admin_commands(query_or_message):
    """Show admin commands."""
    admin_help_text = (
        "🔒 *Admin Commands*:\n\n"
        "/addgc <alphabet> <group_link> - Add a group link under an alphabet\n"
        "/broadcast <message> - Send a message to all users\n"
        "/getpvt - Fetch private group links alphabetically"
    )
    if isinstance(query_or_message, Update):
        await query_or_message.reply_text(admin_help_text, parse_mode="Markdown")
    else:
        await query_or_message.edit_message_text(admin_help_text, parse_mode="Markdown")


async def handle_broadcast(update: Update, context: CallbackContext) -> None:
    """Broadcast a message to all users."""
    user = update.message.from_user
    if admin_verifications.get(user.id) != ADMIN_PASSWORD:
        await update.message.reply_text("🔒 Admin access required to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    message = " ".join(context.args)
    users = users_collection.find({}, {"user_id": 1})
    for user in users:
        try:
            await context.bot.send_message(chat_id=user["user_id"], text=message)
        except Exception as e:
            logger.error(f"Failed to send message to {user['user_id']}: {e}")

    await update.message.reply_text("✅ Broadcast sent successfully!")


def main():
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("broadcast", handle_broadcast))
    application.add_handler(CallbackQueryHandler(handle_help, pattern="^help_main$"))
    application.add_handler(CallbackQueryHandler(handle_user_help, pattern="^help_user$"))
    application.add_handler(CallbackQueryHandler(handle_admin_help, pattern="^help_admin$"))
    application.add_handler(CommandHandler("addgc", handle_admin_password))
    application.add_handler(CommandHandler("help", handle_help))
    application.add_handler(CommandHandler("ping", lambda u, c: u.message.reply_text(f"Uptime: {get_uptime()}")))

    # Start the bot
    application.run_polling()


if __name__ == "__main__":
    main()
