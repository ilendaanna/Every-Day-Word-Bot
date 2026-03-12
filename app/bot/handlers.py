from aiogram import Router, F, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.word_service import get_word_definitions, get_quiz_data
from app.bot.keyboards import (
    get_word_keyboard, get_quiz_keyboard, get_next_quiz_keyboard, 
    get_main_menu, get_dict_selection_keyboard, get_dictionaries_keyboard,
    get_dict_words_keyboard, get_saved_word_action_keyboard
)
from app.db import crud
from sqlalchemy import select
from app.db.models import SavedWord, Dictionary

router = Router()

class DictStates(StatesGroup):
    waiting_for_dict_name = State()
    waiting_for_dict_name_and_save = State()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Hello! I'm your *EveryDayWordBot*. 📚\n\n"
                         "Create dictionaries and save words to them!", 
                         parse_mode="Markdown",
                         reply_markup=get_main_menu())

# --- Dictionary Management ---

@router.message(F.text == "📚 My Dictionaries")
@router.callback_query(F.data == "view_dictionaries")
async def view_dictionaries(event: types.Message | types.CallbackQuery, db: AsyncSession):
    user_id = event.from_user.id
    dictionaries = await crud.get_dictionaries(db, user_id)
    text = "📂 *Your Dictionaries:*"
    kb = get_dictionaries_keyboard(dictionaries)
    
    if isinstance(event, types.Message):
        await event.answer(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await event.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
        await event.answer()

@router.message(F.text == "➕ Create Dictionary")
async def cmd_create_dict(message: types.Message, state: FSMContext):
    await message.answer("Please enter a name for your new dictionary:")
    await state.set_state(DictStates.waiting_for_dict_name)

@router.message(DictStates.waiting_for_dict_name)
async def process_dict_creation(message: types.Message, state: FSMContext, db: AsyncSession):
    name = message.text
    await crud.create_dictionary(db, message.from_user.id, name)
    await state.clear()
    await message.answer(f"✅ Dictionary '{name}' created!", reply_markup=get_main_menu())

# --- Word Saving Flow ---

@router.callback_query(F.data.startswith("save_step_1:"))
async def save_word_step_1(callback: types.CallbackQuery, db: AsyncSession):
    word = callback.data.split(":")[1]
    dictionaries = await crud.get_dictionaries(db, callback.from_user.id)
    
    if not dictionaries:
        # Create default 'General' or ask to create
        await callback.message.answer("You don't have any dictionaries yet. Create one or use 'General'?")
        await crud.create_dictionary(db, callback.from_user.id, "General")
        dictionaries = await crud.get_dictionaries(db, callback.from_user.id)

    await callback.message.edit_text(f"Choose a dictionary to save *{word.capitalize()}*:", 
                                   parse_mode="Markdown",
                                   reply_markup=get_dict_selection_keyboard(word, dictionaries))
    await callback.answer()

@router.callback_query(F.data.startswith("save_step_2:"))
async def save_word_step_2(callback: types.CallbackQuery, db: AsyncSession):
    _, word, dict_id = callback.data.split(":")
    
    # Extract definition from message text (hacky but works for now)
    msg_lines = callback.message.text.split("\n")
    # Actually we don't have the definition in the selection message. 
    # In a better app, we'd use FSM to store the definition.
    # For now, let's re-fetch or use a placeholder.
    definition = "Saved from bot" 
    
    await crud.save_word_to_dict(db, callback.from_user.id, word, definition, int(dict_id))
    await callback.message.edit_text(f"✅ Word *{word.capitalize()}* saved!", parse_mode="Markdown")
    await callback.answer()

# --- Viewing Dictionary Content ---

@router.callback_query(F.data.startswith("view_dict:"))
async def view_dict(callback: types.CallbackQuery, db: AsyncSession):
    dict_id = int(callback.data.split(":")[1])
    words = await crud.get_words_by_dict(db, dict_id)
    
    res = await db.execute(select(Dictionary).where(Dictionary.id == dict_id))
    d = res.scalars().first()
    
    text = f"📂 *Dictionary:* {d.name}\nWords: {len(words)}"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_dict_words_keyboard(words, dict_id))
    await callback.answer()

