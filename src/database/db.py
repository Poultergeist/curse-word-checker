import mysql.connector
from config.settings import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
import random
import json
from utils.logger import log_system_event

def execute_db_query(query: str, params=None, fetch: bool = False) -> list | None:
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
        log_system_event(
            'db_error',
            {'error': str(e), 'query': query, 'params': params},
            'ERROR'
        )
        if conn:
            conn.rollback()
        raise e
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def ensure_chat_exists(chat_id: int, chat_name: str) -> None:
    """
    Ensure chat exists in database, create if it doesn't
    
    Args:
        chat_id (int): ID of the chat
        chat_name (str): Name of the chat
    """
    execute_db_query(
        "INSERT IGNORE INTO chats (id, name) VALUES (%s, %s)",
        (chat_id, chat_name)
    )

def add_banned_word(word: str, chat_id: int, user_id: int, chat_name: str) -> None:
    """
    Add word to banned words list for chat
    
    Args:
        word (str): Word to ban
        chat_id (int): ID of the chat
        user_id (int): ID of the user who banned the word
        chat_name (str): Name of the chat
    """
    ensure_chat_exists(chat_id, chat_name)
    execute_db_query(
        "INSERT IGNORE INTO words (word, chat_id, who_banned) VALUES (%s, %s, %s)",
        (word.lower(), chat_id, user_id)
    )

def remove_banned_word(word: str, chat_id: int) -> None:
    """
    Remove word from banned words list for chat
    
    Args:
        word (str): Word to remove
        chat_id (int): ID of the chat
    """
    execute_db_query(
        "DELETE FROM words WHERE word = %s AND chat_id = %s",
        (word.lower(), chat_id)
    )

def get_banned_words(chat_id: int) -> list[str]:
    """
    Get list of banned words for chat
    
    Args:
        chat_id (int): ID of the chat
    
    Returns:
        list (list[str]): List of banned words for the chat
    """
    result = execute_db_query(
        "SELECT word FROM words WHERE chat_id = %s",
        chat_id,
        fetch=True
    )
    return [row[0] for row in result]

def check_if_moderator(chat_id: int, user_id: int) -> bool | int:
    """
    Check if user is a moderator in the specified chat
    
    Args:
        chat_id (int): ID of the chat
        user_id (int): ID of the user
    
    Returns:
        bool/int: True if user is a moderator in the chat, 0 if user is superadmin, False otherwise
    """
    result = execute_db_query(
        "SELECT chat_id FROM user_is_moderator WHERE user_id = %s",
        user_id,
        fetch=True
    )
    # Fix: handle empty result
    if not result:
        return False
    if result[0][0] == chat_id:
        return True
    elif result[0][0] == 0:
        return 0
    else:
        return False

def new_moderator(user_id: int, username: str, chat_id: int) -> str:
    """
    Add new moderator to chat
    
    Args:
        user_id (int): ID of the user to add as moderator
        username (str): Username of the user
        chat_id (int): ID of the chat
        
    Returns:
        str: "added" if moderator was added, "already_moderator" if user is already a moderator,
             "super_admin" if user is superadmin
    """
    result = check_if_moderator(chat_id, user_id)
    if result:
        return "already_moderator"
    if result == 0:
        return "super_admin"
    
    execute_db_query(
        "INSERT IGNORE INTO users (id, username) VALUES (%s, %s)",
        (user_id, username)
    )
    execute_db_query(
        "INSERT INTO user_is_moderator (user_id, chat_id) VALUES (%s, %s)",
        (user_id, chat_id)
    )
    return "added"

def delete_moderator(user_id: int, chat_id: int) -> str:
    """
    Remove moderator from chat
    
    Args:
        user_id (int): ID of the user to remove as moderator
        chat_id (int): ID of the chat
    
    Returns:
        str: "removed" if moderator was removed, "super_admin" if user is superadmin,
             "not_moderator" if user is not a moderator
    """
    result = check_if_moderator(chat_id, user_id)
    
    if result:
        if result == 0:
            return "super_admin"
        return "not_moderator"
    
    execute_db_query(
        "DELETE FROM user_is_moderator WHERE user_id = %s AND chat_id = %s",
        (user_id, chat_id)
    )
    return "removed"

def list_moderators(chat_id: int) -> list:
    """
    Get list of moderators for chat
    
    Args:
        chat_id (int): ID of the chat
        
    Returns:
        list: List of tuples (user_id, username) for moderators in the chat
    """
    return execute_db_query(
        "SELECT u.id, u.username FROM users u JOIN user_is_moderator m ON u.id = m.user_id WHERE m.chat_id = %s",
        chat_id,
        fetch=True
    )

