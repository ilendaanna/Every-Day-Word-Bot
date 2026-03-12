FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей для сборки, если понадобятся
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Делаем скрипт запуска исполняемым
RUN chmod +x entrypoint.sh

# Используем entrypoint для запуска
ENTRYPOINT ["./entrypoint.sh"]
