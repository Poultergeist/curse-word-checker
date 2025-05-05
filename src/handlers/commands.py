from telegram import Update, BotCommand, BotCommandScopeChat
from telegram.ext import CallbackContext
from src.database import db
from src.utils.logger import log_message
from src.config.settings import DEFAULT_TEMPLATE

async def check_message(update: Update, context: CallbackContext) -> None:
    """Check message for banned words"""
    if not update.message or not update.message.text:
        return

    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    message_id = update.message.message_id
    text = update.message.text.lower()
    
    # Log message
    message_data = {
        "chat_id": chat_id,
        "user_id": user_id,
        "message_id": message_id,
        "text": text,
        "timestamp": update.message.date.isoformat()
    }
    log_message(message_data)
    db.add_message(message_data)
    
    # Check for banned words
    banned_words = db.get_banned_words(chat_id)
    for word in banned_words:
        if word in text:
            template = db.get_message_template(chat_id) or DEFAULT_TEMPLATE
            warning = template.format(
                name=update.message.from_user.first_name,
                word=word
            )
            await update.message.reply_text(warning)
            
            if db.delete_messages_check(chat_id):
                await update.message.delete()
            break

async def ban_word(update: Update, context: CallbackContext) -> None:
    """Ban word in chat"""
    if not context.args:
        await update.message.reply_text("Please provide a word to ban")
        return
        
    if not db.check_if_moderator(update.message.chat_id, update.message.from_user.id):
        await update.message.reply_text("You are not a moderator")
        return
        
    word = " ".join(context.args)
    db.add_banned_word(
        word,
        update.message.chat_id,
        update.message.from_user.id,
        update.message.chat.title
    )
    await update.message.reply_text(f"Word '{word}' has been banned")

async def remove_word(update: Update, context: CallbackContext) -> None:
    """Remove banned word"""
    if not context.args:
        await update.message.reply_text("Please provide a word to remove")
        return
        
    if not db.check_if_moderator(update.message.chat_id, update.message.from_user.id):
        await update.message.reply_text("You are not a moderator")
        return
        
    word = " ".join(context.args)
    db.remove_banned_word(word, update.message.chat_id)
    await update.message.reply_text(f"Word '{word}' has been removed from ban list")

async def show_banned_words(update: Update, context: CallbackContext) -> None:
    """Show list of banned words"""
    words = db.get_banned_words(update.message.chat_id)
    if not words:
        await update.message.reply_text("No banned words in this chat")
        return
        
    message = "Banned words:\n" + "\n".join(f"- {word}" for word in words)
    await update.message.reply_text(message)

async def add_moderator(update: Update, context: CallbackContext) -> None:
    """Add new moderator"""
    if not update.message.reply_to_message:
        await update.message.reply_text("Please reply to a message of the user you want to make moderator")
        return
        
    if not db.check_if_moderator(update.message.chat_id, update.message.from_user.id):
        await update.message.reply_text("You are not a moderator")
        return
        
    user = update.message.reply_to_message.from_user
    status = db.new_moderator(user.id, user.username, update.message.chat_id)
    
    if status == "super_admin":
        await update.message.reply_text("This user is a super admin")
    elif status == "already_moderator":
        await update.message.reply_text("This user is already a moderator")
    else:
        await update.message.reply_text(f"User {user.first_name} is now a moderator")

async def remove_moderator(update: Update, context: CallbackContext) -> None:
    """Remove moderator"""
    if not update.message.reply_to_message:
        await update.message.reply_text("Please reply to a message of the moderator you want to remove")
        return
        
    if not db.check_if_moderator(update.message.chat_id, update.message.from_user.id):
        await update.message.reply_text("You are not a moderator")
        return
        
    user = update.message.reply_to_message.from_user
    status = db.delete_moderator(user.id, update.message.chat_id)
    
    if status == "super_admin":
        await update.message.reply_text("Cannot remove super admin")
    else:
        await update.message.reply_text(f"User {user.first_name} is no longer a moderator")

async def show_moderators(update: Update, context: CallbackContext) -> None:
    """Show list of moderators"""
    moderators = db.list_moderators(update.message.chat_id)
    if not moderators:
        await update.message.reply_text("No moderators in this chat")
        return
        
    message = "Moderators:\n" + "\n".join(f"- {m[1] or f'User {m[0]}'}" for m in moderators)
    await update.message.reply_text(message)

async def clear_words(update: Update, context: CallbackContext) -> None:
    """Clear all banned words"""
    if not db.check_if_moderator(update.message.chat_id, update.message.from_user.id):
        await update.message.reply_text("You are not a moderator")
        return
        
    db.clear_words_by_chat(update.message.chat_id)
    await update.message.reply_text("All banned words have been cleared")

async def show_messages(update: Update, context: CallbackContext) -> None:
    """Show recent messages"""
    if not db.check_if_moderator(update.message.chat_id, update.message.from_user.id):
        await update.message.reply_text("You are not a moderator")
        return
        
    timestamp = context.args[0] if context.args else None
    messages = db.show_messages_by_chat(update.message.chat_id, timestamp)
    
    if not messages:
        await update.message.reply_text("No messages found")
        return
        
    message = "Recent messages:\n" + "\n".join(
        f"- {m[4]}: {m[3]}" for m in messages[-10:]  # Show last 10 messages
    )
    await update.message.reply_text(message)

