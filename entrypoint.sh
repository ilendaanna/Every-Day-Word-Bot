#!/bin/sh

echo "Waiting for database..."

# Применяем любые изменения через наш быстрый мигратор
python init_db.py
python fix_db.py

echo "Starting FastAPI and Bot..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
