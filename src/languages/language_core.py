import os
import json

__t = {}
  
def list_locales(debug: bool = False) -> list:
    """
    List all available locales in the 'locales' directory.
    
    Returns:
        list: A list of locale names (without file extensions).
    """


    locales_dir = os.path.join(os.path.dirname(__file__), "locales")
    if not os.path.exists(locales_dir):
        return []
    
    __l = {
        os.path.splitext(file)[0]: file for file in os.listdir(locales_dir)
        if file.endswith(".json")
    }
    
    if debug:
        print(f"Locales found: {list(__l.keys())}")
    
    return list(__l.keys())

def get_locales(debug: bool = False) -> list:
  """
  Get the list of available locales.
  
  Returns:
      list: A list of locales.
  """
  global __t
  if __t == {}:
    for locale in list_locales():
      with open(os.path.join(os.path.dirname(__file__), "locales", f"{locale}.json"), "r", encoding="utf-8") as file:
        try:
          data = json.load(file)
        except json.JSONDecodeError:
          data = {}

      if not isinstance(data, dict):
        if not debug:
          log_system_event(
            'locale_error',
            {'locale': locale, 'error': 'Invalid JSON format'},
            'ERROR'
          )
        raise ValueError(f"Locale file {locale}.json must contain a JSON object.")

      __t[locale] = data
      if not debug:
        log_system_event(
            'locale_loaded',
            {'locale': locale, 'data_length': len(data)},
            'INFO'
        )
  return __t

def get_locales_list(debug: bool = False) -> list:
  """
  Get the list of locales that are already initialized.
  
  Returns:
      list: A list of strings containing locale names.
  """
  global __t
  locales = list(__t.keys())
  if debug:
    print(f"Locales available: {locales}")
  return locales
  
def reinitialize_locales(debug: bool = False) -> list:
  """
  Reinitialize the locales dictionary.
  This function can be called to reset the locales cache.
  
  Returns:
      list: A list of locales.
  """
  global __t
  __t = {}
  if not debug:
    log_system_event('locales_reinitialized', {"message": "Locales reinitialisation started"}, 'INFO')
  return get_locales(debug)

if __name__ == "__main__":
  print("This is test for language_core.py")
  print(list_locales())  
  print(get_locales(True))
  print(get_locales_list(True))
else:
  from utils.logger import log_system_event