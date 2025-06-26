import argparse

_parser = None
_args = None

# This module provides a global argument parser for the Telegram Curse Word Bot.
def get_parser() -> argparse.ArgumentParser:
    """Initialize and return the global argument parser.
    If the parser is already initialized, it returns the existing instance.
    
    Returns:
        argparse.ArgumentParser: The global argument parser instance.
    """
    global _parser
    if _parser is None:
        _parser = argparse.ArgumentParser(description="Telegram Curse Word Bot")
        _parser.add_argument(
            "-D", "--debug", action="store_true", help="Enable debug mode"
        )
        _parser.add_argument(
            "--migrate",
            choices=["json", "db"],
            help="Migrate messages to 'json' or 'db'"
        )
        # Add more global arguments here if needed
    return _parser

def parse_args() -> argparse.Namespace:
    """Parse and return the global arguments.
    If the arguments have already been parsed, it returns the cached result.
    
    Returns:
        argparse.Namespace: The parsed arguments.
    """
    global _args
    if _args is None:
        _args = get_parser().parse_args()
    return _args