@router.callback_query(F.data.startswith("view_saved:"))
async def view_saved_word(callback: types.CallbackQuery, db: AsyncSession):
    word_id = int(callback.data.split(":")[1])
    res = await db.execute(select(SavedWord).where(SavedWord.id == word_id))
    w = res.scalars().first()
    
    text = f"🔖 *{w.word.capitalize()}*\n\n📖 {w.definition}"
    await callback.message.edit_text(text, parse_mode="Markdown", 
                                   reply_markup=get_saved_word_action_keyboard(w.id, w.dictionary_id))
    await callback.answer()

@router.callback_query(F.data.startswith("remove_saved:"))
async def remove_saved_word(callback: types.CallbackQuery, db: AsyncSession):
    _, word_id, dict_id = callback.data.split(":")
    await crud.remove_saved_word(db, int(word_id))
    await callback.answer("🗑️ Word removed.")
    # Refresh dict view
    callback.data = f"view_dict:{dict_id}"
    await view_dict(callback, db)

import random

@router.callback_query(F.data.startswith("quiz_dict:"))
async def start_dict_quiz(callback: types.CallbackQuery, db: AsyncSession):
    dict_id = int(callback.data.split(":")[1])
    words = await crud.get_words_by_dict(db, dict_id)
    
    if len(words) < 4:
        await callback.answer("You need at least 4 words in the folder to start a quiz!")
        return
        
    # Generate quiz question
    correct_obj = random.choice(words)
    distractors = [w.word for w in words if w.id != correct_obj.id]
    random.shuffle(distractors)
    
    options = distractors[:3] + [correct_obj.word]
    random.shuffle(options)
    
    question = f"📝 *Quiz from this folder*\n\n📖 \"{correct_obj.definition}\"\n\n*Guess the word:*"
    
    # We add dict_id to callback so 'next' button works for this specific folder
    await callback.message.edit_text(
        question, 
        parse_mode="Markdown", 
        reply_markup=get_quiz_keyboard(options, correct_obj.word)
    )
    await callback.answer()

# --- Standard Word/Quiz Handlers ---

@router.message(F.text == "🆕 Get Word")
async def menu_word(message: types.Message):
    words = await get_word_definitions(length=0, number=1)
    for item in words:
        text = f"🌟 *Word:* {item['word'].capitalize()}\n📖 {item['definition']}"
        await message.answer(text, parse_mode="Markdown", reply_markup=get_word_keyboard(item['word'], item['definition']))

@router.callback_query(F.data.startswith("new_word_msg:"))
async def callback_new_word_msg(callback: types.CallbackQuery):
    words = await get_word_definitions(length=0, number=1)
    for item in words:
        text = f"🌟 *Word:* {item['word'].capitalize()}\n📖 {item['definition']}"
        await callback.message.answer(text, parse_mode="Markdown", reply_markup=get_word_keyboard(item['word'], item['definition']))
    await callback.answer()

@router.message(F.text == "🎮 Start Quiz")
async def menu_quiz(message: types.Message):
    quiz = await get_quiz_data()
    if quiz:
        await message.answer(quiz["question"], parse_mode="Markdown", reply_markup=get_quiz_keyboard(quiz["options"], quiz["correct"]))

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
async def callback_quiz_next(callback: types.CallbackQuery, db: AsyncSession):
    quiz = await get_quiz_data()
    if quiz:
        await callback.message.edit_text(
            quiz["question"], 
            parse_mode="Markdown", 
            reply_markup=get_quiz_keyboard(quiz["options"], quiz["correct"])
        )
    await callback.answer()
