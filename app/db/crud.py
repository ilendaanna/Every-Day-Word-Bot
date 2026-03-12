from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import User, SavedWord

async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int):
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalars().first()

async def create_user(db: AsyncSession, telegram_id: int):
    db_user = User(telegram_id=telegram_id)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def save_word(db: AsyncSession, telegram_id: int, word: str, definition: str):
    user = await get_user_by_telegram_id(db, telegram_id)
    if not user:
        user = await create_user(db, telegram_id)
    
    # Check if word already saved
    existing = await db.execute(
        select(SavedWord).where(SavedWord.user_id == user.id, SavedWord.word == word)
    )
    if existing.scalars().first():
        return None
    
    db_word = SavedWord(user_id=user.id, word=word, definition=definition)
    db.add(db_word)
    await db.commit()
    await db.refresh(db_word)
    return db_word

async def get_saved_words(db: AsyncSession, telegram_id: int):
    user = await get_user_by_telegram_id(db, telegram_id)
    if not user:
        return []
    result = await db.execute(
        select(SavedWord).where(SavedWord.user_id == user.id).order_by(SavedWord.created_at.desc())
    )
    return result.scalars().all()

async def remove_saved_word(db: AsyncSession, telegram_id: int, word_id: int):
    user = await get_user_by_telegram_id(db, telegram_id)
    if not user:
        return False
    
    result = await db.execute(
        select(SavedWord).where(SavedWord.id == word_id, SavedWord.user_id == user.id)
    )
    db_word = result.scalars().first()
    if db_word:
        await db.delete(db_word)
        await db.commit()
        return True
    return False
