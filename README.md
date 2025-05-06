# Telegram Curse Word Bot

Бот для Telegram, який допомагає модераторам чатів контролювати використання заборонених слів.

## Функціональність

- Перевірка повідомлень на наявність заборонених слів
- Автоматичне видалення повідомлень з забороненими словами (опціонально)
- Налаштовувані шаблони попереджень
- Система модераторів
- Логування повідомлень

## Команди

### Управління словами
- `/word ban <слова>` - забанити одне або кілька слів (наприклад: `/word ban слово1 слово2`)
- `/word unban <слова>` - розбанити одне або кілька слів (наприклад: `/word unban слово1 слово2`)
- `/word list` - показати список забанених слів
- `/word clear` - очистити всі забанені слова

### Управління модераторами
- **Відповідь на повідомлення користувача** `/mod add` - додати модератора
- **Відповідь на повідомлення користувача** `/mod delete` - видалити модератора
- `/mod list` - показати список модераторів

### Управління шаблонами
- `/template add <текст>` - додати шаблон повідомлення
- `/template delete <id>` - видалити шаблон
- `/template list` - показати список шаблонів

### Інші команди
- `/messages [timestamp]` - показати останні повідомлення
- `/delete [on|off]` - увімкнути/вимкнути автоматичне видалення повідомлень
- `/help [команда] [підкоманда]` - показати допомогу

## Шаблони повідомлень

Шаблони можуть містити опціональні плейсхолдери:
- `{name}` - ім'я користувача
- `{word}` - заборонене слово

Приклади шаблонів:
- "Привіт, {name}!"
- "Не використовуй слово {word}!"
- "Привіт, {name}! Не використовуй слово {word}!"
- "Це слово заборонено!"

## Встановлення

1. Клонуйте репозиторій:
```bash
git clone https://github.com/your-username/curse-word-bot.git
cd curse-word-bot
```

2. Створіть віртуальне середовище та встановіть залежності:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
# або
venv\Scripts\activate  # для Windows
pip install -r requirements.txt
```

3. Створіть файл `.env` на основі `.env.example`:
```bash
cp .env.example .env
```

4. Налаштуйте змінні середовища в `.env`:
```
DB_HOST=host
DB_USER=user
DB_PASSWORD=password
DB_NAME=database_name

TELEGRAM_BOT_API=telegram_bot_api_key

LOG_DIR=logs
LOG_FILE=message_log.json
LOG_MAX_SIZE=10485760  # 10MB in bytes

DEFAULT_TEMPLATE="Default template {name} {word}"
```

5. Створіть базу даних та таблиці:
```bash
mysql -u your_username -p your_database < structure.sql
```

6. Запустіть бота:
```bash
python src/main.py
```

## Запуск на сервері

Для запуску бота в фоновому режимі на сервері можна використовувати `nohup`:
```bash
nohup python src/main.py > bot.log 2>&1 &
```

Або створити systemd сервіс:
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

## Ліцензія

MIT