import os
import json
import mysql.connector
from datetime import datetime
from telegram import Update, BotCommand, BotCommandScopeChat
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackContext
from dotenv import load_dotenv
import re

# Loading environment variables
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
TELEGRAM_BOT_API = os.getenv("TELEGRAM_BOT_API")
LOG_DIR = os.getenv("LOG_DIR", "logs")  # Default logs directory
LOG_FILE = os.getenv("LOG_FILE", "message_log.json")  # Default log filename
LOG_MAX_SIZE = int(os.getenv("LOG_MAX_SIZE", "10485760"))  # Default 10MB in bytes
DEFAULT_TEMPLATE = os.getenv("DEFAULT_TEMPLATE", "Hey, {name}, this word `{word}` is banned!")

# Function to execute database queries
def execute_db_query(query: str, params=None, fetch: bool = False):
    """
    Execute database query with automatic connection management
    
    Args:
        query (str): SQL query to execute
        params: Parameters for the query (will be converted to tuple if single value)
        fetch (bool): Whether to fetch and return results
        
    Returns:
        list or None: Query results if fetch=True, None otherwise
        
    Raises:
        Exception: If database operation fails
    """
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = conn.cursor()
        
        if params is not None:
            # Convert single parameter to tuple
            if not isinstance(params, (tuple, list)):
                params = (params,)
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        if fetch:
            result = cursor.fetchall()
        else:
            conn.commit()
            result = None
            
        return result
    except Exception as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
        raise e
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Message logging function
def log_message(message_data: dict, log_dir=LOG_DIR, log_file=LOG_FILE):
    """
    Log message data to JSON file with automatic rotation
    
    Args:
        message_data (dict): Message data to log
        log_dir (str): Directory for log files
        log_file (str): Name of the log file
        
    The function will:
    1. Create log directory if it doesn't exist
    2. Rotate log file if it exceeds LOG_MAX_SIZE
    3. Append message to existing log file or create new one
    4. Add message to database
    """
    try:
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        log_path = os.path.join(log_dir, log_file)
        if os.path.exists(log_path) and os.path.getsize(log_path) > LOG_MAX_SIZE:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_log_path = os.path.join(log_dir, f"message_log.{timestamp}.json")
            os.rename(log_path, new_log_path)
        
        if os.path.exists(log_path):
            with open(log_path, 'r+') as file:
                try:
                    file_data = json.load(file)
                except json.JSONDecodeError:
                    file_data = {"messages": []}
                file_data["messages"].append(message_data)
                file.seek(0)
                json.dump(file_data, file, indent=4)
        else:
            with open(log_path, 'w') as file:
                json.dump({"messages": [message_data]}, file, indent=4)
        add_message(message_data)
    except Exception as e:
        print(f"Error logging message: {e}")

# Check if user is a moderator
def check_if_moderator(chat_id: int, user_id: int):
    """
    Check if user is a moderator in the specified chat
    
    Args:
        chat_id (int): Chat ID to check
        user_id (int): User ID to check
        
    Returns:
        bool: True if user is moderator, False otherwise
    """
    result = execute_db_query(
        "SELECT chat_id FROM user_is_moderator WHERE user_id = %s",
        user_id,
        fetch=True
    )
    return result is not None and (result[0][0] == chat_id or result[0][0] == 0)

# Function to add chat to DB if it doesn't exist
def ensure_chat_exists(chat_id: int, chat_name: str):
    """
    Ensure chat exists in database, create if it doesn't
    
    Args:
        chat_id (int): Chat ID
        chat_name (str): Chat name/title
    """
    execute_db_query(
        "INSERT IGNORE INTO chats (id, name) VALUES (%s, %s)",
        (chat_id, chat_name)
    )

# Function to add banned word to DB
def add_banned_word(word: str, chat_id: int, user_id: int, chat_name: str):
    """
    Add word to banned words list for chat
    
    Args:
        word (str): Word to ban
        chat_id (int): Chat ID
        user_id (int): User ID who banned the word
        chat_name (str): Chat name/title
    """
    ensure_chat_exists(chat_id, chat_name)
    execute_db_query(
        "INSERT INTO words (word, chat_id, who_banned) VALUES (%s, %s, %s)",
        (word.lower(), chat_id, user_id)
    )

