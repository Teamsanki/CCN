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
requests_collection = db['requests']  # To store user requests

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
        [InlineKeyboardButton("Sᴜᴘᴘᴏʀᴛ", url=OWNER_SUPPORT_CHANNEL)],
        [InlineKeyboardButton("Oᴡɴᴇʀ", url=f"tg://user?id={OWNER_TELEGRAM_ID}")],
        [InlineKeyboardButton("Hᴇʟᴘ", callback_data="help")]
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
        "2. /getpvt - Get random private group links\n"
        "3. /req <message> <link> - Send a request with your message and link to the owner\n\n"
    )

    keyboard = [
        [InlineKeyboardButton("🛠 Contact Support", url=OWNER_SUPPORT_CHANNEL)],
        [InlineKeyboardButton("💬 Message Owner", url=f"tg://user?id={OWNER_TELEGRAM_ID}")],
        [InlineKeyboardButton("Back", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send help message with commands and inline keyboard
    await update.message.reply_text(help_text, reply_markup=reply_markup)

    # If the user clicks "Back," return to the previous state or main options
    if update.callback_query and update.callback_query.data == "back":
        await update.callback_query.answer()
        # You can add logic to return to the initial bot options or menu here.

async def req(update: Update, context: CallbackContext) -> None:
    """User command to send a request message with their link to the owner."""
    user_id = update.message.from_user.id
    if len(context.args) < 2:
        await update.message.reply_text("Please provide a message and a link. Usage: /req <message> <link>")
        return

    user_message = context.args[0]
    user_link = context.args[1]

    # Save the request to MongoDB
    requests_collection.insert_one({"user_id": user_id, "message": user_message, "link": user_link})
    
    await update.message.reply_text(f"Your request has been sent to the owner. Message: {user_message}, Link: {user_link}")

async def for_command(update: Update, context: CallbackContext) -> None:
    """Owner-only command to forward a user's message to the specified user."""
    if update.message.from_user.id != int(OWNER_TELEGRAM_ID):
        await update.message.reply_text("This command is restricted to the owner only.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Please provide the user ID and the message to forward. Usage: /for <user_id> <message>")
        return

    user_id = int(context.args[0])
    owner_message = " ".join(context.args[1:])

    try:
        await context.bot.send_message(user_id, owner_message)
        await update.message.reply_text(f"Message successfully forwarded to user {user_id}.")
    except Exception as e:
        await update.message.reply_text(f"Error forwarding message: {e}")

async def getpvt(update: Update, context: CallbackContext) -> None:
    """Fetches random private group links."""
    group_links = private_groups_collection.find()
    group_links_list = list(group_links)

    if len(group_links_list) > 0:
        random_links = random.sample(group_links_list, 10)
        keyboard = [
            [
                InlineKeyboardButton(f"Gᴄ𝟷", url=random_links[0]['link']),
                InlineKeyboardButton(f"Gᴄ𝟸", url=random_links[1]['link']),
                InlineKeyboardButton(f"Gᴄ𝟹", url=random_links[2]['link']),
                InlineKeyboardButton(f"Gᴄ𝟺", url=random_links[3]['link']),
                InlineKeyboardButton(f"Gᴄ𝟻", url=random_links[4]['link'])
            ],
            [
                InlineKeyboardButton(f"Gᴄ𝟼", url=random_links[5]['link']),
                InlineKeyboardButton(f"Gᴄ𝟽", url=random_links[6]['link']),
                InlineKeyboardButton(f"Gᴄ𝟾", url=random_links[7]['link']),
                InlineKeyboardButton(f"Gᴄ𝟿", url=random_links[8]['link']),
                InlineKeyboardButton(f"Gᴇᴛ", url=random_links[9]['link'])
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Tʜɪs ɪs Tʜᴇ 𝟷𝟶 ʀᴀɴᴅᴏᴍ  ɢʀᴏᴜᴘ ʟɪɴᴋs\n\nNᴏᴛᴇ ᴀғᴛᴇʀ 𝟷𝟶 sᴇᴄ ᴛʜᴇɴ ᴜsᴇʀ /getpvt ᴄᴏᴍᴍᴀɴᴅ\n\nBᴇᴄᴀᴜsᴇ ᴏғ Tᴇᴀᴍ Sᴀɴᴋɪ ᴘᴏʟɪᴄʏ", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Nᴏ ᴘʀɪᴠᴀᴛᴇ ɢʀᴏᴜᴘ ʟɪɴᴋs ᴀᴠᴀɪʟᴀʙʟᴇ ʏᴇᴛ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ")

async def broadcast(update: Update, context: CallbackContext) -> None:
    """Owner-only command to send a broadcast message to all users."""
    if update.message.from_user.id != int(OWNER_TELEGRAM_ID):
        await update.message.reply_text("This command is restricted to the owner only.")
        return

    # Check if the message contains the text to broadcast
    if not context.args:
        await update.message.reply_text("Please provide the message to broadcast.")
        return

    message = " ".join(context.args)

    # Send broadcast message to all users
    all_users = users_collection.find()
    for user in all_users:
        try:
            await context.bot.send_message(user['user_id'], message)
        except Exception as e:
            logger.error(f"Error sending message to {user['user_id']}: {e}")

    await update.message.reply_text("Broadcast message sent to all users.")

async def stats(update: Update, context: CallbackContext) -> None:
    """Owner-only command to view bot statistics."""
    if update.message.from_user.id != int(OWNER_TELEGRAM_ID):
        await update.message.reply_text("This command is restricted to the owner only.")
        return

    # Get user count from MongoDB
    user_count = users_collection.count_documents({})

    # Get the number of requests in the database
    request_count = requests_collection.count_documents({})

    # Get the number of private groups in the database
    group_count = private_groups_collection.count_documents({})

    # Get uptime of the bot
    uptime = get_uptime()

    # Prepare the statistics message
    stats_message = (
        "*Bot Statistics:*\n\n"
        f"◈ Total number of users: {user_count}\n"
        f"◈ Total number of requests: {request_count}\n"
        f"◈ Total number of private groups: {group_count}\n"
        f"◈ Uptime: {uptime}\n\n"
        "*Keep up the great work! 🚀*"
    )

    # Send the statistics message
    await update.message.reply_text(stats_message)
# Main function to run the bot
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Register the command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("req", req))
    application.add_handler(CommandHandler("getpvt", getpvt))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("for", for_command))
    application.add_handler(CommandHandler("stats", stats))

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()
