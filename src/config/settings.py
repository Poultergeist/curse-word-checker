import os
from dotenv import load_dotenv

# Loading environment variables
load_dotenv()

# Database settings
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# Telegram settings
TELEGRAM_BOT_API = os.getenv("TELEGRAM_BOT_API")

# Logging settings
LOG_DIR = os.getenv("LOG_DIR", "logs")  # Default logs directory
LOG_FILE = os.getenv("LOG_FILE", "message_log.json")  # Default log filename
LOG_MAX_SIZE = int(os.getenv("LOG_MAX_SIZE", "10485760"))  # Default 10MB in bytes

# Message template settings
DEFAULT_TEMPLATE = os.getenv("DEFAULT_TEMPLATE", "Hey, {name}, this word `{word}` is banned!") 