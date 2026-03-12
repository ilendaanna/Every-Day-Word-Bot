from aiogram import Router, F, types, Bot
from aiogram.filters import Command, CommandObject
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.word_service import get_word_definitions, get_quiz_data
from app.bot.keyboards import (
    get_word_keyboard, get_quiz_keyboard, get_next_quiz_keyboard, 
    get_favorites_keyboard, get_saved_word_action_keyboard
)
from app.db import crud

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Hello! I'm your EveryDayWordBot.\n\n"
                         "Commands:\n"
                         "/word - Get a random word\n"
                         "/quiz - Start a mini-quiz\n"
                         "/favorites - See your saved words\n", 
                         parse_mode="Markdown")

@router.message(Command("word"))
async def cmd_word(message: types.Message, command: CommandObject):
    length = 0
    number = 1
    if command.args:
        args = command.args.split()
        try:
            length = int(args[0])
            if len(args) > 1:
                number = min(int(args[1]), 5)
        except (ValueError, IndexError):
            pass

    words = await get_word_definitions(length=length, number=number)
    if not words:
        await message.answer("❌ Could not find words. Try again.")
        return

    for item in words:
        text = f"🌟 *Word:* {item['word'].capitalize()} ({item['length']} letters)\n📖 {item['definition']}"
        await message.answer(
            text, 
            parse_mode="Markdown", 
            reply_markup=get_word_keyboard(item['word'], item['definition'], length, number)
        )

@router.callback_query(F.data.startswith("new_word:"))
async def callback_new_word(callback: types.CallbackQuery):
    _, length, number = callback.data.split(":")
    length, number = int(length), int(number)
    
    words = await get_word_definitions(length=length, number=number)
    if not words:
        await callback.answer("❌ Error fetching words")
        return
        
    item = words[0] # Just update one
    text = f"🌟 *Word:* {item['word'].capitalize()} ({item['length']} letters)\n📖 {item['definition']}"
    
    await callback.message.edit_text(
        text, 
        parse_mode="Markdown", 
        reply_markup=get_word_keyboard(item['word'], item['definition'], length, number)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("save_word:"))
async def callback_save_word(callback: types.CallbackQuery, db: AsyncSession):
    word_text = callback.data.split(":")[1]
    
    # We need definition. We can extract it from the message text
    # The message text is: 🌟 Word: ... \n📖 [Definition]
    msg_lines = callback.message.text.split("\n")
    definition = msg_lines[1].replace("📖 ", "") if len(msg_lines) > 1 else "No definition"

    saved = await crud.save_word(db, callback.from_user.id, word_text, definition)
    if saved:
        await callback.answer(f"✅ Saved '{word_text}' to favorites!")
    else:
        await callback.answer("⚠️ Already in your favorites.")

@router.message(Command("favorites"))
async def cmd_favorites(message: types.Message, db: AsyncSession):
    words = await crud.get_saved_words(db, message.from_user.id)
    if not words:
        await message.answer("Your favorites list is empty. Use ⭐ button to save words!")
        return
    
    await message.answer("⭐ *Your Saved Words:*", 
                         parse_mode="Markdown", 
                         reply_markup=get_favorites_keyboard(words))

@router.callback_query(F.data == "back_to_favorites")
async def callback_back_to_favorites(callback: types.CallbackQuery, db: AsyncSession):
    words = await crud.get_saved_words(db, callback.from_user.id)
    await callback.message.edit_text("⭐ *Your Saved Words:*", 
                                   parse_mode="Markdown", 
                                   reply_markup=get_favorites_keyboard(words))
    await callback.answer()

@router.callback_query(F.data.startswith("view_saved:"))
async def callback_view_saved(callback: types.CallbackQuery, db: AsyncSession):
    word_id = int(callback.data.split(":")[1])
    # Fetch word details
    # Need to add get_saved_word_by_id in crud
    # For now, let's just use the query
    from sqlalchemy import select
    from app.db.models import SavedWord
    res = await db.execute(select(SavedWord).where(SavedWord.id == word_id))
    w = res.scalars().first()
    
    if not w:
        await callback.answer("Word not found.")
        return
        
    text = f"🔖 *{w.word.capitalize()}*\n\n📖 {w.definition}\n\n📅 Saved: {w.created_at.strftime('%Y-%m-%d')}"
    await callback.message.edit_text(text, parse_mode="Markdown", 
                                   reply_markup=get_saved_word_action_keyboard(w.id))
    await callback.answer()

@router.callback_query(F.data.startswith("remove_saved:"))
async def callback_remove_saved(callback: types.CallbackQuery, db: AsyncSession):
    word_id = int(callback.data.split(":")[1])
    removed = await crud.remove_saved_word(db, callback.from_user.id, word_id)
    if removed:
        await callback.answer("🗑️ Removed from favorites.")
        # Go back to list
        words = await crud.get_saved_words(db, callback.from_user.id)
        if not words:
            await callback.message.edit_text("Your favorites list is now empty.")
        else:
            await callback.message.edit_text("⭐ *Your Saved Words:*", 
                                           parse_mode="Markdown", 
                                           reply_markup=get_favorites_keyboard(words))
    else:
        await callback.answer("❌ Error removing word.")

@router.message(Command("quiz"))
async def cmd_quiz(message: types.Message, command: CommandObject):
    length = 0
    if command.args:
        try:
            length = int(command.args.split()[0])
        except (ValueError, IndexError):
            pass
            
    loading_msg = await message.answer("⏳ Generating a quiz...")
    quiz = await get_quiz_data(length)
    await loading_msg.delete()
    
    if not quiz:
        await message.answer("❌ Could not generate quiz.")
        return
        
    await message.answer(
        quiz["question"], 
        parse_mode="Markdown", 
        reply_markup=get_quiz_keyboard(quiz["options"], quiz["correct"])
    )

@router.callback_query(F.data.startswith("quiz:"))
async def callback_quiz(callback: types.CallbackQuery):
    _, selected, correct = callback.data.split(":")
    
    if selected == correct:
        text = f"✅ *Correct!*\n\nThe word was: *{correct.capitalize()}*"
    else:
        text = f"❌ *Wrong!*\n\nThe correct word was: *{correct.capitalize()}*"
    
    await callback.message.edit_text(text, parse_mode="Markdown", 
                                   reply_markup=get_next_quiz_keyboard())
    await callback.answer()

@router.callback_query(F.data == "quiz_next")
async def callback_quiz_next(callback: types.CallbackQuery):
    quiz = await get_quiz_data()
    if not quiz:
        await callback.message.edit_text("❌ Error. Use /quiz.")
        return
        
    await callback.message.edit_text(
        quiz["question"], 
        parse_mode="Markdown", 
        reply_markup=get_quiz_keyboard(quiz["options"], quiz["correct"])
    )
    await callback.answer()
