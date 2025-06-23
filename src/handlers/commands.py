from telegram import Update, BotCommand, BotCommandScopeChat
from telegram.ext import CallbackContext, ContextTypes
from database import db
from utils.logger import log_message, log_system_event
from config.settings import DEFAULT_TEMPLATE
import re
from datetime import datetime
from utils import args as global_args

async def check_message(update: Update, context: CallbackContext) -> None:
    """
    Check messages for banned words
    
    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """
    try:
        args = global_args.parse_args()
        RAT_MODE = args.rat

        if not update.message or not update.message.text:
            return

        message_data = {
            'message_id': update.message.message_id,
            'chat_id': update.effective_chat.id,
            'user_id': update.effective_user.id,
            'username': update.effective_user.username,
            'message_text': update.message.text,
            'date': update.message.date.isoformat(),
            'rat': RAT_MODE
        }
        
        if RAT_MODE:
            await log_message(message_data)
            log_system_event(
                'message_received_rat',
                message_data
            )

        # Check message for banned words
        chat_id = update.effective_chat.id
        banned_words = db.get_banned_words(chat_id)
        bad_words = []
        
        message = re.sub(r"[^\w\s']", ' ', update.message.text)
        
        # Split message text into words for whole-word matching
        message_words = set(message.lower().split())
        
        # Check each banned word against the message
        for word in banned_words:
            if word.lower() in message_words:
                bad_words.append(word)
                
        if bad_words:
            template = db.get_message_template(chat_id) or DEFAULT_TEMPLATE
            
            # Preparation of parameters for formatting
            format_params = {}
            if '{name}' in template:
                format_params['name'] = update.message.from_user.first_name
            if '{word}' in template:
                format_params['word'] = ', '.join(bad_words)
            
            # Formatting the template with available parameters
            warning = template.format(**format_params)
            await update.message.reply_text(warning)
            message_data['is_banned'] = True
            message_data['banned_words'] = bad_words
            await log_message(message_data)
            
            log_system_event(
                'message_received',
                message_data
            )
            
            if db.delete_messages_check(chat_id):
                await update.message.delete()

    except Exception as e:
        log_system_event(
            'message_check_error',
            {
                'error': str(e),
                'message_id': update.message.message_id,
                'chat_id': update.effective_chat.id
            },
            'ERROR'
        )
        await update.message.reply_text("An error occurred while executing the command.")

