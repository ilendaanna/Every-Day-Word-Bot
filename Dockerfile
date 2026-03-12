FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY bot/ ./bot/

# Run the bot
CMD ["python", "bot/word_bot.py"]
