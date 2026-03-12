from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import User, SavedWord, Dictionary

async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int):
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalars().first()

async def create_user(db: AsyncSession, telegram_id: int):
    db_user = User(telegram_id=telegram_id)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

# Dictionary CRUD
async def create_dictionary(db: AsyncSession, telegram_id: int, name: str):
    user = await get_user_by_telegram_id(db, telegram_id)
    if not user: user = await create_user(db, telegram_id)
    db_dict = Dictionary(user_id=user.id, name=name)
    db.add(db_dict)
    await db.commit()
    await db.refresh(db_dict)
    return db_dict

async def get_dictionaries(db: AsyncSession, telegram_id: int):
    user = await get_user_by_telegram_id(db, telegram_id)
    if not user: return []
    result = await db.execute(select(Dictionary).where(Dictionary.user_id == user.id))
    return result.scalars().all()

async def delete_dictionary(db: AsyncSession, telegram_id: int, dict_id: int):
    user = await get_user_by_telegram_id(db, telegram_id)
    result = await db.execute(select(Dictionary).where(Dictionary.id == dict_id, Dictionary.user_id == user.id))
    db_dict = result.scalars().first()
    if db_dict:
        await db.delete(db_dict)
        await db.commit()
        return True
    return False

# Word Saving with Dictionary
async def save_word_to_dict(db: AsyncSession, telegram_id: int, word: str, definition: str, dict_id: int = None):
    user = await get_user_by_telegram_id(db, telegram_id)
    if not user: user = await create_user(db, telegram_id)
    
    # If dict_id is 0 or None, we can save to a default dictionary later, 
    # but for now we'll require one or save to 'General'
    if not dict_id:
        res = await db.execute(select(Dictionary).where(Dictionary.user_id == user.id, Dictionary.name == "General"))
        general_dict = res.scalars().first()
        if not general_dict:
            general_dict = await create_dictionary(db, telegram_id, "General")
        dict_id = general_dict.id

    db_word = SavedWord(user_id=user.id, dictionary_id=dict_id, word=word, definition=definition)
    db.add(db_word)
    await db.commit()
    await db.refresh(db_word)
    return db_word

async def get_words_by_dict(db: AsyncSession, dict_id: int):
    result = await db.execute(select(SavedWord).where(SavedWord.dictionary_id == dict_id))
    return result.scalars().all()

async def remove_saved_word(db: AsyncSession, word_id: int):
    result = await db.execute(select(SavedWord).where(SavedWord.id == word_id))
    db_word = result.scalars().first()
    if db_word:
        await db.delete(db_word)
        await db.commit()
        return True
    return False
