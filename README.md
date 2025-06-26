# Telegram Curse Word Bot

A Telegram bot to help chat moderators control the use of banned words, manage moderators, customize warning templates, and support multiple languages.

## Features

- Checks messages for banned words (whole-word match)
- Optionally deletes messages with banned words
- Customizable warning templates with placeholders
- Moderator management (add/remove/list)
- Logging of messages and statistics
- Locale/language support (switch bot language per chat)
- Command help with detailed usage and examples

## Commands

### Word Management
- `/word ban <words>` — Ban one or more words (e.g. `/word ban word1 word2`)
- `/word unban <words>` — Unban one or more words (e.g. `/word unban word1 word2`)
- `/word list` — Show banned words
- `/word clear` — Clear all banned words

### Moderator Management
- **Reply to a user** `/mod add` — Add moderator
- **Reply to a user** `/mod delete` — Remove moderator
- `/mod list` — Show moderators

### Template Management
- `/template add <text>` — Add a message template (supports `{name}` and `{word}` placeholders)
- `/template delete <id>` — Remove a template
- `/template list` — Show templates

### Locale Management
- `/locale list` — Show available locales
- `/locale current` — Show current locale for the chat
- `/locale set <locale>` — Set locale for the chat (e.g. `/locale set en`)

### Other Commands
- `/messages [timestamp]` — Show recent messages (optionally since a date)
- `/delete [on|off]` — Toggle automatic message deletion
- `/statistics [dd-mm-yy]` — Show statistics for today or a given date (top users, top banned words)
- `/help [command] [subcommand]` — Show help for commands

## Message Templates

Templates can include:
- `{name}` — user's first name
- `{word}` — banned word(s)

**Examples:**
- `Hey, {name}!`
- `Don't use {word}!`
- `Hey {name}, don't use {word}!`
- `This word is not allowed!`

## Locale/Language Support

You can switch the bot's language per chat using `/locale set <locale>`.  
Available locales are listed with `/locale list`.  
Default locales provided: `en` (English), `tem` (Temmie-style English).

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/your-username/curse-word-bot.git
    cd curse-word-bot
    ```

2. Create a virtual environment and install dependencies:
    ```bash
    python -m venv venv
    source venv/bin/activate  # for Linux/Mac
    # or
    venv\Scripts\activate  # for Windows
    pip install -r requirements.txt
    ```

3. Copy the example environment file and configure:
    ```bash
    cp .env.example .env
    ```
    Edit `.env` and set your database and Telegram bot credentials.

4. Create the database and tables:
    ```bash
    mysql -u your_username -p your_database < structure.sql
    ```

5. Run the bot:
    ```bash
    python src/main.py
    ```

## Running on a Server

To run the bot in the background:
```bash
nohup python src/main.py > bot.log 2>&1 &
```

Or use a systemd service:
```ini
[Unit]
Description=Telegram Curse Word Bot
After=network.target

[Service]
User=your_user
WorkingDirectory=/path/to/curse-word-bot
Environment=PYTHONPATH=/path/to/curse-word-bot
ExecStart=/path/to/curse-word-bot/venv/bin/python src/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## License

MIT