async def word_command(update: Update, context: CallbackContext) -> None:
    """
    Handle word-related commands
    
    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """
    if not context.args:
        await update.message.reply_text("Please specify action: ban, unban, list, or clear")
        return

    action = context.args[0].lower()
    if action not in ['ban', 'unban', 'list', 'clear']:
        await update.message.reply_text("Invalid action. Use: ban, unban, list, or clear")
        return
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if action == 'list':
        words = db.get_banned_words(chat_id)
        
        if not words:
            await update.message.reply_text("No banned words in this chat")
            return
        
        await update.message.reply_text("Banned words:\n" + "\n".join(f"- {word}" for word in words))
        return

    if not db.check_if_moderator(chat_id, update.message.from_user.id):
        await update.message.reply_text("You are not a moderator")
        
        log_system_event(
            'access_denied',
            {
                'command': 'word',
                'action': action,
                'user_id': update.effective_user.id,
                'username': update.effective_user.username,
            },
            "WARNING"
        )
        
        return

    if action == 'clear':
        db.clear_words_by_chat(chat_id)
        await update.message.reply_text("All banned words have been cleared")
        return

    if len(context.args) < 2:
        await update.message.reply_text(f"Please provide a word to {action}")
        return

    words = context.args[1:]
    chat_name = update.effective_chat.title or str(chat_id)
    
    if words.__len__() == 0:
        await update.message.reply_text(f"Please provide a word to {action}")
        log_system_event(
            'command_error',
            {
                'command': action,
                'error': "No words provided",
                'user_id': user_id,
                'chat_id': chat_id
            }
        )
        return
    
    
    word_list = db.get_banned_words(chat_id)
    banned = [w for w in words if w.lower() in word_list]
    not_banned = [w for w in words if w.lower() not in word_list]


    if action == 'ban':
        try:
            # Log command execution
            log_system_event(
                'command_executed',
                {
                    'command': 'ban',
                    'user_id': user_id,
                    'chat_id': chat_id
                }
            )

            # Split input into individual words and add each to the banned list
            if banned == words:
                # If all words are already banned, reply with a message
                await update.message.reply_text(
                    f"Words '{', '.join(words)}' are already banned."
                )
                return
            for word in not_banned:
                db.add_banned_word(word, chat_id, user_id, chat_name)
                
            # Reply with confirmation message
            await update.message.reply_text(
                f"Words '{', '.join([w for w in words if w.lower() not in banned])}' have been added to the banned list."
                + (banned and f" Already banned: {', '.join(banned)}" if banned else "")
            )
            
        except Exception as e:
            log_system_event(
                'command_error',
                {
                    'command': 'ban',
                    'error': str(e),
                    'user_id': user_id,
                    'chat_id': chat_id
                },
                'ERROR'
            )
            await update.message.reply_text("An error occurred while executing the command.") 
    
    if action == 'unban':
        try:
            # Log command execution
            log_system_event(
                'command_executed',
                {
                    'command': 'unban',
                    'user_id': user_id,
                    'chat_id': chat_id
                }
            )
            
            # Split input into individual words and remove each from the banned list
            if not_banned == words:
                # If all words are not banned, reply with a message
                await update.message.reply_text(
                    f"Words '{', '.join(words)}' are not banned."
                )
                return
            for word in banned:
                db.remove_banned_word(word, update.message.chat_id)
            # Reply with confirmation message
            await update.message.reply_text(
                f"Words '{', '.join([w for w in words if w.lower() not in not_banned])}' have been removed from the banned list."
                + (not_banned and f" Already was unbanned: {', '.join(not_banned)}" if not_banned else "")
            )
        except Exception as e:
            log_system_event(
                'command_error',
                {
                    'command': 'unban',
                    'error': str(e),
                    'user_id': update.effective_user.id,
                    'chat_id': update.effective_chat.id
                },
                'ERROR'
            )
            await update.message.reply_text("An error occurred while executing the command.")

async def mod_command(update: Update, context: CallbackContext) -> None:
    """
    Handle moderator-related commands
    
    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """
    if not context.args:
        await update.message.reply_text("Please specify action: add, delete, or list")
        return

    action = context.args[0].lower()
    if action not in ['add', 'delete', 'list']:
        await update.message.reply_text("Invalid action. Use: add, delete, or list")
        return
        
    if not db.check_if_moderator(update.message.chat_id, update.message.from_user.id):
        await update.message.reply_text("You are not a moderator")
        log_system_event(
            'access_denied',
            {
                'command': 'mod',
                'action': action,
                'user_id': update.effective_user.id,
                'username': update.effective_user.username,
            },
            "WARNING"
        )
        return
        
    if action == 'list':
        moderators = db.list_moderators(update.message.chat_id)
        if not moderators:
            await update.message.reply_text("No moderators in this chat")
            return
        
        await update.message.reply_text("Moderators:\n" + "\n".join(f"- {m[1] or f'User {m[0]}'}" for m in moderators))
        return

    # Handle add/delete with reply to message
    if action in ['add', 'delete'] and update.message.reply_to_message:
        replied_user = update.message.reply_to_message.from_user
        user_id = replied_user.id
        username = replied_user.username
        
        if action == 'add':
            status = db.new_moderator(user_id, username, update.message.chat_id)
            if status == "super_admin":
                await update.message.reply_text("This user is a super admin")
            elif status == "already_moderator":
                await update.message.reply_text("This user is already a moderator")
            else:
                await update.message.reply_text(f"User {username or user_id} is now a moderator")
        else:  # delete
            status = db.delete_moderator(user_id, update.message.chat_id)
            if status == "super_admin":
                await update.message.reply_text("Cannot remove super admin")
            else:
                await update.message.reply_text(f"User {username or user_id} is no longer a moderator")
        return
    
    if action in ['add', 'delete'] and not update.message.reply_to_message:
        await update.message.reply_text("Please reply to the user you want to add/delete as a moderator")
        return

