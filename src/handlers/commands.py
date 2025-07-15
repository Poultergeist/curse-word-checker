import base64
import json
from anyio import sleep
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, BotCommand, BotCommandScopeChat
from telegram.ext import CallbackContext, ContextTypes
from database import db
from utils.logger import log_message, log_system_event
from config.settings import DEFAULT_TEMPLATE
import re
from datetime import datetime
from utils import args as global_args
from languages.language_core import get_locales, reinitialize_locales, list_locales, get_locales_list
from functools import wraps

locales = get_locales()

def command_middleware(func):
    log_system_event(
        'command_middleware',
        {
            'command': func.__name__,
            'message': 'Command middleware initialized'
        }
    )
    @wraps(func)
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        chat = update.effective_chat
        user = update.effective_user

        if chat.id > 0:
            chat_title = user.username or user.first_name
        else:
            chat_title = chat.title or f"Chat {chat.id}"

        chat_created = not db.ensure_chat_exists(chat.id, chat_title)
        result = await func(update, context, *args, **kwargs)

        if chat_created:
            await on_bot_added(update, context)
            if not db.check_if_moderator(chat.id, user.id) is 0:
                db.new_moderator(user.id, user.username, chat.id)

        return result
    return wrapper

@command_middleware
async def check_message(update: Update, context: CallbackContext) -> None:
    """
    Check messages for banned words
    
    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """
    try:
        if not update.message or not update.message.text:
            return

        message_data = {
            'message_id': update.message.message_id,
            'chat_id': update.effective_chat.id,
            'user_id': update.effective_user.id,
            'username': update.effective_user.username,
            'message_text': update.message.text,
            'date': update.message.date.isoformat()
        }

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

