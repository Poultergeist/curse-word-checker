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

def log_message(message_data: Dict[str, Any]) -> None:
    """
    Logging user messages
    
    Args:
        message_data (Dict[str, Any]): Message data
    """
    try:
        # Create file name based on date
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = f"messages_{date_str}.json"
        log_path = os.path.join(LOG_DIR + "/messages", log_file)
        
        # Add timestamp to message data
        message_data['timestamp'] = datetime.now().isoformat()
        
        if 'is_banned' in message_data:
            db.add_message(message_data)
        
        # Read existing data or create new file
        if os.path.exists(log_path):
            with open(log_path, 'r+', encoding='utf-8') as file:
                try:
                    file_data = json.load(file)
                except json.JSONDecodeError:
                    file_data = {"messages": []}
                file_data["messages"].append(message_data)
                file.seek(0)
                json.dump(file_data, file, indent=4, ensure_ascii=False)
        else:
            with open(log_path, 'w', encoding='utf-8') as file:
                json.dump({"messages": [message_data]}, file, indent=4, ensure_ascii=False)
                
        # Log successful message saving
        log_system_event(
            'message_logged',
            {'message_id': message_data.get('message_id'), 'chat_id': message_data.get('chat_id')},
            'INFO'
        )
    except Exception as e:
        log_system_event(
            'message_logging_error',
            {'error': str(e), 'message_data': message_data},
            'ERROR'
        )

def get_messages_by_date(date_str: str) -> Optional[Dict[str, Any]]:
    """
    Getting logs for a specific date
    
    Args:
        date_str (str): Date in format YYYY-MM-DD
        
    Returns:
        Optional[Dict[str, Any]]: Log data or None if file not found
    """
    log_file = f"messages_{date_str}.json"
    log_path = os.path.join(LOG_DIR + "/messages", log_file)
    
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    return None 