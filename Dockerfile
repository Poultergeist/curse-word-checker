FROM python:3.11-slim

# Встановлюємо робочу директорію
WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
 && rm -rf /var/lib/apt/lists/*

# Копіюємо requirements і встановлюємо залежності
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо весь код
COPY . .

# Встановлюємо перемінні середовища
ENV PYTHONUNBUFFERED=1

# Запускаємо бота
CMD ["python", "src/main.py"]
