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

# Bot start time (used for uptime calculation)
bot_start_time = datetime.now()

# Admin password
ADMIN_PASSWORD = "112566"

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
        [InlineKeyboardButton("ℹ️ Help", callback_data="help_commands")]
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

async def addgc(update: Update, context: CallbackContext) -> None:
    """Owner-only command to add a private group link."""
    if update.message.from_user.id != int(OWNER_TELEGRAM_ID):
        await update.message.reply_text("This command is restricted to the owner only.")
        return

    if not context.args:
        await update.message.reply_text("Please provide the private group link. Usage: /addgc <group_link>")
        return

    group_link = context.args[0]

    # Insert the group link into MongoDB
    try:
        private_groups_collection.insert_one({"link": group_link})
        await update.message.reply_text(f"Group link added: {group_link}")
    except Exception as e:
        await update.message.reply_text(f"Failed to add the group link. Error: {e}")

async def getpvt(update: Update, context: CallbackContext) -> None:
    """Fetches a random private group link from the owner's collection."""
    # Create inline buttons for 1-5 links
    keyboard = [
        [InlineKeyboardButton("1", callback_data="link_1")],
        [InlineKeyboardButton("2", callback_data="link_2")],
        [InlineKeyboardButton("3", callback_data="link_3")],
        [InlineKeyboardButton("4", callback_data="link_4")],
        [InlineKeyboardButton("5", callback_data="link_5")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("Choose a number between 1 and 5 to get private group links:", reply_markup=reply_markup)

async def show_link(update: Update, context: CallbackContext) -> None:
    """Shows the link(s) based on the button clicked."""
    query = update.callback_query
    choice = query.data  # link_1, link_2, etc.
    
    # Fetch all private group links from MongoDB
    group_links = private_groups_collection.find()

    # Convert the cursor to a list to randomly select a link
    group_links_list = list(group_links)

    if len(group_links_list) > 0:
        if choice in ["link_1", "link_2", "link_3", "link_4", "link_5"]:
            number = int(choice.split("_")[1]) - 1
            if number < len(group_links_list):
                # Send multiple links if the user clicks 2, 3, etc.
                links_to_send = group_links_list[:number + 1]  # Slice the list based on the user's choice
                links_message = "\n".join([link['link'] for link in links_to_send])
                await query.edit_message_text(f"Here are your private group links:\n{links_message}")
            else:
                await query.edit_message_text("No more links available for this choice.")
        else:
            await query.edit_message_text("Invalid choice. Please try again.")
    else:
        await query.edit_message_text("No private group links available yet. Please try again later.")

async def help_command(update: Update, context: CallbackContext) -> None:
    """Shows available commands to the user."""
    keyboard = [
        [InlineKeyboardButton("🧑‍💻 User", callback_data="user_commands")],
        [InlineKeyboardButton("👨‍💻 Admin", callback_data="admin_commands")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose your role:", reply_markup=reply_markup)

async def user_commands(update: Update, context: CallbackContext) -> None:
    """Shows user-related commands."""
    user_commands_text = (
        "User Commands:\n"
        "/getpvt - Get private group links\n"
        "/stats - View bot stats\n"
        "/help - Show this help message"
    )
    await update.callback_query.edit_message_text(user_commands_text)

async def admin_commands(update: Update, context: CallbackContext) -> None:
    """Prompt for the admin password."""
    await update.callback_query.edit_message_text("Please enter the admin password:")

    # Set the state for password verification
    context.user_data['is_admin'] = True

async def verify_admin_password(update: Update, context: CallbackContext) -> None:
    """Verify if the password entered is correct."""
    entered_password = update.message.text.strip()

    if entered_password == ADMIN_PASSWORD:
        # Password is correct, show admin commands
        admin_commands_text = (
            "Admin Commands:\n"
            "/addgc - Add private group link\n"
            "/getpvt - Get private group links\n"
            "/stats - View bot stats\n"
            "/help - Show this help message"
        )
        await update.message.reply_text(admin_commands_text)
    else:
        await update.message.reply_text("Incorrect password. Please start the bot again.")

async def stats(update: Update, context: CallbackContext) -> None:
    """Shows bot stats like the number of users and private groups."""
    total_users = users_collection.count_documents({})
    total_getpvt = private_groups_collection.count_documents({})
    stats_text = f"Total Users: {total_users}\nTotal Private Group Links: {total_getpvt}"
    await update.message.reply_text(stats_text)

def main():
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addgc", addgc))  # Command to add a private group link
    application.add_handler(CommandHandler("getpvt", getpvt))  # Command to get private group links
    application.add_handler(CommandHandler("help", help_command))  # Command for showing help
    application.add_handler(CommandHandler("stats", stats))  # Command to view bot stats
    application.add_handler(CallbackQueryHandler(show_link))  # Handle link selection in getpvt command
    application.add_handler(CallbackQueryHandler(user_commands, pattern="user_commands"))  # User command callback
    application.add_handler(CallbackQueryHandler(admin_commands, pattern="admin_commands"))  # Admin command callback
    application.add_handler(MessageHandler(Filters.text & ~Filters.command, verify_admin_password))  # Handle password entry

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