async def template_command(update: Update, context: CallbackContext) -> None:
    """
    Handle template-related commands
    
    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """
    if not context.args:
        await update.message.reply_text("Please specify action: add, delete, or list")
        return

    action = context.args[0].lower()
    if action not in ['add', 'delete', 'list']:
        await update.message.reply_text("Invalid action. Use: add, delete, or list")
        return

    if not db.check_if_moderator(update.message.chat_id, update.message.from_user.id):
        await update.message.reply_text("You are not a moderator")
        return

    if action == 'list':
        try:
            # Log command execution
            log_system_event(
                'command_executed',
                {
                    'command': 'list',
                    'user_id': update.effective_user.id,
                    'chat_id': update.effective_chat.id
                }
            )
            templates = db.list_message_templates(update.message.chat_id)
            if not templates:
                await update.message.reply_text("There are no message templates in this chat")
                return
            message = "Message templates:\n" + "\n".join(
                f"- ID: {t[0]},\n\tTemplate: {t[1]}" for t in templates
            )
            await update.message.reply_text(message)
            return
        except Exception as e:
            log_system_event(
                'command_error',
                {
                    'command': 'list',
                    'error': str(e),
                    'user_id': update.effective_user.id,
                    'chat_id': update.effective_chat.id
                },
                'ERROR'
            )
            await update.message.reply_text("An error occurred while executing the command.")
            return

    if action == 'add':
        try:
            # Log command execution
            log_system_event(
                'command_executed',
                {
                    'command': 'add',
                    'user_id': update.effective_user.id,
                    'chat_id': update.effective_chat.id
                }
            )
            if len(context.args) < 2:
                await update.message.reply_text("Please provide template text")
                return
            # Ensure template is a single string
            template = " ".join(context.args[1:]).strip()
            db.add_message_template(update.message.chat_id, template)
            
            # Update template IDs to be sequential
            db.reorder_template_ids(update.message.chat_id)
            
            await update.message.reply_text("Template has been added")
            return
        except Exception as e:
            log_system_event(
                'command_error',
                {
                    'command': 'add',
                    'error': str(e),
                    'user_id': update.effective_user.id,
                }
            )
            await update.message.reply_text("An error occurred while adding the template.")
            return
        
    if action == 'delete' or action == 'remove':  # delete
        if len(context.args) < 2:
            await update.message.reply_text("Please provide template ID")
            return
        try:
            # Log command execution
            log_system_event(
                'command_executed',
                {
                    'command': 'delete',
                    'user_id': update.effective_user.id,
                    'chat_id': update.effective_chat.id
                }
            )
            # Ensure template ID is an integer
            template_id = int(context.args[1])
            db.remove_message_template(update.message.chat_id, template_id)
            
            # Update template IDs to be sequential
            db.reorder_template_ids(update.message.chat_id)
            
            await update.message.reply_text("Template has been removed")
        except ValueError:
            log_system_event(
                'command_error',
                {
                    'command': 'delete',
                    'error': "Invalid template ID",
                    'user_id': update.effective_user.id,
                }
            )
            await update.message.reply_text("Please provide a valid template ID")
        except Exception as e:
            log_system_event(
                'command_error',
                {
                    'command': 'delete',
                    'error': str(e),
                    'user_id': update.effective_user.id,
                }
            )
            await update.message.reply_text("An error occurred while deleting the template.")
        return
    await update.message.reply_text("Invalid action. Use: add, delete, or list")
    return

async def messages_command(update: Update, context: CallbackContext) -> None:
    """
    Show recent messages
    
    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """
    if not db.check_if_moderator(update.message.chat_id, update.message.from_user.id):
        await update.message.reply_text("You are not a moderator")
        return
        
    timestamp = context.args[0] if context.args else None
    messages = db.show_messages_by_chat(update.message.chat_id, timestamp)
    
    if not messages:
        await update.message.reply_text("No messages found")
        return
        
    message = "Recent messages:\n" + "\n".join(
        f"- @{m[1]}: {m[2]}" for m in messages[-10:]  # Show last 10 messages
    )
    await update.message.reply_text(message)

