from database.db import add_message, show_messages_by_chat
import os
import json
from utils.logger import log_system_event, log_message

def load_from_json_to_db(log_path: str) -> None:
    """
    Load messages from a JSON file into the database.
    
    Args:
        file_path (str): Path to the JSON file.
    """
    try:
      if not os.path.exists(log_path): 
        log_system_event(
            'migration_error_json',
            {'error': f"{log_path} does not exist."},
            'ERROR'
        )
        return
      
      if not os.path.isdir(log_path):
        log_system_event(
            'migration_error_json',
            {'error': f"{log_path} is not a directory."},
            'ERROR'
        )
        return
      
      files = sorted(os.listdir(log_path))
      for file_name in files:
        file_path = os.path.join(log_path, file_name)
        if os.path.isfile(file_path) and file_name.endswith('.json'):
          with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            for message in data.get('messages', []):
              if 'is_banned' in message:
                add_message(message)
        else:
          log_system_event(
              'migration_error_json',
              {'error': f"{file_path} is not a valid JSON file."},
              'ERROR'
          )
          continue
      log_system_event(
          'migration_success_json',
          {'file_path': file_path},
          'INFO'
      )
    except Exception as e:
        log_system_event(
            'migration_error_json',
            {'error': str(e), 'log_path': log_path},
            'ERROR'
        )
        raise e
      
async def load_from_db_to_json(log_path: str) -> None:
    """
    Load messages from the database into a JSON file.
    
    Args:
        log_path (str): Path to the directory where JSON files will be saved.
    """
    try:
      if not os.path.isdir(log_path):
        log_system_event(
            'migration_error_json',
            {'error': f"{log_path} is not a directory."},
            'ERROR'
        )
        return
      
      if not os.path.exists(log_path):
        os.makedirs(log_path)
        log_system_event(
            'migration_success_json',
            {'log_path': f'Directory created: {log_path}'},
            'INFO'
        )
      
      # Fetch messages from the database
      messages = show_messages_by_chat()
      
      if not messages:
        log_system_event(
            'migration_no_data',
            {'log_path': log_path},
            'INFO'
        )
        return
      
      await log_message(messages, isMigrate=True)
      
    except Exception as e:
        log_system_event(
            'migration_error_db',
            {'error': str(e), 'log_path': log_path},
            'ERROR'
        )
        raise e