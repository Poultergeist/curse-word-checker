import os
import json
import mysql.connector
from datetime import datetime
from telegram import Update, BotCommand, BotCommandScopeChat
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackContext
from dotenv import load_dotenv
import re

# Завантаження змінних середовища
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
TELEGRAM_BOT_API = os.getenv("TELEGRAM_BOT_API")
LOG_DIR = os.getenv("LOG_DIR")

# Підключення до MySQL
def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

# Функція логування повідомлень
def log_message(message_data: dict, log_dir=LOG_DIR, log_file="message_log.json"):
    try:
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        log_path = os.path.join(log_dir, log_file)
        if os.path.exists(log_path) and os.path.getsize(log_path) > 10 * 1024 * 1024:
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

def check_if_moderator(chat_id: int, user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM user_is_moderator WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()    
    return result is not None and (result[0] == chat_id or result[0] == 0)

# Функція для додавання чату до БД, якщо його ще немає
def ensure_chat_exists(chat_id: int, chat_name: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT IGNORE INTO chats (id, name) VALUES (%s, %s)", (chat_id, chat_name))
    conn.commit()
    cursor.close()
    conn.close()

# Функція для додавання забороненого слова до БД
def add_banned_word(word: str, chat_id: int, user_id: int, chat_name: str):
    ensure_chat_exists(chat_id, chat_name)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO words (word, chat_id, who_banned) VALUES (%s, %s, %s)", (word.lower(), chat_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()

# Функція для видалення забороненого слова
def remove_banned_word(word: str, chat_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM words WHERE word = %s AND chat_id = %s", (word.lower(), chat_id))
    conn.commit()
    cursor.close()
    conn.close()

# Функція для отримання списку заборонених слів у чаті
def get_banned_words(chat_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT word FROM words WHERE chat_id = %s", (chat_id,))
    words = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return words

def new_moderator(user_id: int, username: str, chat_id: int) -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM user_is_moderator WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    if result and result[0] == 0:
        cursor.close()
        conn.close()
        return "super_admin"
    elif result and result[0] == chat_id:
        cursor.close()
        conn.close()
        return "already_moderator"
    cursor.execute("INSERT IGNORE INTO users (id, username) VALUES (%s, %s)", (user_id, username))
    cursor.execute("INSERT INTO user_is_moderator (user_id, chat_id) VALUES (%s, %s)", (user_id, chat_id))
    conn.commit()
    cursor.close()
    conn.close()
    return "added"

def delete_moderator(user_id: int, chat_id: int) -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM user_is_moderator WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    if result and result[0] == 0:
        cursor.close()
        conn.close()
        return "super_admin"
    cursor.execute("DELETE FROM user_is_moderator WHERE user_id = %s AND chat_id = %s", (user_id, chat_id))
    conn.commit()
    cursor.close()
    conn.close()
    return "removed"
    
def list_moderators(chat_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.username 
        FROM user_is_moderator um
        JOIN users u ON um.user_id = u.id
        WHERE um.chat_id = %s OR um.chat_id = 0
    """, (chat_id,))
    moderators = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return moderators

def clear_words_by_chat(chat_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM words WHERE chat_id = %s", (chat_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
def delete_messages_change(chat_id: int, delete: bool):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE chats SET delete_messages = %s WHERE id = %s", (delete, chat_id))
    conn.commit()
    cursor.close()
    conn.close()
    
def delete_messages_check(chat_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT delete_messages FROM chats WHERE id = %s", (chat_id,))
    delete_messages = cursor.fetchone()
    cursor.close()
    conn.close()
    return delete_messages[0]
    
def add_message(message_data: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO logs (user_id, username, message_text, chat_id, message_id, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (message_data["user_id"], message_data["username"], message_data["message_text"], message_data["chat_id"], message_data["message_id"], message_data["timestamp"]))
    conn.commit()
    cursor.close()
    conn.close()

def show_messages_by_chat(chat_id: int, timestamp: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if timestamp:
        cursor.execute("""
            SELECT username, message_text, timestamp
            FROM logs
            WHERE chat_id = %s AND timestamp > %s
        """, (chat_id, timestamp))
    else:
        cursor.execute("""
            SELECT username, message_text, timestamp
            FROM logs
            WHERE chat_id = %s
        """, (chat_id,))
    messages = [row for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return messages

# Функція перевірки повідомлень
async def check_message(update: Update, context: CallbackContext) -> None:
    message_text = update.message.text
    chat_id = update.message.chat.id
    user = update.message.from_user
    banned_words = get_banned_words(chat_id)
    print(f"Checking message: {message_text}")

    for word in banned_words:
        if re.search(r'\b' + re.escape(word) + r'\b', message_text.lower()):
            await update.message.reply_text(f"Hey, {user.username}, this word `{word}` is banned!")
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

# Команда для додавання забороненого слова
async def ban_word(update: Update, context: CallbackContext) -> None:
    if not check_if_moderator(update.message.chat.id, update.message.from_user.id):
        await update.message.reply_text("You are not allowed to use this, sorry")
        return
    if context.args:
        word = context.args[0]
        add_banned_word(word, update.message.chat.id, update.message.from_user.id, update.message.chat.title)
        await update.message.reply_text(f"The word '{word}' has been banned.")
    else:
        await update.message.reply_text("Usage: /ban_word <word>")

# Команда для видалення забороненого слова
async def remove_word(update: Update, context: CallbackContext) -> None:
    if not check_if_moderator(update.message.chat.id, update.message.from_user.id):
        await update.message.reply_text("You are not allowed to use this, sorry")
        return
    if context.args:
        word = context.args[0]
        remove_banned_word(word, update.message.chat.id)
        await update.message.reply_text(f"The word '{word}' has been removed from the banned list.")
    else:
        await update.message.reply_text("Usage: /remove_word <word>")

# Команда для відображення списку заборонених слів
async def show_banned_words(update: Update, context: CallbackContext) -> None:
    words = get_banned_words(update.message.chat.id)
    if words:
        await update.message.reply_text("Banned words:\n" + "\n".join(words))
    else:
        await update.message.reply_text("No banned words yet.")
        
async def add_moderator(update: Update, context: CallbackContext) -> None:
    if not check_if_moderator(update.message.chat.id, update.message.from_user.id):
        await update.message.reply_text("You are not allowed to use this, sorry")
        return
    if context.args:
        moderator_raw = context.args[0]
        if moderator_raw.isdigit():  # Якщо введено ID
            moderator_id = int(moderator_raw)
            try:
                # Отримуємо username через ID користувача
                user = await context.bot.get_chat_member(update.message.chat.id, moderator_id)
                moderator = user.user.username
            except Exception as e:
                await update.message.reply_text(f"Error retrieving user: {e}")
                return
        else:  # Якщо введено username
            moderator = moderator_raw
            # Шукаємо користувача по username
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

async def remove_moderator(update: Update, context: CallbackContext) -> None:
    if not check_if_moderator(update.message.chat.id, update.message.from_user.id):
        await update.message.reply_text("You are not allowed to use this, sorry")
        return
    if context.args:
        moderator_raw = context.args[0]
        if moderator_raw.isdigit():  # Якщо введено ID
            moderator_id = int(moderator_raw)
        else:  # Якщо введено username
            moderator = moderator_raw
            # Шукаємо користувача по username
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
        
async def show_moderators(update: Update, context: CallbackContext) -> None:
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
            
async def clear_words(update: Update, context: CallbackContext) -> None:
    if not check_if_moderator(update.message.chat.id, update.message.from_user.id):
        await update.message.reply_text("You are not allowed to use this, sorry")
        return
    clear_words_by_chat(update.message.chat.id)
    
async def show_messages(update: Update, context: CallbackContext) -> None:
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
    
    
async def delete_messages(update: Update, context: CallbackContext) -> None:
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

# Основна функція
def main() -> None:
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
    application.run_polling()

if __name__ == '__main__':
    main()