async def delete_command(update: Update, context: CallbackContext) -> None:
    """
    Toggle message deletion
    
    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """
    if not db.check_if_moderator(update.message.chat_id, update.message.from_user.id):
        await update.message.reply_text("You are not a moderator")
        return
        
    # Show current status
    if not context.args:
        current = db.delete_messages_check(update.message.chat_id)
        await update.message.reply_text(f"Message deletion is {'enabled' if current else 'disabled'}")
        return
        
    # Check if argument is 'on' or 'off'
    value = context.args[0].lower()
    if value not in ['on', 'off']:
        await update.message.reply_text("Please use 'on' or 'off'")
        return
        
    # Update deletion setting in database
    db.delete_messages_change(update.message.chat_id, value == 'on')
    await update.message.reply_text(f"Message deletion has been turned {value}")

async def statistics_command(update: Update, context: CallbackContext) -> None:
    """
    Show statistics for today or a given date
    
    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """
    
    # Empty flag to check if statistics are available
    empty = True

    # Parse date argument if provided
    if context.args:
        try:
            date = datetime.strptime(context.args[0], "%d-%m-%y").date()
        except Exception:
            await update.message.reply_text("Please provide date in format dd-mm-yy")
            return
    else:
        date = datetime.now().date()

    stats = db.get_statistics(update.message.chat_id, date)
    msg = f"📊 Statistics for {date.strftime('%d-%m-%Y')}:\n\n"
    
    if stats['user_stats']:
        empty = False
        msg += "👤 Top users (by banned words used):\n"
        for i, (username, count) in enumerate(stats['user_stats'], 1):
            msg += f"{i}. @{username or 'unknown'} — {count}\n"
    msg += "\n"
    
    if stats['word_stats']:
        empty = False
        msg += "🚫 Top banned words used:\n"
        for i, (word, count) in enumerate(stats['word_stats'], 1):
            msg += f"{i}. {word} — {count}\n"
    msg += "\n"
    
    if stats['most_banned_message']:
        empty = False
        msg += f"📝 Most banned message:\n{stats['most_banned_message'][0]}\n"
    
    if empty:
        msg = "⛔️ No statistics available for this date. ⛔️"
    
    await update.message.reply_text(msg)

async def on_bot_added(update: Update, context: CallbackContext) -> None:
    """
    Handle bot being added to chat
    
    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """
    if not update.message or not update.message.new_chat_members:
        await update.message.reply_text("No new chat members")
        return

    bot = context.bot
    for member in update.message.new_chat_members:
        if member.id == bot.id:
            # Set commands for this chat
            commands = [
                BotCommand("word", "Manage banned words (ban/unban/list)"),
                BotCommand("mod", "Manage moderators (add/delete/list)"),
                BotCommand("template", "Manage message templates (add/delete/list)"),
                BotCommand("clear", "Clear all banned words"),
                BotCommand("messages", "Show recent messages"),
                BotCommand("delete", "Toggle message deletion"),
                BotCommand("help", "Show help")
            ]
            await bot.set_my_commands(
                commands,
                scope=BotCommandScopeChat(chat_id=update.message.chat_id)
            )
            await update.message.reply_text(
                "Hello! I'm a curse word bot. Use /help to see available commands."
            )
            
            # Ensure chat exists in the database
            db.ensure_chat_exists(update.message.chat_id, update.message.chat.title)
            if not db.has_moderators(update.message.chat_id):
                db.new_moderator(update.message.from_user.id, update.message.from_user.username, update.message.chat_id)
            
            # Log bot added event
            log_system_event(
                'bot_added',
                {
                    'chat_id': update.message.chat_id,
                    'chat_title': update.message.chat.title,
                    'user_id': update.message.from_user.id
                }
            )
            break

