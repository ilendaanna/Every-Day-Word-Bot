import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine
from app.db.models import Base
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_db():
    logger.info(f"Connecting to database at {settings.DATABASE_URL.split('@')[1]}...")
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        logger.info("Creating all tables...")
        # This will create all tables defined in models.py
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Tables created successfully!")
    
    await engine.dispose()

if __name__ == "__main__":
    try:
        asyncio.run(init_db())
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