def clear_words_by_chat(chat_id: int) -> None:
    """
    Clear all banned words for chat
    
    Args:
        chat_id (int): ID of the chat
    """
    execute_db_query(
        "DELETE FROM words WHERE chat_id = %s",
        chat_id
    )

def delete_messages_change(chat_id: int, delete: bool) -> None:
    """
    Change delete messages setting for chat
    
    Args:
        chat_id (int): ID of the chat
        delete (bool): True to enable delete messages, False to disable
    """
    execute_db_query(
        "UPDATE chats SET delete_messages = %s WHERE id = %s",
        (delete, chat_id)
    )

def delete_messages_check(chat_id: int) -> bool:
    """
    Check if delete messages is enabled for chat
    
    Args:
        chat_id (int): ID of the chat
        
    Returns:
        bool: True if delete messages is enabled, False otherwise
    """
    result = execute_db_query(
        "SELECT delete_messages FROM chats WHERE id = %s",
        chat_id,
        fetch=True
    )
    return result and result[0][0]

def add_message(message_data: dict) -> None:
    """
    Add message to database
    
    Args:
        message_data (dict): Dictionary containing message data with keys:
            - chat_id (int): ID of the chat
            - user_id (int): ID of the user who sent the message
            - message_id (int): ID of the message
            - message_text (str): Text of the message
            - timestamp (str): Timestamp of the message in ISO format
            - username (str): Username of the user who sent the message
            - banned_words (list): List of banned words found in the message (optional)
    """
    execute_db_query(
        """
        INSERT INTO logs (chat_id, user_id, message_id, message_text, timestamp, username, banned_words)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            message_data["chat_id"],
            message_data["user_id"],
            message_data["message_id"],
            message_data["message_text"],
            message_data["timestamp"],
            message_data["username"],
            json.dumps(message_data["banned_words"]) if message_data.get("banned_words") else None
        )
    )

def show_messages_by_chat(chat_id: int, timestamp: str = None) -> list:
    """
    Get messages for chat with optional timestamp filter
    
    Args:
        chat_id (int): ID of the chat
        timestamp (str): Optional timestamp in ISO format to filter messages
    
    Returns:
        list: List of messages for the chat, optionally filtered by timestamp
    """
    # If timestamp is provided, return messages from that timestamp onwards
    if timestamp:
        return execute_db_query(
            "SELECT * FROM logs WHERE chat_id = %s AND timestamp >= %s",
            (chat_id, timestamp),
            fetch=True
        )
        
    # If no chat_id, return all messages
    if not chat_id:
        return execute_db_query(
            "SELECT * FROM logs",
            fetch=True
        )
        
    # If chat_id is provided, return messages for that chat
    return execute_db_query(
        "SELECT * FROM logs WHERE chat_id = %s",
        chat_id,
        fetch=True
    )

def has_moderators(chat_id: int) -> bool:
    """
    Check if chat has any moderators
    
    Args:
        chat_id (int): ID of chat
    
    Returns:
        bool: True if chat has moderators, False otherwise
    """
    result = execute_db_query(
        "SELECT COUNT(*) FROM user_is_moderator WHERE chat_id = %s",
        chat_id,
        fetch=True
    )
    return result and result[0][0] > 0

def get_message_template(chat_id: int) -> str:
    """
    Get a random message template for chat
    
    Args:
        chat_id (int): ID чату
        
    Returns:
        str: Random message template or None if no templates exist
    """
    result = execute_db_query(
        "SELECT template_text FROM message_templates WHERE chat_id = %s",
        chat_id,
        fetch=True
    )
    if not result:
        return None
    return random.choice(result)[0]

def add_message_template(chat_id: int, template_text: str) -> None:
    """
    Add new message template for chat
    
    Args:
        chat_id (int): ID of the chat
        template_text (str): Text of the message template
    """
    template_id = execute_db_query(
        "SELECT MAX(template_id) FROM message_templates WHERE chat_id = %s",
        chat_id,
        fetch=True
    )[0][0]
    if template_id is not None:
        template_id += 1
    else:
        template_id = 1
    execute_db_query(
        "INSERT INTO message_templates (chat_id, template_id, template_text) VALUES (%s, %s, %s)",
        (chat_id, template_id, template_text)
    )

def remove_message_template(chat_id: int, template_id: int) -> None:
    """
    Remove message template
    
    Args:
        chat_id (int): ID of the chat
        template_id (int): ID of the template to remove
    """
    execute_db_query(
        "DELETE FROM message_templates WHERE template_id = %s AND chat_id = %s",
        (template_id, chat_id)
    )

def list_message_templates(chat_id: int) -> list:
    """
    Get list of message templates for chat
    
    Args:
        chat_id (int): ID of the chat

    Returns:
        list: List of tuples (template_id, template_text) for templates in the chat
    """
    return execute_db_query(
        "SELECT template_id, template_text FROM message_templates WHERE chat_id = %s",
        chat_id,
        fetch=True
    )

def reorder_template_ids(chat_id: int) -> None:
    """
    Reorder template IDs sequentially for a given chat.
    
    Args:
        chat_id (int): ID of the chat for which to reorder templates.
    """
    templates = list_message_templates(chat_id)
    for index, template in enumerate(templates, start=1):
        update_template_id(chat_id, template[0], index)

def update_template_id(chat_id: int, old_id: int, new_id: int) -> None:
    """
    Update a specific template ID.
    
    Args:
        chat_id (int): ID of the chat.
        old_id (int): Current ID of the template.
        new_id (int): New ID to assign to the template.
    """
    execute_db_query("UPDATE message_templates SET template_id = %s WHERE chat_id = %s AND template_id = %s", (new_id, chat_id, old_id))

def delete_chat_and_moderators(chat_id: int) -> None:
    """
    Delete chat and all connected moderators from database
    
    Args:
        chat_id (int): ID of the chat to delete
    """
    # Remove moderators for this chat
    execute_db_query(
        "DELETE FROM user_is_moderator WHERE chat_id = %s",
        chat_id
    )
    # Remove chat itself
    execute_db_query(
        "DELETE FROM chats WHERE id = %s",
        chat_id
    )
    # Optionally, remove other chat-related data (words, templates, logs)
    execute_db_query(
        "DELETE FROM words WHERE chat_id = %s",
        chat_id
    )
    execute_db_query(
        "DELETE FROM message_templates WHERE chat_id = %s",
        chat_id
    )
    execute_db_query(
        "DELETE FROM logs WHERE chat_id = %s",
        chat_id
    )

def get_statistics(chat_id: int, date) -> dict:
    """
    Returns statistics for a chat and date:
    - top users by banned words used
    - top banned words used
    - message with the most banned words used
    
    Args:
        chat_id (int): ID of the chat
        date (datetime.date): Date for which to get statistics
        
    Returns:
        dict: Dictionary containing:
            - user_stats (list): List of top users with banned words used
            - word_stats (list): List of top banned words used
            - most_banned_message (tuple): Message with the most banned words used
    """
    date_str = date.strftime("%Y-%m-%d")
    # Top users
    user_stats = execute_db_query(
        """
        SELECT l.username, COUNT(*) as cnt
        FROM logs l
        WHERE l.chat_id = %s AND DATE(l.timestamp) = %s
          AND l.banned_words IS NOT NULL AND JSON_LENGTH(l.banned_words) > 0
        GROUP BY l.user_id, l.username
        ORDER BY cnt DESC
        LIMIT 10
        """,
        (chat_id, date_str),
        fetch=True
    )
    
    # Top banned words
    word_stats = execute_db_query(
        """
        SELECT bw.word, COUNT(*) as cnt
        FROM logs l
        JOIN JSON_TABLE(l.banned_words, '$[*]' COLUMNS(word VARCHAR(255) PATH '$')) bw
        WHERE l.chat_id = %s AND DATE(l.timestamp) = %s
          AND l.banned_words IS NOT NULL AND JSON_LENGTH(l.banned_words) > 0
        GROUP BY bw.word
        ORDER BY cnt DESC
        LIMIT 10
        """,
        (chat_id, date_str),
        fetch=True
    )
    
    # Message with most banned words
    most_banned_message = execute_db_query(
        """
        SELECT l.message_text, JSON_LENGTH(l.banned_words) as banned_count
        FROM logs l
        WHERE l.chat_id = %s AND DATE(l.timestamp) = %s
          AND l.banned_words IS NOT NULL AND JSON_LENGTH(l.banned_words) > 0
        ORDER BY banned_count DESC
        LIMIT 1
        """,
        (chat_id, date_str),
        fetch=True
    )
     
    return {
        "user_stats": user_stats or [],
        "word_stats": word_stats or [],
        "most_banned_message": most_banned_message[0] if most_banned_message else None
    }