async def on_bot_removed(update: Update, context: CallbackContext) -> None:
    """
    Handle bot being removed from chat
    
    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """
    chat = update.effective_chat
    db.delete_chat_and_moderators(chat.id)
    log_system_event(
        'bot_removed',
        {
            'chat_id': chat.id,
            'chat_title': getattr(chat, 'title', None)
        }
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    """
    Show help message
    
    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """
    if not context.args:
        # Show general help
        help_text = (
            "Available commands:\n\n"
            "Word management:\n"
            "/word ban <word> - Ban a word\n"
            "/word unban <word> - Remove banned word\n"
            "/word list - Show banned words\n\n"
            "Moderator management:\n"
            "**reply to user** /mod add - Add moderator\n"
            "**reply to user** /mod delete - Remove moderator\n"
            "/mod list - Show moderators\n\n"
            "Template management:\n"
            "/template add <text> - Add message template\n"
            "/template delete <id> - Remove template\n"
            "/template list - Show templates\n\n"
            "Other commands:\n"
            "/messages (optional)[timestamp] - Show recent messages\n"
            "/delete [on|off] - Toggle message deletion\n\n"
            "Use /help <command> for detailed help about specific command\n"
            "Example: /help word ban"
        )
        await update.message.reply_text(help_text)
    else:
        # Show help for specific command
        command = context.args[0].lower()
        subcommand = context.args[1].lower() if len(context.args) > 1 else None
        help_text = get_command_help(command, subcommand)
        if help_text:
            await update.message.reply_text(help_text)
        else:
            await update.message.reply_text(f"No help available for command {command}")

def get_command_help(command: str, subcommand: str = None) -> str:
    """
    Get help text for specific command
    
    Args:
        command (str): Command name
        subcommand (str, optional): Subcommand name, defaults to None

    Returns:
        str: Help text for the command or subcommand
    """
    help_texts = {
        "word": {
            None: "Word management commands\nUsage:\n/word ban <words> - Ban a word\n/word unban <words> - Remove banned word\n/word list - Show banned words\n/word clear - Clear all banned words",
            "ban": "Ban a word in the chat\nUsage: /word ban <words>\nExamples:\n - /word ban badword\n - /word ban badword1 badword2",
            "unban": "Remove a word from ban list\nUsage: /word unban <words>\nExamples:\n - /word unban badword\n - /word unban badword1 badword2",
            "list": "Show all banned words in the chat\nUsage: /word list",
            "clear": "Remove all banned words from the chat\nUsage: /word clear"
        },
        "mod": {
            None: "Moderator management commands\nUsage:\n**reply to user** /mod add - Add moderator\n**reply to user** /mod delete - Remove moderator\n/mod list - Show moderators",
            "add": "Add a new moderator\nUsage: **reply to user** /mod add\nExample: **reply to user** /mod add",
            "delete": "Remove a moderator\nUsage: **reply to user** /mod delete\nExample: **reply to user** /mod delete",
            "list": "Show all moderators in the chat\nUsage: /mod list"
        },
        "template": {
            None: "Template management commands\nUsage:\n/template add <text> - Add template\n/template delete <id> - Remove template\n/template list - Show templates",
            "add": "Add a new message template\nUsage: /template add <text>\nOptional placeholders: {name} for user name, {word} for banned word\nExamples:\n - /template add Hey {name}!\n - /template add Don't use {word}!\n - /template add Hey {name}, don't use {word}!\n - /template add This word is not allowed!",
            "delete": "Remove a message template\nUsage: /template delete <id>\nExample: /template delete 1",
            "list": "Show all message templates\nUsage: /template list"
        },
        "messages": "Show recent messages\nUsage: /messages (optional)[timestamp]\nExample: /messages 2024-03-20",
        "delete": "Toggle automatic message deletion\nUsage: /delete [on|off]\nExample: /delete on",
        "statistics": "Show statistics for today or a given date\nUsage: /statistics (optional)[dd-mm-yy]\nExample: /statistics 20-03-24",
        "help": {
            None: "Show help message\nUsage: /help [command]\nExample: /help word ban",
            "help": "Realy?"
            }
    }
    
    if command in help_texts:
        if isinstance(help_texts[command], dict):
            return help_texts[command].get(subcommand, help_texts[command][None])
        return help_texts[command]
    return ""
