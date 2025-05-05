# Telegram Curse Word Bot

Бот для модерації заборонених слів у Telegram-чатах.

## Функціональність

- Заборона та розборона слів
- Система модераторів
- Налаштовувані шаблони повідомлень
- Автоматичне видалення повідомлень
- Логування повідомлень
- Перегляд історії повідомлень

## Встановлення

1. Клонуйте репозиторій:
```bash
git clone https://github.com/yourusername/curse-word-bot.git
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

3. Створіть файл `.env` на основі `.env.example` та заповніть необхідні змінні:
```bash
cp .env.example .env
```

4. Створіть базу даних та таблиці:
```bash
mysql -u your_username -p your_database < structure.sql
```

## Запуск

```bash
python src/main.py
```

## Команди

- `/ban <word>` - Заборонити слово
- `/unban <word>` - Розборонити слово
- `/list` - Показати список заборонених слів
- `/addmod` - Додати модератора (відповідь на повідомлення користувача)
- `/delmod` - Видалити модератора (відповідь на повідомлення модератора)
- `/mods` - Показати список модераторів
- `/clear` - Очистити всі заборонені слова
- `/messages [timestamp]` - Показати останні повідомлення
- `/delete [on|off]` - Увімкнути/вимкнути автоматичне видалення повідомлень
- `/template <text>` - Додати шаблон повідомлення
- `/deltemplate <id>` - Видалити шаблон повідомлення
- `/templates` - Показати список шаблонів
- `/help [command]` - Показати довідку

## Структура проекту

```
curse-word-bot/
├── src/
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── database/
│   │   ├── __init__.py
│   │   └── db.py
│   ├── handlers/
│   │   ├── __init__.py
│   │   └── commands.py
│   ├── utils/
│   │   ├── __init__.py
│   │   └── logger.py
│   ├── __init__.py
│   └── main.py
├── logs/
├── .env
├── .env.example
├── requirements.txt
├── structure.sql
└── README.md
```

## Ліцензія

MIT 