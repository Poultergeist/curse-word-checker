from telegram.ext import Application, MessageHandler, filters, CommandHandler
from src.config.settings import TELEGRAM_BOT_API
from src.handlers.commands import (
    check_message, ban_word, remove_word, show_banned_words,
    add_moderator, remove_moderator, show_moderators, clear_words,
    show_messages, delete_messages, add_template, remove_template,
    list_templates, on_bot_added, help_command
)

def main() -> None:
    """Start the bot"""
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_API).build()

    # Add handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_message))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_bot_added))
    
    # Command handlers
    application.add_handler(CommandHandler("ban", ban_word))
    application.add_handler(CommandHandler("unban", remove_word))
    application.add_handler(CommandHandler("list", show_banned_words))
    application.add_handler(CommandHandler("addmod", add_moderator))
    application.add_handler(CommandHandler("delmod", remove_moderator))
    application.add_handler(CommandHandler("mods", show_moderators))
    application.add_handler(CommandHandler("clear", clear_words))
    application.add_handler(CommandHandler("messages", show_messages))
    application.add_handler(CommandHandler("delete", delete_messages))
    application.add_handler(CommandHandler("template", add_template))
    application.add_handler(CommandHandler("deltemplate", remove_template))
    application.add_handler(CommandHandler("templates", list_templates))
    application.add_handler(CommandHandler("help", help_command))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main() 