@command_middleware
async def word_command(update: Update, context: CallbackContext) -> None:
    """
    Handle word-related commands
    
    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """
    
    current_locale = db.get_locale(update.effective_chat.id)
    
    if not context.args:
        await update.message.reply_text(locales[current_locale]['word']['no_args'])
        return

    action = context.args[0].lower()
    if action not in ['ban', 'unban', 'list', 'clear']:
        await update.message.reply_text(locales[current_locale]['word']['invalid_action'])
        return
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if action == 'list':
        words = db.get_banned_words(chat_id)
        
        if not words:
            await update.message.reply_text(locales[current_locale]['word']['list_empty'])
            return
        
        await update.message.reply_text(f"{locales[current_locale]['word']['list_header']}" + "\n".join(f"- {word}" for word in words))
        return

    if chat_id < 0:
        # Create inline keyboard with button to start private chat
        payload = {"chat_id": chat_id, "command": "word", "action": action, "params": context.args[1:]}
        encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
        keyboard = [[InlineKeyboardButton("Continue in Private Chat", url=f"https://t.me/{context.bot.username}?start=settings__{chat_id} command__word")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"From now chat settings can be changed only in *private* chat with me.\n\n payload: \n```\n{payload}```\n\nEncoded payload:\n```{encoded}```", reply_markup=reply_markup, parse_mode='Markdown')
        return

    if db.check_if_moderator(chat_id, update.message.from_user.id) is False:
        await update.message.reply_text(locales[current_locale]['no_access'])
        
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
        await update.message.reply_text(locales[current_locale]['word']['cleared'])
        return

    if len(context.args) < 2:
        await update.message.reply_text(locales[db.get_locale(chat_id)]['word']['too_short'].format(action=action))
        return

    words = context.args[1:]
    chat_name = update.effective_chat.title or str(chat_id)
    
    if len(words) == 0:
        await update.message.reply_text(locales[current_locale]['word']['too_short'].format(action=action))
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
                    locales[current_locale]['word']['ban_banned'].format(words=', '.join(words))
                )
                return
            for word in not_banned:
                db.add_banned_word(word, chat_id, user_id, chat_name)
                
            # Reply with confirmation message
            await update.message.reply_text(
                locales[current_locale]['word']['banned_success'].format(words=', '.join([w for w in words if w.lower() not in banned]))
                + (banned and " " + locales[current_locale]['word']['banned_success'].format(words=', '.join(banned)) if banned else "")
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
            await update.message.reply_text(locales[current_locale]['error']) 
    
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
                    locales[current_locale]['word']['unban_not_banned'].format(words=', '.join(words))
                )
                return
            for word in banned:
                db.remove_banned_word(word, update.message.chat_id)
            # Reply with confirmation message
            await update.message.reply_text(
                locales[current_locale]['word']['unbanned_success'].format(words=', '.join([w for w in words if w.lower() not in not_banned]))
                + (not_banned and ' ' + locales[current_locale]['word']['already_unbanned'].format(words=', '.join(not_banned)) if not_banned else "")
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
            await update.message.reply_text(locales[current_locale]['error'])

@command_middleware
async def mod_command(update: Update, context: CallbackContext) -> None:
    """
    Handle moderator-related commands
    
    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """
    
    current_locale = db.get_locale(update.effective_chat.id)
    
    if not context.args:
        await update.message.reply_text(locales[current_locale]['mod']['no_args'])
        return

    action = context.args[0].lower()
    if action not in ['add', 'delete', 'list']:
        await update.message.reply_text(locales[current_locale]['mod']['invalid_action'])
        return
        
    if db.check_if_moderator(update.message.chat_id, update.message.from_user.id) is False:
        await update.message.reply_text(locales[current_locale]['no_access'])
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
            await update.message.reply_text(locales[current_locale]['mod']['list_empty'])
            return
        
        await update.message.reply_text(locales[current_locale]['mod']['list_header'] + "\n".join(f"- {m[1] or f'User {m[0]}'}" for m in moderators))
        return

    # Handle add/delete with reply to message
    if action in ['add', 'delete'] and update.message.reply_to_message:
        replied_user = update.message.reply_to_message.from_user
        user_id = replied_user.id
        username = replied_user.username
        
        if action == 'add':
            status = db.new_moderator(user_id, username, update.message.chat_id)
            if status == "super_admin":
                await update.message.reply_text(locales[current_locale]['mod']['add_superadmin'])
            elif status == "already_moderator":
                await update.message.reply_text(locales[current_locale]['mod']['add_already'])
            else:
                await update.message.reply_text(locales[current_locale]['mod']['add_success'].format(user=username or user_id))
        else:  # delete
            status = db.delete_moderator(user_id, update.message.chat_id)
            if status == "super_admin":
                await update.message.reply_text(locales[current_locale]['mod']['delete_superadmin'])
            else:
                await update.message.reply_text(locales[current_locale]['mod']['delete_success'].format(user=username or user_id))
        return
    else:
        await update.message.reply_text(locales[current_locale]['mod']['reply'])
        return
    
@command_middleware
async def template_command(update: Update, context: CallbackContext) -> None:
    """
    Handle template-related commands
    
    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """
    
    current_locale = db.get_locale(update.effective_chat.id)
    
    if not context.args:
        await update.message.reply_text(locales[current_locale]['template']['no_args'])
        return

    action = context.args[0].lower()
    if action not in ['add', 'delete', 'list', 'remove']:
        await update.message.reply_text(locales[current_locale]['template']['invalid_action'])
        return

    if db.check_if_moderator(update.message.chat_id, update.message.from_user.id) is False:
        await update.message.reply_text(locales[current_locale]['no_access'])
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
                await update.message.reply_text(locales[current_locale]['template']['list_empty'])
                return
            message = locales[current_locale]['template']['list_header'] + "\n".join(
                locales[current_locale]['template']['list_item'].format(template_id=t[0], template=t[1]) for t in templates
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
            await update.message.reply_text(locales[current_locale]['error'])
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
                await update.message.reply_text(locales[current_locale]['template']['add_no_text'])
                return
            # Ensure template is a single string
            template = " ".join(context.args[1:]).strip()
            db.add_message_template(update.message.chat_id, template)
            
            # Update template IDs to be sequential
            db.reorder_template_ids(update.message.chat_id)
            
            await update.message.reply_text(locales[current_locale]['template']['add_success'])
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
            await update.message.reply_text(locales[current_locale]['error'])
            return
        
    if action == 'delete' or action == 'remove':  # delete
        if len(context.args) < 2:
            await update.message.reply_text(locales[current_locale]['template']['remove_no_id'])
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
            
            await update.message.reply_text(locales[current_locale]['template']['remove_success'])
        except ValueError:
            log_system_event(
                'command_error',
                {
                    'command': 'delete',
                    'error': "Invalid template ID",
                    'user_id': update.effective_user.id,
                }
            )
            await update.message.reply_text(locales[current_locale]['template']['remove_value_error'])
        except Exception as e:
            log_system_event(
                'command_error',
                {
                    'command': 'template_delete',
                    'error': str(e),
                    'user_id': update.effective_user.id,
                }
            )
            await update.message.reply_text(locales[current_locale]['error'])
        return
    await update.message.reply_text(locales[current_locale]['template']['invalid_action'])
    return

@command_middleware
async def messages_command(update: Update, context: CallbackContext) -> None:
    """
    Show recent messages
    
    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """
    
    current_locale = db.get_locale(update.effective_chat.id)
    
    if db.check_if_moderator(update.message.chat_id, update.message.from_user.id) is False:
        await update.message.reply_text(locales[current_locale]['no_access'])
        return
        
    timestamp = context.args[0] if context.args else None
    messages = db.show_messages_by_chat(update.message.chat_id, timestamp)
    
    if not messages:
        await update.message.reply_text(locales[current_locale]['messages']['recent_empty'])
        return
        
    message = locales[current_locale]['messages']['recent'] + "\n".join(
        locales[current_locale]['messages']['recent_item'].format(user=m[1], message=m[2]) for m in messages[-10:]  # Show last 10 messages
    )
    await update.message.reply_text(message)

@command_middleware
async def delete_command(update: Update, context: CallbackContext) -> None:
    """
    Toggle message deletion
    
    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """
    
    current_locale = db.get_locale(update.effective_chat.id)
    
    if db.check_if_moderator(update.message.chat_id, update.message.from_user.id) is False:
        await update.message.reply_text(locales[current_locale]['no_access'])
        return
        
    # Show current status
    if not context.args:
        current = db.delete_messages_check(update.message.chat_id)
        await update.message.reply_text(locales[current_locale]['delete']['show'].format(status='enabled' if current else 'disabled'))
        return
        
    # Check if argument is 'on' or 'off'
    value = context.args[0].lower()
    if value not in ['on', 'off']:
        await update.message.reply_text(locales[current_locale]['delete']['invalid_action'])
        return
        
    # Update deletion setting in database
    db.delete_messages_change(update.message.chat_id, value == 'on')
    await update.message.reply_text(locales[current_locale]['delete']['switch'].format(value=value))

@command_middleware
async def locale_command(update: Update, context: CallbackContext) -> None:
    """
    Handle locale-related commands

    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """
    
    current_locale = db.get_locale(update.effective_chat.id)
    
    if not context.args:
        await update.message.reply_text(locales[current_locale]['locale']['no_args'])
        return

    action = context.args[0].lower()
    if action not in ['list', 'current', 'set']:
        await update.message.reply_text(locales[current_locale]['locale']['invalid_action'])
        return
    
    if db.check_if_moderator(update.message.chat_id, update.message.from_user.id) is False:
        await update.message.reply_text(locales[current_locale]['no_access'])
        log_system_event(
            'access_denied',
            {
                'command': 'locale',
                'action': action,
                'user_id': update.effective_user.id,
                'username': update.effective_user.username,
            },
            "WARNING"
        )
        return
    
    if action == 'list':
        _locales = get_locales_list()
        if not _locales:
            await update.message.reply_text(locales[current_locale]['locale']['list_empty'])
            return
        await update.message.reply_text(locales[current_locale]['locale']['list'] + "\n".join(_locales))
        return

    if action == 'current':
        locale = db.get_locale(update.message.chat_id)
        if not locale:
            await update.message.reply_text(locales[current_locale]['locale']['current_empty'])
            return
        await update.message.reply_text(locales[current_locale]['locale']['current'].format(locale=locale))
        return

    if action == 'set':
        if len(context.args) < 2:
            await update.message.reply_text(locales[current_locale]['locale']['set_no_locale'])
            return
        locale = " ".join(context.args[1:]).lower()
        if db.set_locale(update.message.chat_id, locale):
            await update.message.reply_text(locales[current_locale]['locale']['set'].format(locale=locale))
        else:
            await update.message.reply_text(locales[current_locale]['locale']['set_invalid_locale'].format(locale=locale))
            log_system_event(
                'locale_set_error',
                {
                    'chat_id': update.message.chat_id,
                    'locale': locale,
                    'user_id': update.effective_user.id
                },
                'ERROR'
            )

@command_middleware
async def reinitialize_locales_command(update: Update, context: CallbackContext) -> None:
    """
    Reinitialize locales from files

    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """

    global locales
    current_locale = db.get_locale(update.effective_chat.id)

    if not db.check_if_moderator(update.message.chat_id, update.message.from_user.id) is 0:
        await update.message.reply_text(locales[current_locale]['no_access'])

        log_system_event(
            'access_denied',
            {
                'command': 'reinitialize_locales',
                'user_id': update.effective_user.id,
                'username': update.effective_user.username,
            },
            "WARNING"
        )

        return

    try:
        locales = reinitialize_locales()
        await update.message.reply_text("Locales have been reinitialized successfully")
    except Exception as e:
        log_system_event(
            'locales_reinitialization_error',
            {'error': str(e)},
            'ERROR'
        )
        await update.message.reply_text(locales[current_locale]['error'])

@command_middleware        
async def all_locales_command(update: Update, context: CallbackContext) -> None:
    """
    Show all available locales
    
    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """
    
    current_locale = db.get_locale(update.effective_chat.id)
    
    if not db.check_if_moderator(update.message.chat_id, update.message.from_user.id) is 0:
        await update.message.reply_text(locales[current_locale]['no_access'])
        return
    
    locales = list_locales()
    if not locales:
        await update.message.reply_text("No available locales found")
        return
    
    await update.message.reply_text("Available locales:\n" + "\n".join(locales))

@command_middleware
async def statistics_command(update: Update, context: CallbackContext) -> None:
    """
    Show statistics for today or a given date
    
    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """
    
    current_locale = db.get_locale(update.effective_chat.id)
    
    # Empty flag to check if statistics are available
    empty = True

    # Parse date argument if provided
    if context.args and context.args[0].lower() == 'full':
        # If 'full' is specified, show statistics for all time
        date = None
    elif context.args:
        try:
            date = datetime.strptime(context.args[0], "%d-%m-%y").date()
        except Exception:
            await update.message.reply_text(locales[current_locale]['statistics']['format'])
            return
    else:
        date = datetime.now().date()

    if date:
        stats = db.get_statistics(update.message.chat_id, date)
    else:
        stats = db.get_statistics_full(update.message.chat_id)
    msg = locales[current_locale]['statistics']['header'].format(date=(date.strftime("%d-%m-%Y") if date else "all time"))
    
    if stats['user_stats']:
        empty = False
        msg += locales[current_locale]['statistics']['users_header']
        for i, (username, count) in enumerate(stats['user_stats'], 1):
            msg += locales[current_locale]['statistics']['users_item'].format(
                id=i,
                user=username or f"User {count[0]}",
                count=count
            )
    msg += "\n"
    
    if stats['word_stats']:
        empty = False
        msg += locales[current_locale]['statistics']['words_header']
        for i, (word, count) in enumerate(stats['word_stats'], 1):
            msg += locales[current_locale]['statistics']['words_item'].format(
                id=i,
                word=word,
                count=count
            )
    msg += "\n"
    
    if stats['most_banned_message']:
        empty = False
        msg += locales[current_locale]['statistics']['most_banned'].format(
            message=stats['most_banned_message'][0]
        )
    
    if empty:
        msg = locales[current_locale]['statistics']['empty']
    
    await update.message.reply_text(msg)

async def on_bot_added(update: Update, context: CallbackContext) -> None:
    """
    Handle bot being added to chat
    
    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """
    
    current_locale = db.get_locale(update.effective_chat.id)
    
    if not update.message or not update.message.new_chat_members:
        await update.message.reply_text(locales[current_locale]['bot_add']['no_new'])
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
                locales[current_locale]['bot_add']['added']
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

@command_middleware
async def help_command(update: Update, context: CallbackContext) -> None:
    """
    Show help message
    
    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """
    
    current_locale = db.get_locale(update.effective_chat.id)
    help_short = locales[current_locale]['help']['help_short']
    locale_help = locales[current_locale]['help']['help_texts']
    
    if not context.args:
        # Show general help
        help_text = (
            f"{help_short['header']}\n\n"
            f"{help_short['word_header']}\n"
            f"/word ban <word> - {help_short['word_ban']}\n"
            f"/word unban <word> - {help_short['word_unban']}\n"
            f"/word list - {help_short['word_list']}\n"
            f"/word clear - {help_short['word_clear']}\n\n"
            f"{help_short['mod_header']}\n"
            f"**reply to user** /mod add - {help_short['mod_add']}\n"
            f"**reply to user** /mod delete - {help_short['mod_delete']}\n"
            f"/mod list - {help_short['mod_list']}\n\n"
            f"{help_short['template_header']}\n"
            f"/template add <text> - {help_short['template_add']}\n"
            f"/template delete <id> - {help_short['template_delete']}\n"
            f"/template list - {help_short['template_list']}\n\n"
            f"{help_short['locale_header']}\n"
            f"/locale list - {help_short['locale_list']}\n"
            f"/locale current - {help_short['locale_current']}\n"
            f"/locale set <locale> - {help_short['locale_set']}\n\n"
            f"{help_short['other_header']}\n"
            f"/messages (optional)[timestamp] - {help_short['other_messages']}\n"
            f"/delete [on|off] - {help_short['other_delete']}\n"
            f"/statistics (optional)[dd-mm-yy] - {help_short['other_statistics']}\n\n"
            f"{help_short['other_help']}"
        )
        await update.message.reply_text(help_text)
    else:
        # Show help for specific command
        command = context.args[0].lower()
        subcommand = context.args[1].lower() if len(context.args) > 1 else None
        help_text = get_command_help(command, locale_help, subcommand)
        if help_text:
            await update.message.reply_text(help_text)
        else:
            await update.message.reply_text(help_short['error'].format(command=command))

def get_command_help(command: str, locale_help: list, subcommand: str = None) -> str:
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
            None: locale_help['word']['none'].format(
                help_template='\n/word ban <words> - Ban a word\n/word unban <words> - Remove banned word\n/word list - Show banned words\n/word clear - Clear all banned words'
            ),
            "ban": locale_help['word']['ban'].format(
                help_template='/word ban <words> - Ban a word',
                help_ex='- /word ban badword\n- /word ban badword1 badword2'
            ),
            "unban": locale_help['word']['unban'].format(
                help_template='/word unban <words> - Remove banned word',
                help_ex='- /word unban badword\n- /word unban badword1 badword2'
            ),
            "list": locale_help['word']['list'].format(
                help_template='/word list - Show banned words'
            ),
            "clear": locale_help['word']['clear'].format(
                help_template='/word clear - Clear all banned words'
            )
        },
        "mod": {
            None: locale_help['mod']['none'].format(
                help_template='\n**reply to user** /mod add - Add moderator\n**reply to user** /mod delete - Remove moderator\n/mod list - Show moderators'
            ),
            "add": locale_help['mod']['add'].format(
                help_template='**reply to user** /mod add - Add moderator',
                help_ex='**reply to user** /mod add'
            ),
            "delete": locale_help['mod']['delete'].format(
                help_template='**reply to user** /mod delete - Remove moderator',
                help_ex='**reply to user** /mod delete'
            ),
            "list": locale_help['mod']['list'].format(
                help_template='/mod list - Show moderators'
            )
        },
        "template": {
            None: locale_help['template']['none'].format(
                help_template='\n/template add <text> - Add template\n/template delete <id> - Remove template\n/template list - Show templates'
            ),
            "add": locale_help['template']['add'].format(
                help_template='/template add <text> - Add template',
                help_ex='- /template add Hey {name}!\n- /template add Don\'t use {word}!\n- /template add Hey {name}, don\'t use {word}!\n- /template add This word is not allowed!'
            ),
            "delete": locale_help['template']['delete'].format(
                help_template='/template delete <id> - Remove template',
                help_ex='/template delete 1'
            ),
            "list": locale_help['template']['list'].format(
                help_template='/template list - Show templates'
            )
        },
        "locale": {
            None: locale_help['locale']['none'].format(
                help_template='\n/locale list - Show available locales\n/locale current - Show current locale\n/locale set <locale> - Set locale for the chat'
            ),
            "list": locale_help['locale']['list'].format(
                help_template='/locale list - Show available locales'
            ),
            "current": locale_help['locale']['current'].format(
                help_template='/locale current - Show current locale'
            ),
            "set": locale_help['locale']['set'].format(
                help_template='/locale set <locale> - Set locale for the chat',
                help_ex='/locale set en'
            )
        },
        "help": {
            None: locale_help['help']['none'].format(
                help_template='/help [command] - Show help for command',
                help_ex='/help word ban'
            ),
            "help": locale_help['help']['help']
        },
        "messages": locale_help['messages'].format(
            help_template='/messages (optional)[timestamp] - Show recent messages',
            help_ex='/messages 2024-03-20'
        ),
        "delete": locale_help['delete'].format(
            help_template='/delete [on|off] - Toggle automatic message deletion',
            help_ex='/delete on'
        ),
        "statistics": locale_help['statistics'].format(
            help_template='/statistics (optional)[dd-mm-yy] - Show statistics for today or a given date',
            help_ex='/statistics 20-03-24'
        )
    }
    
    if command in help_texts:
        if isinstance(help_texts[command], dict):
            return help_texts[command].get(subcommand, help_texts[command][None])
        return help_texts[command]
    return ""

