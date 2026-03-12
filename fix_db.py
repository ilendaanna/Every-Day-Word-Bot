import asyncio
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_db():
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.begin() as conn:
        logger.info("Adding dictionary_id column to saved_words...")
        try:
            # Добавляем колонку и связываем её с таблицей dictionaries
            await conn.execute(text("ALTER TABLE saved_words ADD COLUMN IF NOT EXISTS dictionary_id INTEGER REFERENCES dictionaries(id) ON DELETE CASCADE"))
            logger.info("Column added successfully!")
        except Exception as e:
            logger.error(f"Error: {e}")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix_db())
