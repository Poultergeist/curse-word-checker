import os
import json
from datetime import datetime
from src.config.settings import LOG_DIR, LOG_FILE, LOG_MAX_SIZE

def log_message(message_data: dict, log_dir=LOG_DIR, log_file=LOG_FILE):
    """
    Log message data to JSON file with automatic rotation
    
    Args:
        message_data (dict): Message data to log
        log_dir (str): Directory for log files
        log_file (str): Name of the log file
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
    except Exception as e:
        print(f"Error logging message: {e}") 