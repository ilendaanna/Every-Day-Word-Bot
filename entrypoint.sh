#!/bin/sh

# Ожидание доступности базы данных (опционально, но полезно)
echo "Waiting for database..."

# Создаем таблицы через скрипт инициализации (самый быстрый способ для первого запуска)
python init_db.py

# Или через Alembic, если миграции уже сгенерированы
# alembic upgrade head

echo "Starting FastAPI and Bot..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