# Function to remove banned word
def remove_banned_word(word: str, chat_id: int):
    """
    Remove word from banned words list for chat
    
    Args:
        word (str): Word to remove from ban list
        chat_id (int): Chat ID
    """
    execute_db_query(
        "DELETE FROM words WHERE word = %s AND chat_id = %s",
        (word.lower(), chat_id)
    )

# Function to get list of banned words in chat
def get_banned_words(chat_id: int):
    """
    Get list of banned words for chat
    
    Args:
        chat_id (int): Chat ID
        
    Returns:
        list: List of banned words
    """
    result = execute_db_query(
        "SELECT word FROM words WHERE chat_id = %s",
        chat_id,
        fetch=True
    )
    return [row[0] for row in result]

# Function to add new moderator
def new_moderator(user_id: int, username: str, chat_id: int) -> str:
    """
    Add new moderator to chat
    
    Args:
        user_id (int): User ID to make moderator
        username (str): Username of the user
        chat_id (int): Chat ID
        
    Returns:
        str: Status of operation ("super_admin", "already_moderator", or "added")
    """
    result = execute_db_query(
        "SELECT chat_id FROM user_is_moderator WHERE user_id = %s",
        user_id,
        fetch=True
    )
    if result and result[0][0] == 0:
        return "super_admin"
    elif result and result[0][0] == chat_id:
        return "already_moderator"
    
    execute_db_query(
        "INSERT IGNORE INTO users (id, username) VALUES (%s, %s)",
        (user_id, username)
    )
    execute_db_query(
        "INSERT INTO user_is_moderator (user_id, chat_id) VALUES (%s, %s)",
        (user_id, chat_id)
    )
    return "added"

# Function to remove moderator
def delete_moderator(user_id: int, chat_id: int) -> str:
    """
    Remove moderator from chat
    
    Args:
        user_id (int): User ID to remove as moderator
        chat_id (int): Chat ID
        
    Returns:
        str: Status of operation ("super_admin" or "removed")
    """
    result = execute_db_query(
        "SELECT chat_id FROM user_is_moderator WHERE user_id = %s",
        user_id,
        fetch=True
    )
    if result and result[0][0] == 0:
        return "super_admin"
    
    execute_db_query(
        "DELETE FROM user_is_moderator WHERE user_id = %s AND chat_id = %s",
        (user_id, chat_id)
    )
    return "removed"
    
# Function to list all moderators
def list_moderators(chat_id: int):
    """
    Get list of moderators for chat
    
    Args:
        chat_id (int): Chat ID
        
    Returns:
        list: List of moderator usernames
    """
    result = execute_db_query("""
        SELECT u.username 
        FROM user_is_moderator um
        JOIN users u ON um.user_id = u.id
        WHERE um.chat_id = %s OR um.chat_id = 0
    """, chat_id, fetch=True)
    return [row[0] for row in result]

# Function to clear all banned words in chat
def clear_words_by_chat(chat_id: int):
    """
    Remove all banned words from chat
    
    Args:
        chat_id (int): Chat ID
    """
    execute_db_query(
        "DELETE FROM words WHERE chat_id = %s",
        chat_id
    )
    
# Function to change message deletion setting
def delete_messages_change(chat_id: int, delete: bool):
    """
    Change message deletion setting for chat
    
    Args:
        chat_id (int): Chat ID
        delete (bool): Whether to delete messages with banned words
    """
    execute_db_query(
        "UPDATE chats SET delete_messages = %s WHERE id = %s",
        (delete, chat_id)
    )
    
# Function to check if messages should be deleted
def delete_messages_check(chat_id: int) -> bool:
    """
    Check if messages should be deleted in chat
    
    Args:
        chat_id (int): Chat ID
        
    Returns:
        bool: True if messages should be deleted, False otherwise
    """
    result = execute_db_query(
        "SELECT delete_messages FROM chats WHERE id = %s",
        chat_id,
        fetch=True
    )
    return result[0][0]
    
