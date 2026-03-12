import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from aiogram import Bot, Dispatcher
from app.core.config import settings
from app.bot.handlers import router as bot_router
from app.bot.middlewares import DbSessionMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=logging.INFO)

# Initialize Bot and Dispatcher
bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()
dp.include_router(bot_router)
dp.update.middleware(DbSessionMiddleware())

scheduler = AsyncIOScheduler()

async def send_daily_word():
    # This is a simplified version, ideally you'd iterate over users in DB
    # For now, we'll need a way to track which users want daily words.
    # In a real app, you'd query the 'users' table.
    pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start Bot
    logging.info("Starting bot...")
    asyncio.create_task(dp.start_polling(bot))
    
    # Start Scheduler
    scheduler.start()
    # Note: Adding jobs should be done here or via API
    
    yield
    
    # Shutdown
    logging.info("Shutting down...")
    await bot.session.close()
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "ok", "message": "EveryDayWordBot API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