async def delete_messages(update: Update, context: CallbackContext) -> None:
    """Toggle message deletion"""
    if not db.check_if_moderator(update.message.chat_id, update.message.from_user.id):
        await update.message.reply_text("You are not a moderator")
        return
        
    if not context.args:
        current = db.delete_messages_check(update.message.chat_id)
        await update.message.reply_text(f"Message deletion is {'enabled' if current else 'disabled'}")
        return
        
    value = context.args[0].lower()
    if value not in ['on', 'off']:
        await update.message.reply_text("Please use 'on' or 'off'")
        return
        
    db.delete_messages_change(update.message.chat_id, value == 'on')
    await update.message.reply_text(f"Message deletion has been turned {value}")

async def add_template(update: Update, context: CallbackContext) -> None:
    """Add message template"""
    if not db.check_if_moderator(update.message.chat_id, update.message.from_user.id):
        await update.message.reply_text("You are not a moderator")
        return
        
    if not context.args:
        await update.message.reply_text("Please provide a template text")
        return
        
    template = " ".join(context.args)
    if '{name}' not in template or '{word}' not in template:
        await update.message.reply_text("Template must contain {name} and {word}")
        return
        
    db.add_message_template(update.message.chat_id, template)
    await update.message.reply_text("Template has been added")

async def remove_template(update: Update, context: CallbackContext) -> None:
    """Remove message template"""
    if not db.check_if_moderator(update.message.chat_id, update.message.from_user.id):
        await update.message.reply_text("You are not a moderator")
        return
        
    if not context.args:
        await update.message.reply_text("Please provide template ID")
        return
        
    try:
        template_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Please provide a valid template ID")
        return
        
    db.remove_message_template(update.message.chat_id, template_id)
    await update.message.reply_text("Template has been removed")

async def list_templates(update: Update, context: CallbackContext) -> None:
    """Show message templates"""
    if not db.check_if_moderator(update.message.chat_id, update.message.from_user.id):
        await update.message.reply_text("You are not a moderator")
        return
        
    templates = db.list_message_templates(update.message.chat_id)
    if not templates:
        await update.message.reply_text("No templates found")
        return
        
    message = "Message templates:\n" + "\n".join(
        f"- ID: {t[0]}, Active: {t[2]}\n  {t[1]}" for t in templates
    )
    await update.message.reply_text(message)

async def on_bot_added(update: Update, context: CallbackContext) -> None:
    """Handle bot being added to chat"""
    if not update.message or not update.message.new_chat_members:
        return
        
    bot = context.bot
    for member in update.message.new_chat_members:
        if member.id == bot.id:
            # Set commands for this chat
            commands = [
                BotCommand("ban", "Ban a word"),
                BotCommand("unban", "Remove banned word"),
                BotCommand("list", "Show banned words"),
                BotCommand("addmod", "Add moderator"),
                BotCommand("delmod", "Remove moderator"),
                BotCommand("mods", "Show moderators"),
                BotCommand("clear", "Clear all banned words"),
                BotCommand("messages", "Show recent messages"),
                BotCommand("delete", "Toggle message deletion"),
                BotCommand("template", "Add message template"),
                BotCommand("deltemplate", "Remove message template"),
                BotCommand("templates", "Show message templates"),
                BotCommand("help", "Show help")
            ]
            await bot.set_my_commands(
                commands,
                scope=BotCommandScopeChat(chat_id=update.message.chat_id)
            )
            await update.message.reply_text(
                "Hello! I'm a curse word bot. Use /help to see available commands."
            )
            break

async def help_command(update: Update, context: CallbackContext) -> None:
    """Show help message"""
    if not context.args:
        # Show general help
        help_text = (
            "Available commands:\n"
            "/ban <word> - Ban a word\n"
            "/unban <word> - Remove banned word\n"
            "/list - Show banned words\n"
            "/addmod - Add moderator (reply to user)\n"
            "/delmod - Remove moderator (reply to user)\n"
            "/mods - Show moderators\n"
            "/clear - Clear all banned words\n"
            "/messages [timestamp] - Show recent messages\n"
            "/delete [on|off] - Toggle message deletion\n"
            "/template <text> - Add message template\n"
            "/deltemplate <id> - Remove message template\n"
            "/templates - Show message templates\n"
            "/help [command] - Show help for specific command"
        )
        await update.message.reply_text(help_text)
    else:
        # Show help for specific command
        command = context.args[0].lstrip('/')
        help_text = get_command_help(command)
        if help_text:
            await update.message.reply_text(help_text)
        else:
            await update.message.reply_text(f"No help available for command {command}")

def get_command_help(command: str) -> str:
    """Get help text for specific command"""
    help_texts = {
        "ban": "Ban a word in the chat\nUsage: /ban <word>",
        "unban": "Remove a word from ban list\nUsage: /unban <word>",
        "list": "Show all banned words in the chat",
        "addmod": "Add a new moderator\nUsage: Reply to user's message with /addmod",
        "delmod": "Remove a moderator\nUsage: Reply to user's message with /delmod",
        "mods": "Show all moderators in the chat",
        "clear": "Remove all banned words from the chat",
        "messages": "Show recent messages\nUsage: /messages [timestamp]",
        "delete": "Toggle automatic message deletion\nUsage: /delete [on|off]",
        "template": "Add a new message template\nUsage: /template <text>\nTemplate must contain {name} and {word}",
        "deltemplate": "Remove a message template\nUsage: /deltemplate <id>",
        "templates": "Show all message templates",
        "help": "Show this help message\nUsage: /help [command]"
    }
    return help_texts.get(command, "") 