import argparse
import os
import logging
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from handlers.commands import (
    check_message,
    word_command,
    mod_command,
    template_command,
    messages_command,
    delete_command,
    on_bot_added,
    help_command
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_API')).build()

    # Add handlers
    application.add_handler(CommandHandler("word", word_command))
    application.add_handler(CommandHandler("mod", mod_command))
    application.add_handler(CommandHandler("template", template_command))
    application.add_handler(CommandHandler("messages", messages_command))
    application.add_handler(CommandHandler("delete", delete_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Handle new chat members (for bot being added to chat)
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_bot_added))
    
    # Handle regular messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_message))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main() 