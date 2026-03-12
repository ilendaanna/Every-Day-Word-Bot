import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8638491798:AAEoVdMbu1vOGphhKCzKj2X-yU56vao63j8")
    # Using asyncpg for async connection
    DATABASE_URL: str = "postgresql+asyncpg://postgres:dp7uyowlxrbw6asf@144.91.122.10:5430/postgres"
    
    class Config:
        env_file = ".env"

settings = Settings()
