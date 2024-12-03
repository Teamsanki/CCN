import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler
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
stats_collection = db['stats']

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
        [InlineKeyboardButton("📋 Help", callback_data="help_commands")]
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

# Command to handle help button
async def handle_help(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("User Commands", callback_data="user_commands")],
        [InlineKeyboardButton("Admin Commands", callback_data="admin_commands")]
    ]
    await query.edit_message_text("Choose an option:", reply_markup=InlineKeyboardMarkup(keyboard))

# Command to handle user commands
async def handle_user_commands(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_commands_text = (
        "User Commands:\n"
        "/start - Start the bot\n"
        "/getpvt - Get a random private group link\n"
        "/help - Show this help message\n"
        "/stats - Show total users and getpvt usage stats"
    )
    await query.edit_message_text(user_commands_text)

# Admin command to handle admin authentication and commands
async def handle_admin_commands(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    if context.user_data.get("admin_verified"):
        admin_commands_text = (
            "Admin Commands:\n"
            "/broadcast - Send a broadcast message to all users\n"
            "/getpvt - Get a random private group link\n"
            "/stats - Show total users and getpvt usage stats"
        )
        await query.edit_message_text(admin_commands_text)
    else:
        await query.edit_message_text("Please enter the admin password:")

# Admin password verification
async def verify_admin_password(update: Update, context: CallbackContext) -> None:
    password = update.message.text
    if password == "SKCC11256#":
        context.user_data["admin_verified"] = True
        await update.message.reply_text("Password verified! You can now access admin commands.")
    else:
        await update.message.reply_text("Incorrect password. Please try again.")

# Handle the broadcast command for admins
async def handle_broadcast(update: Update, context: CallbackContext) -> None:
    if not context.user_data.get("admin_verified"):
        await update.message.reply_text("You are not authorized to perform this action.")
        return

    # Get message text for broadcast
    broadcast_message = " ".join(context.args)
    if not broadcast_message:
        await update.message.reply_text("Please provide a message to broadcast.")
        return

    # Send the broadcast message to all users
    users = users_collection.find()
    for user in users:
        try:
            await context.bot.send_message(chat_id=user["user_id"], text=broadcast_message)
        except Exception as e:
            logger.error(f"Failed to send message to {user['user_id']}: {e}")

# Fetch private group links for the getpvt command
async def getpvt(update: Update, context: CallbackContext) -> None:
    """Fetches random private group link(s) based on user selection."""
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("1 Link", callback_data="getpvt_1")],
        [InlineKeyboardButton("2 Links", callback_data="getpvt_2")],
        [InlineKeyboardButton("3 Links", callback_data="getpvt_3")],
        [InlineKeyboardButton("4 Links", callback_data="getpvt_4")],
        [InlineKeyboardButton("5 Links", callback_data="getpvt_5")]
    ]
    await query.edit_message_text("Choose how many private links you want:", reply_markup=InlineKeyboardMarkup(keyboard))

# Handle user selection for the number of private links to retrieve
async def handle_getpvt_selection(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    selection = query.data.split("_")[1]
    
    # Fetch all private group links from MongoDB
    group_links = private_groups_collection.find()
    group_links_list = list(group_links)
    
    # Number of links to send
    num_links = int(selection)
    links_to_send = random.sample(group_links_list, num_links)
    
    # Send the links to the user
    links_message = "\n".join([link['link'] for link in links_to_send])
    await query.edit_message_text(f"Here are {num_links} random private group link(s):\n\n{links_message}")

# Stats command for users
async def stats(update: Update, context: CallbackContext) -> None:
    """Displays statistics for the bot usage."""
    total_users = users_collection.count_documents({})
    total_getpvt_usage = stats_collection.count_documents({"command": "getpvt"})
    
    stats_message = (
        f"Total Users: {total_users}\n"
        f"Total getpvt Usage: {total_getpvt_usage}"
    )
    await update.message.reply_text(stats_message)

def main():
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", handle_help))
    application.add_handler(CommandHandler("stats", stats))

    # Add callback query handlers
    application.add_handler(CallbackQueryHandler(handle_help, pattern="help_commands"))
    application.add_handler(CallbackQueryHandler(handle_user_commands, pattern="user_commands"))
    application.add_handler(CallbackQueryHandler(handle_admin_commands, pattern="admin_commands"))
    application.add_handler(CallbackQueryHandler(handle_getpvt_selection, pattern="getpvt_"))

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()
