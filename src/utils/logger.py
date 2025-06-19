import os
import json
import logging
import database.db as db
from datetime import datetime
from typing import Dict, Any, Optional
from logging.handlers import RotatingFileHandler

# Log config
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_MAX_SIZE = int(os.getenv("LOG_MAX_SIZE", "10485760"))  # 10MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

if not LOG_DIR:
    raise ValueError("LOG_DIR environment variable is not set.")

# Create directories for logs
for directory in [LOG_DIR + "/system", LOG_DIR + "/messages"]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# Configure system logging
system_logger = logging.getLogger('system')
system_logger.setLevel(logging.INFO)
system_handler = RotatingFileHandler(
    os.path.join(LOG_DIR + "/system", 'system.log'),
    maxBytes=LOG_MAX_SIZE,
    backupCount=LOG_BACKUP_COUNT
)
system_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
system_handler.setFormatter(system_formatter)
system_logger.addHandler(system_handler)

def log_system_event(event_type: str, details: Dict[str, Any], level: str = 'INFO') -> None:
    """
    Logging system events
    
    Args:
        event_type (str): Event type (e.g., 'command_executed', 'error_occurred')
        details (Dict[str, Any]): Event details
        level (str): Logging level ('INFO', 'WARNING', 'ERROR', 'CRITICAL')
    """
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'event_type': event_type,
        'details': details
    }
    
    log_method = getattr(system_logger, level.lower())
    log_method(json.dumps(log_data))

def log_message(message_data: Any, isMigrate: bool=False) -> None:
    """
    Logging user messages
    
    Args:
        message_data (Any): Message data, can be a single dictionary or a list of dictionaries
    """
    try:
        # Ensure message_data is a list of dictionaries
        if isinstance(message_data, dict):
            message_data = [message_data]
        elif not isinstance(message_data, list) or not all(isinstance(item, dict) for item in message_data):
            raise ValueError("message_data must be a dictionary or a list of dictionaries")
        
        # Create file name based on date
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = f"messages_{date_str}.json"
        log_path = os.path.join(LOG_DIR + "/messages", log_file)
        
        # Add timestamp to each message and save to database if applicable
        for message in message_data:
            message['timestamp'] = datetime.now().isoformat()
            if 'is_banned' in message:
                db.add_message(message)
        
        # Read existing data or create new file
        if not isMigrate:
            if os.path.exists(log_path):
                with open(log_path, 'r+', encoding='utf-8') as file:
                    try:
                        file_data = json.load(file)
                    except json.JSONDecodeError:
                        file_data = {"messages": []}
                    file_data["messages"].extend(message_data)
                    file.seek(0)
                    json.dump(file_data, file, indent=4, ensure_ascii=False)
            else:
                with open(log_path, 'w', encoding='utf-8') as file:
                    json.dump({"messages": message_data}, file, indent=4, ensure_ascii=False)
                
        # Log successful message saving
        for message in message_data:
            log_system_event(
                'message_logged',
                {'message_id': message.get('message_id'), 'chat_id': message.get('chat_id')},
                'INFO'
            )
    except Exception as e:
        log_system_event(
            'message_logging_error',
            {'error': str(e), 'message_data': message_data},
            'ERROR'
        )