@command_middleware
async def start_command(update: Update, context: CallbackContext) -> None:
    """
    Handle /start command
    
    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """
    
    # Extract start parameter from URL (if user clicked a button with URL)
    start_param = None
    if context.args:
        start_param = context.args[0]
        
    # Properly escape curly braces and backslashes for MarkdownV2
    args_text = str(context.args).replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('-', '\\-').replace('_', '\\_').replace('*', '\\*').replace('`', '\\`')
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"context\\.args:\n```\n{args_text}\n```",
        parse_mode='MarkdownV2'
    )
    
    if start_param:
        start_params = start_param.split('___')
    
    start_message = await update.message.reply_text(
        "Welcome! You can configure bot settings here. Use /help to see available commands."
    )
    
    # Handle different start parameters
    for start_param in start_params:
        if start_param.startswith("settings_"):
            affected_chat_id = start_param.split("__")[1]
            start_message = await start_message.edit_text(
                text=f"{start_message.text}\n\nSettings for chat {affected_chat_id} have been configured. You can now manage this chat's settings."
            )
        elif start_param.startswith("command_"):
            command_name = start_param.split("__")[1]
            start_message = await start_message.edit_text(
                text=f"{start_message.text}\n\nYou can now use the /{command_name} command to manage this chat's settings."
            )
        elif start_param.startswith("action_"): 
            action = start_param.split("__")[1]
            start_message = await start_message.edit_text(
                text=f"{start_message.text}\n\nYou can now perform the {action} action in this chat."
            )
        elif start_param.startswith("args_"):
            args = (start_param.split("__")[1]).split('_')
            start_message = await start_message.edit_text(
                text=f"{start_message.text}\n\nYou can now use the following arguments: {', '.join(args)}."
            )
        elif start_param == "hello":
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Hello! You came from the private chat button. How can I help you with bot settings?"
            )
            

@command_middleware
async def handle_callback(update: Update, context: CallbackContext) -> None:
    """
    Handle callback queries
    
    Args:
        update (Update): Incoming update from Telegram
        context (CallbackContext): Context for the callback
    """
    log_system_event(
        'callback_query',
        {
            'query_id': update.callback_query.id,
            'data': update.callback_query.data,
            'user_id': update.effective_user.id,
            'chat_id': update.effective_chat.id
        }
    )
    
    # Extract callback data
    callback_data = update.callback_query.data
    
    # Handle different callback data
    if callback_data == "start_private_chat":
        await update.callback_query.edit_message_text(
            text="Great! Now you can configure bot settings in this private chat. Use /help to see available commands."
        )
    else:
        # Handle other callback data
        await update.callback_query.answer(
            text="Unknown action",
            show_alert=False
        )
        
    # Always answer the callback query to remove loading state
    await update.callback_query.answer()