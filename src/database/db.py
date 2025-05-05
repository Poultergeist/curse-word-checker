import mysql.connector
from src.config.settings import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

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

def ensure_chat_exists(chat_id: int, chat_name: str):
    """Ensure chat exists in database, create if it doesn't"""
    execute_db_query(
        "INSERT IGNORE INTO chats (id, name) VALUES (%s, %s)",
        (chat_id, chat_name)
    )

def add_banned_word(word: str, chat_id: int, user_id: int, chat_name: str):
    """Add word to banned words list for chat"""
    ensure_chat_exists(chat_id, chat_name)
    execute_db_query(
        "INSERT INTO words (word, chat_id, who_banned) VALUES (%s, %s, %s)",
        (word.lower(), chat_id, user_id)
    )

def remove_banned_word(word: str, chat_id: int):
    """Remove word from banned words list for chat"""
    execute_db_query(
        "DELETE FROM words WHERE word = %s AND chat_id = %s",
        (word.lower(), chat_id)
    )

def get_banned_words(chat_id: int):
    """Get list of banned words for chat"""
    result = execute_db_query(
        "SELECT word FROM words WHERE chat_id = %s",
        chat_id,
        fetch=True
    )
    return [row[0] for row in result]

def check_if_moderator(chat_id: int, user_id: int):
    """Check if user is a moderator in the specified chat"""
    result = execute_db_query(
        "SELECT chat_id FROM user_is_moderator WHERE user_id = %s",
        user_id,
        fetch=True
    )
    return result is not None and (result[0][0] == chat_id or result[0][0] == 0)

def new_moderator(user_id: int, username: str, chat_id: int) -> str:
    """Add new moderator to chat"""
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

def delete_moderator(user_id: int, chat_id: int) -> str:
    """Remove moderator from chat"""
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

def list_moderators(chat_id: int):
    """Get list of moderators for chat"""
    return execute_db_query(
        "SELECT u.id, u.username FROM users u JOIN user_is_moderator m ON u.id = m.user_id WHERE m.chat_id = %s",
        chat_id,
        fetch=True
    )

def clear_words_by_chat(chat_id: int):
    """Clear all banned words for chat"""
    execute_db_query(
        "DELETE FROM words WHERE chat_id = %s",
        chat_id
    )

def delete_messages_change(chat_id: int, delete: bool):
    """Change delete messages setting for chat"""
    execute_db_query(
        "UPDATE chats SET delete_messages = %s WHERE id = %s",
        (delete, chat_id)
    )

def delete_messages_check(chat_id: int) -> bool:
    """Check if delete messages is enabled for chat"""
    result = execute_db_query(
        "SELECT delete_messages FROM chats WHERE id = %s",
        chat_id,
        fetch=True
    )
    return result and result[0][0]

def add_message(message_data: dict):
    """Add message to database"""
    execute_db_query(
        """
        INSERT INTO messages (chat_id, user_id, message_id, text, timestamp)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            message_data["chat_id"],
            message_data["user_id"],
            message_data["message_id"],
            message_data["text"],
            message_data["timestamp"]
        )
    )

def show_messages_by_chat(chat_id: int, timestamp: str = None):
    """Get messages for chat with optional timestamp filter"""
    if timestamp:
        return execute_db_query(
            "SELECT * FROM messages WHERE chat_id = %s AND timestamp >= %s",
            (chat_id, timestamp),
            fetch=True
        )
    return execute_db_query(
        "SELECT * FROM messages WHERE chat_id = %s",
        chat_id,
        fetch=True
    )

def has_moderators(chat_id: int) -> bool:
    """Check if chat has any moderators"""
    result = execute_db_query(
        "SELECT COUNT(*) FROM user_is_moderator WHERE chat_id = %s",
        chat_id,
        fetch=True
    )
    return result and result[0][0] > 0

def get_message_template(chat_id: int) -> str:
    """Get message template for chat"""
    result = execute_db_query(
        "SELECT template FROM message_templates WHERE chat_id = %s AND is_active = 1",
        chat_id,
        fetch=True
    )
    return result[0][0] if result else None

def add_message_template(chat_id: int, template_text: str):
    """Add new message template for chat"""
    execute_db_query(
        "UPDATE message_templates SET is_active = 0 WHERE chat_id = %s",
        chat_id
    )
    execute_db_query(
        "INSERT INTO message_templates (chat_id, template, is_active) VALUES (%s, %s, 1)",
        (chat_id, template_text)
    )

def remove_message_template(chat_id: int, template_id: int):
    """Remove message template"""
    execute_db_query(
        "DELETE FROM message_templates WHERE id = %s AND chat_id = %s",
        (template_id, chat_id)
    )

def list_message_templates(chat_id: int):
    """Get list of message templates for chat"""
    return execute_db_query(
        "SELECT id, template, is_active FROM message_templates WHERE chat_id = %s",
        chat_id,
        fetch=True
    ) 