# Function to add message to logs
def add_message(message_data: dict):
    """
    Add message to database logs
    
    Args:
        message_data (dict): Message data containing:
            - user_id: ID of message sender
            - username: Username of sender
            - message_text: Text content of message
            - chat_id: Chat ID
            - message_id: Message ID
            - timestamp: Message timestamp
    """
    execute_db_query("""
        INSERT INTO logs (user_id, username, message_text, chat_id, message_id, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        message_data["user_id"],
        message_data["username"],
        message_data["message_text"],
        message_data["chat_id"],
        message_data["message_id"],
        message_data["timestamp"]
    ))

# Function to show messages by chat
def show_messages_by_chat(chat_id: int, timestamp: str = None):
    """
    Get messages from chat
    
    Args:
        chat_id (int): Chat ID
        timestamp (str, optional): Only show messages after this timestamp
        
    Returns:
        list: List of tuples containing (username, message_text, timestamp)
    """
    if timestamp:
        result = execute_db_query("""
            SELECT username, message_text, timestamp
            FROM logs
            WHERE chat_id = %s AND timestamp > %s
        """, (chat_id, timestamp), fetch=True)
    else:
        result = execute_db_query("""
            SELECT username, message_text, timestamp
            FROM logs
            WHERE chat_id = %s
        """, chat_id, fetch=True)
    return result

# Function to check if chat has moderators
def has_moderators(chat_id: int) -> bool:
    """
    Check if chat has any moderators
    
    Args:
        chat_id (int): Chat ID
        
    Returns:
        bool: True if chat has moderators, False otherwise
    """
    result = execute_db_query(
        "SELECT COUNT(*) FROM user_is_moderator WHERE chat_id = %s",
        chat_id,
        fetch=True
    )
    return result[0][0] > 0

# Function to get message template for chat
def get_message_template(chat_id: int) -> str:
    """
    Get random message template for chat
    
    Args:
        chat_id (int): Chat ID
        
    Returns:
        str: Message template with optional {name} and {word} placeholders
    """
    result = execute_db_query("""
        SELECT template_text 
        FROM message_templates 
        WHERE chat_id = %s 
        ORDER BY template_id, RAND() 
        LIMIT 1
    """, chat_id, fetch=True)
    
    if result and result[0][0]:
        return result[0][0]
    return DEFAULT_TEMPLATE

# Function to add message template
def add_message_template(chat_id: int, template_text: str):
    """
    Add new message template for chat
    
    Args:
        chat_id (int): Chat ID
        template_text (str): Template text with {name} and {word} placeholders
        
    Returns:
        int: ID of the new template
    """
    # Get max template_id for this chat
    result = execute_db_query("""
        SELECT COALESCE(MAX(template_id), 0) 
        FROM message_templates 
        WHERE chat_id = %s
    """, chat_id, fetch=True)
    template_id = result[0][0] + 1
    
    execute_db_query("""
        INSERT INTO message_templates (chat_id, template_text, template_id)
        VALUES (%s, %s, %s)
    """, (chat_id, template_text, template_id))
    return template_id

# Function to remove message template
def remove_message_template(chat_id: int, template_id: int):
    """
    Remove message template from chat
    
    Args:
        chat_id (int): Chat ID
        template_id (int): ID of template to remove
    """
    execute_db_query("""
        DELETE FROM message_templates 
        WHERE chat_id = %s AND template_id = %s
    """, (chat_id, template_id))

# Function to list message templates
def list_message_templates(chat_id: int):
    """
    Get list of message templates for chat
    
    Args:
        chat_id (int): Chat ID
        
    Returns:
        list: List of tuples containing (template_id, template_text)
    """
    result = execute_db_query("""
        SELECT template_id, template_text 
        FROM message_templates 
        WHERE chat_id = %s
        ORDER BY template_id
    """, chat_id, fetch=True)
    return result

# Message checking function
async def check_message(update: Update, context: CallbackContext) -> None:
    """
    Check message for banned words and take action
    
    Args:
        update (Update): Telegram update object
        context (CallbackContext): Bot context
        
    Actions:
    1. Ignore bot's own messages
    2. Check message against banned words
    3. If banned word found:
       - Send template message
       - Log message
       - Delete message if enabled
    """
    # Ignore bot's own messages
    if update.message.from_user.id == context.bot.id:
        return
        
    message_text = update.message.text
    chat_id = update.message.chat.id
    user = update.message.from_user
    banned_words = get_banned_words(chat_id)
    print(f"Checking message: {message_text}")

    for word in banned_words:
        if re.search(r'\b' + re.escape(word) + r'\b', message_text.lower()):
            template = get_message_template(chat_id)
            try:
                # create dictionary with available variables
                template_vars = {}
                if '{name}' in template:
                    template_vars['name'] = user.username or user.first_name
                if '{word}' in template:
                    template_vars['word'] = word
                
                # format template only with available variables
                response = template.format(**template_vars)
            except KeyError as e:
                # if formatting error, use default template
                response = DEFAULT_TEMPLATE.format(
                    name=user.username or user.first_name,
                    word=word
                )
                
            await update.message.reply_text(response)
            message_data = {
                "user_id": user.id,
                "username": user.username,
                "message_text": message_text,
                "chat_id": chat_id,
                "message_id": update.message.message_id,
                "timestamp": update.message.date.isoformat(),
            }
            log_message(message_data)
            try:
                if delete_messages_check(chat_id):
                    await update.message.delete()
            except Exception as e:
                print(f"Error deleting message: {e}")
            break

# Command to add banned word
async def ban_word(update: Update, context: CallbackContext) -> None:
    """
    Command handler for /ban_word
    
    Args:
        update (Update): Telegram update object
        context (CallbackContext): Bot context
        
    Usage:
        /ban_word <word>
    """
    if not check_if_moderator(update.message.chat.id, update.message.from_user.id):
        await update.message.reply_text("You are not allowed to use this, sorry")
        return
    if context.args:
        word = context.args[0]
        add_banned_word(word, update.message.chat.id, update.message.from_user.id, update.message.chat.title)
        await update.message.reply_text(f"The word '{word}' has been banned.")
    else:
        await update.message.reply_text("Usage: /ban_word <word>")

# Command to remove banned word
async def remove_word(update: Update, context: CallbackContext) -> None:
    """
    Command handler for /remove_word
    
    Args:
        update (Update): Telegram update object
        context (CallbackContext): Bot context
        
    Usage:
        /remove_word <word>
    """
    if not check_if_moderator(update.message.chat.id, update.message.from_user.id):
        await update.message.reply_text("You are not allowed to use this, sorry")
        return
    if context.args:
        word = context.args[0]
        remove_banned_word(word, update.message.chat.id)
        await update.message.reply_text(f"The word '{word}' has been removed from the banned list.")
    else:
        await update.message.reply_text("Usage: /remove_word <word>")

# Command to show list of banned words
async def show_banned_words(update: Update, context: CallbackContext) -> None:
    """
    Command handler for /show_banned_words
    
    Args:
        update (Update): Telegram update object
        context (CallbackContext): Bot context
        
    Usage:
        /show_banned_words
    """
    words = get_banned_words(update.message.chat.id)
    if words:
        await update.message.reply_text("Banned words:\n" + "\n".join(words))
    else:
        await update.message.reply_text("No banned words yet.")
        
# Command to add moderator
async def add_moderator(update: Update, context: CallbackContext) -> None:
    """
    Command handler for /add_moderator
    
    Args:
        update (Update): Telegram update object
        context (CallbackContext): Bot context
        
    Usage:
        /add_moderator <username or user_id>
    """
    if not check_if_moderator(update.message.chat.id, update.message.from_user.id):
        await update.message.reply_text("You are not allowed to use this, sorry")
        return
    if context.args:
        moderator_raw = context.args[0]
        if moderator_raw.isdigit():  # If ID is entered
            moderator_id = int(moderator_raw)
            try:
                # Get username through user ID
                user = await context.bot.get_chat_member(update.message.chat.id, moderator_id)
                moderator = user.user.username
            except Exception as e:
                await update.message.reply_text(f"Error retrieving user: {e}")
                return
        else:  # If username is entered
            moderator = moderator_raw
            # Search for user by username
            try:
                chat_members = await context.bot.get_chat_administrators(update.message.chat.id)
                user = next((member for member in chat_members if member.user.username == moderator), None)
                if user:
                    moderator_id = user.user.id
                else:
                    raise Exception("User not found")
            except Exception as e:
                await update.message.reply_text(f"Error retrieving user: {e}")
                return
        
        if not moderator.startswith('@'):
            moderator = '@' + moderator
        result = new_moderator(moderator_id, moderator, update.message.chat.id)
        if result == "super_admin":
            await update.message.reply_text("This user is super admin")
        elif result == "already_moderator":
            await update.message.reply_text("This user already is moderator for this group")
        else:
            await update.message.reply_text(f"Moderator {moderator_raw} has been added.")
    
    else:
        await update.message.reply_text("Usage: /add_moderator <[user_id, username]>")

# Command to remove moderator
async def remove_moderator(update: Update, context: CallbackContext) -> None:
    """
    Command handler for /remove_moderator
    
    Args:
        update (Update): Telegram update object
        context (CallbackContext): Bot context
        
    Usage:
        /remove_moderator <username or user_id>
    """
    if not check_if_moderator(update.message.chat.id, update.message.from_user.id):
        await update.message.reply_text("You are not allowed to use this, sorry")
        return
    if context.args:
        moderator_raw = context.args[0]
        if moderator_raw.isdigit():  # If ID is entered
            moderator_id = int(moderator_raw)
        else:  # If username is entered
            moderator = moderator_raw
            # Search for user by username
            try:
                chat_members = await context.bot.get_chat_administrators(update.message.chat.id)
                user = next((member for member in chat_members if member.user.username == moderator), None)
                if user:
                    moderator_id = user.user.id
                else:
                    raise Exception("User not found")
            except Exception as e:
                await update.message.reply_text(f"Error retrieving user: {e}")
                return
        
        result = delete_moderator(moderator_id, update.message.chat.id)
        if result == "super_admin":
            await update.message.reply_text("This user is super admin and cannot be removed")
        else:
            await update.message.reply_text(f"Moderator {moderator_raw} has been removed.")

    else:
        await update.message.reply_text("Usage: /remove_moderator <[user_id, username]>")
        
# Command to show moderators
async def show_moderators(update: Update, context: CallbackContext) -> None:
    """
    Command handler for /show_moderators
    
    Args:
        update (Update): Telegram update object
        context (CallbackContext): Bot context
        
    Usage:
        /show_moderators
    """
    if context.args:
        await update.message.reply_text("Usage: /show_moderators")
        return
    else:
        moderators = list_moderators(update.message.chat.id)
        if moderators:
            for i in range(moderators.__len__()):
                if not moderators[i].startswith('@'):
                    moderators[i] = '@' + moderators[i]
            await update.message.reply_text("Moderators:\n" + "\n".join(moderators))
        else:
            await update.message.reply_text("No moderators yet.")
            
# Command to clear all banned words
async def clear_words(update: Update, context: CallbackContext) -> None:
    """
    Command handler for /clear_words
    
    Args:
        update (Update): Telegram update object
        context (CallbackContext): Bot context
        
    Usage:
        /clear_words
    """
    if not check_if_moderator(update.message.chat.id, update.message.from_user.id):
        await update.message.reply_text("You are not allowed to use this, sorry")
        return
    clear_words_by_chat(update.message.chat.id)
    
# Command to show messages
async def show_messages(update: Update, context: CallbackContext) -> None:
    """
    Command handler for /show_messages
    
    Args:
        update (Update): Telegram update object
        context (CallbackContext): Bot context
        
    Usage:
        /show_messages [timestamp]
    """
    if context.args:
        timestamp = context.args[0]
    else:
        timestamp = None
        
    messages = show_messages_by_chat(update.message.chat.id, timestamp)
    if messages:
        messages_str = [f"{msg[0]}: {msg[1]} at {msg[2]}" for msg in messages]
        await update.message.reply_text("Messages:\n" + "\n".join(messages_str))
    else:
        await update.message.reply_text("No messages yet.")
    
# Command to change message deletion setting
async def delete_messages(update: Update, context: CallbackContext) -> None:
    """
    Command handler for /delete_messages
    
    Args:
        update (Update): Telegram update object
        context (CallbackContext): Bot context
        
    Usage:
        /delete_messages <true/false>
    """
    if not check_if_moderator(update.message.chat.id, update.message.from_user.id):
        await update.message.reply_text("You are not allowed to use this, sorry")
        return
    if context.args:
        delete = context.args[0]
        if delete.lower == "true" or delete == "1":
            delete_messages_change(update.message.chat.id, True)
            await update.message.reply_text("Messages will be deleted")
        elif delete.lower == "false" or delete == "0":
            delete_messages_change(update.message.chat.id, False)
            await update.message.reply_text("Messages will not be deleted")
        else:
            await update.message.reply_text("Usage: /delete_messages <[true, false]>")
    else:
        await update.message.reply_text("Usage: /delete_messages <[true, false]>")

# Command to add message template
async def add_template(update: Update, context: CallbackContext) -> None:
    """
    Command handler for /add_template
    
    Args:
        update (Update): Telegram update object
        context (CallbackContext): Bot context
        
    Usage:
        Reply to a message with /add_template
    """
    if not check_if_moderator(update.message.chat.id, update.message.from_user.id):
        await update.message.reply_text("You are not allowed to use this, sorry")
        return
        
    if not update.message.reply_to_message:
        await update.message.reply_text("Please reply to a message with the template you want to add.")
        return
        
    template_text = update.message.reply_to_message.text
    template_id = add_message_template(update.message.chat.id, template_text)
    await update.message.reply_text(f"Template has been added successfully with ID: {template_id}!")

# Command to remove message template
async def remove_template(update: Update, context: CallbackContext) -> None:
    """
    Command handler for /remove_template
    
    Args:
        update (Update): Telegram update object
        context (CallbackContext): Bot context
        
    Usage:
        /remove_template <id>
    """
    if not check_if_moderator(update.message.chat.id, update.message.from_user.id):
        await update.message.reply_text("You are not allowed to use this, sorry")
        return
        
    if not context.args:
        await update.message.reply_text("Usage: /remove_template <template_id>")
        return
        
    try:
        template_id = int(context.args[0])
        remove_message_template(update.message.chat.id, template_id)
        await update.message.reply_text(f"Template with ID {template_id} has been removed successfully!")
    except ValueError:
        await update.message.reply_text("Invalid template ID. Please provide a number.")

# Command to list message templates
async def list_templates(update: Update, context: CallbackContext) -> None:
    """
    Command handler for /list_templates
    
    Args:
        update (Update): Telegram update object
        context (CallbackContext): Bot context
        
    Usage:
        /list_templates
    """
    if not check_if_moderator(update.message.chat.id, update.message.from_user.id):
        await update.message.reply_text("You are not allowed to use this, sorry")
        return
        
    templates = list_message_templates(update.message.chat.id)
    if templates:
        template_list = "\n".join([f"ID: {t[0]}\nTemplate: {t[1]}\n" for t in templates])
        await update.message.reply_text(f"Available templates:\n{template_list}")
    else:
        await update.message.reply_text("No custom templates found. Using default template.")

# Function to handle bot being added to chat
async def on_bot_added(update: Update, context: CallbackContext) -> None:
    """
    Handler for when bot is added to chat
    
    Args:
        update (Update): Telegram update object
        context (CallbackContext): Bot context
        
    Actions:
    1. Check if bot was added
    2. If no moderators exist, make the user who added bot a moderator
    """
    if update.message and update.message.new_chat_members:
        for member in update.message.new_chat_members:
            if member.id == context.bot.id:
                chat_id = update.message.chat.id
                chat_name = update.message.chat.title
                user_id = update.message.from_user.id
                username = update.message.from_user.username or str(user_id)
                
                # Check if chat already has moderators
                if not has_moderators(chat_id):
                    # If no moderators, add the user who added the bot
                    result = new_moderator(user_id, username, chat_id)
                    if result == "added":
                        await update.message.reply_text(f"@{username} has been automatically appointed as a bot moderator in this chat.")
                break

# Command to show help
async def help_command(update: Update, context: CallbackContext) -> None:
    if not context.args:
        help_text = """
Available commands:
/ban_word <word> - Ban a word in chat
/remove_word <word> - Remove banned word
/clear_words - Clear all banned words
/show_banned_words - Show all banned words
/add_moderator <username or user_id> - Add moderator
/remove_moderator <username or user_id> - Remove moderator
/show_moderators - Show all moderators
/show_messages [timestamp] - Show messages (optional: after timestamp)
/delete_messages <true/false> - Enable/disable message deletion
/add_template - Add message template (reply to message)
/remove_template <id> - Remove template by ID
/list_templates - Show all templates
/help <command> - Show detailed help for command
"""
        await update.message.reply_text(help_text)
        return

    command = context.args[0].lower().lstrip('/')
    help_text = get_command_help(command)
    if help_text:
        await update.message.reply_text(help_text)
    else:
        await update.message.reply_text(f"No help available for command: {command}")

def get_command_help(command: str) -> str:
    """Get detailed help text for a specific command"""
    help_texts = {
        "ban_word": """
Command: /ban_word <word>
Description: Ban a word in the current chat
Parameters:
- word: The word to ban (required)
Example: /ban_word badword
Note: Only moderators can use this command
""",
        "remove_word": """
Command: /remove_word <word>
Description: Remove a banned word from the current chat
Parameters:
- word: The word to remove from ban list (required)
Example: /remove_word badword
Note: Only moderators can use this command
""",
        "clear_words": """
Command: /clear_words
Description: Remove all banned words from the current chat
Example: /clear_words
Note: Only moderators can use this command
""",
        "show_banned_words": """
Command: /show_banned_words
Description: Show all banned words in the current chat
Example: /show_banned_words
Note: Only moderators can use this command
""",
        "add_moderator": """
Command: /add_moderator <username or user_id>
Description: Add a new moderator to the current chat
Parameters:
- username or user_id: The user to make moderator (required)
Example: /add_moderator @username
Example: /add_moderator 123456789
Note: Only moderators can use this command
""",
        "remove_moderator": """
Command: /remove_moderator <username or user_id>
Description: Remove a moderator from the current chat
Parameters:
- username or user_id: The moderator to remove (required)
Example: /remove_moderator @username
Example: /remove_moderator 123456789
Note: Only moderators can use this command
""",
        "show_moderators": """
Command: /show_moderators
Description: Show all moderators in the current chat
Example: /show_moderators
Note: Only moderators can use this command
""",
        "show_messages": """
Command: /show_messages [timestamp]
Description: Show messages in the current chat
Parameters:
- timestamp: Optional timestamp to show messages after (format: YYYY-MM-DD HH:MM:SS)
Example: /show_messages
Example: /show_messages 2024-03-20 12:00:00
Note: Only moderators can use this command
""",
        "delete_messages": """
Command: /delete_messages <true/false>
Description: Enable or disable automatic deletion of messages with banned words
Parameters:
- true/false: Whether to delete messages (required)
Example: /delete_messages true
Example: /delete_messages false
Note: Only moderators can use this command
""",
        "add_template": """
Command: /add_template
Description: Add a new message template (reply to a message)
Usage: Reply to a message with /add_template
Template variables (optional):
- {name}: Username of the message sender
- {word}: The banned word that was used
Examples:
- "Hi, {name}!" - only with name
- "This word {word} is banned!" - only with word
- "Hi, {name}! This word {word} is banned!" - with both variables
- "This message contains a banned word!" - without variables
Note: Only moderators can use this command
""",
        "remove_template": """
Command: /remove_template <id>
Description: Remove a message template by its ID
Parameters:
- id: The template ID to remove (required)
Example: /remove_template 1
Note: Only moderators can use this command
""",
        "list_templates": """
Command: /list_templates
Description: Show all message templates in the current chat
Example: /list_templates
Note: Only moderators can use this command
"""
    }
    return help_texts.get(command, "")

# Main function
def main() -> None:
    """
    Main function to start the bot
    
    Sets up:
    1. Bot application
    2. Command handlers
    3. Message handlers
    4. Starts polling for updates
    """
    application = Application.builder().token(TELEGRAM_BOT_API).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_message))
    application.add_handler(CommandHandler("ban_word", ban_word))
    application.add_handler(CommandHandler("remove_word", remove_word))
    application.add_handler(CommandHandler("clear_words", clear_words))
    application.add_handler(CommandHandler("show_banned_words", show_banned_words))
    application.add_handler(CommandHandler("add_moderator", add_moderator))
    application.add_handler(CommandHandler("remove_moderator", remove_moderator))
    application.add_handler(CommandHandler("show_moderators", show_moderators))
    application.add_handler(CommandHandler("show_messages", show_messages))
    application.add_handler(CommandHandler("delete_messages", delete_messages))
    application.add_handler(CommandHandler("add_template", add_template))
    application.add_handler(CommandHandler("remove_template", remove_template))
    application.add_handler(CommandHandler("list_templates", list_templates))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_bot_added))
    application.run_polling()

if __name__ == '__main__':
    main()
