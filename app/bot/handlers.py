from aiogram import Router, F, types, Bot
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
import random
import aiohttp

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

class WordStates(StatesGroup):
    waiting_for_dict_selection = State()
    waiting_for_dict_name = State()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Hello! I'm your *EveryDayWordBot*. 📚\n\n"
                         "Create dictionaries, save words, and practice them!", 
                         parse_mode="Markdown",
                         reply_markup=get_main_menu())

# --- Dictionaries ---

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
    await state.set_state(WordStates.waiting_for_dict_name)

@router.message(WordStates.waiting_for_dict_name)
async def process_dict_creation(message: types.Message, state: FSMContext, db: AsyncSession):
    name = message.text
    await crud.create_dictionary(db, message.from_user.id, name)
    await state.clear()
    await message.answer(f"✅ Dictionary '{name}' created!", reply_markup=get_main_menu())

@router.callback_query(F.data.startswith("view_dict:"))
async def view_dict(callback: types.CallbackQuery, db: AsyncSession):
    dict_id = int(callback.data.split(":")[1])
    words = await crud.get_words_by_dict(db, dict_id)
    res = await db.execute(select(Dictionary).where(Dictionary.id == dict_id))
    d = res.scalars().first()
    
    if not d:
        await callback.answer("Dictionary not found.")
        return
        
    text = f"📂 *Dictionary:* {d.name}\nWords: {len(words)}"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_dict_words_keyboard(words, dict_id))
    await callback.answer()

# --- Word Saving Flow with FSM to keep definition ---

@router.callback_query(F.data.startswith("save_step_1:"))
async def save_word_step_1(callback: types.CallbackQuery, db: AsyncSession, state: FSMContext):
    word = callback.data.split(":")[1]
    
    # Пытаемся максимально надежно достать определение
    msg_text = callback.message.text or callback.message.caption or ""
    definition = "No definition found"
    
    if "📖" in msg_text:
        # Берем всё, что после значка книги
        parts = msg_text.split("📖")
        if len(parts) > 1:
            definition = parts[1].strip()
            # Убираем лишние кнопки или служебную инфу, если она была в конце
            definition = definition.split("\n---")[0].strip()

    await state.update_data(word=word, definition=definition)
    
    dictionaries = await crud.get_dictionaries(db, callback.from_user.id)
    if not dictionaries:
        await crud.create_dictionary(db, callback.from_user.id, "General")
        dictionaries = await crud.get_dictionaries(db, callback.from_user.id)

    await callback.message.edit_text(f"Choose a dictionary for *{word.capitalize()}*:", 
                                   parse_mode="Markdown",
                                   reply_markup=get_dict_selection_keyboard(word, dictionaries))
    await callback.answer()

@router.callback_query(F.data.startswith("save_step_2:"))
async def save_word_step_2(callback: types.CallbackQuery, db: AsyncSession, state: FSMContext):
    data = callback.data.split(":")
    dict_id = int(data[2])
    
    user_data = await state.get_data()
    word = user_data.get("word")
    definition = user_data.get("definition")
    
    if not word or not definition or definition == "No definition found":
        # Если FSM пуст, попробуем восстановить из текста (на всякий случай)
        word = data[1]
        definition = "Manual save (definition lost)"

    await crud.save_word_to_dict(db, callback.from_user.id, word, definition, dict_id)
    await state.clear()
    await callback.message.edit_text(f"✅ Saved *{word.capitalize()}* to dictionary!", parse_mode="Markdown")
    await callback.answer()

# --- FOLDER QUIZ LOGIC ---

@router.callback_query(F.data.startswith("quiz_dict:"))
async def start_dict_quiz(callback: types.CallbackQuery, db: AsyncSession):
    dict_id = int(callback.data.split(":")[1])
    words = await crud.get_words_by_dict(db, dict_id)
    
    if len(words) < 2:
        await callback.answer("Add at least 2 words to start a quiz!")
        return
        
    correct_obj = random.choice(words)
    distractor_pool = [w.word for w in words if w.id != correct_obj.id]
    
    if len(distractor_pool) < 3:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://random-word-api.herokuapp.com/word?number=5") as resp:
                if resp.status == 200:
                    api_words = await resp.json()
                    distractor_pool.extend(api_words)

    random.shuffle(distractor_pool)
    options = distractor_pool[:3] + [correct_obj.word]
    random.shuffle(options)
    
    # Используем сохраненное определение!
    text = f"📝 *Folder Quiz*\n\n📖 \"{correct_obj.definition}\"\n\n*Guess the word:*"
    await callback.message.edit_text(text, parse_mode="Markdown", 
                                   reply_markup=get_quiz_keyboard(options, correct_obj.word, dict_id))
    await callback.answer()

@router.callback_query(F.data.startswith("quiz_ans:"))
async def callback_quiz_answer(callback: types.CallbackQuery):
    _, selected, correct, dict_id = callback.data.split(":")
    dict_id = int(dict_id)
    
    if selected == correct:
        text = f"✅ *Correct!*\n\nThe word was: *{correct.capitalize()}*"
    else:
        text = f"❌ *Wrong!*\n\nThe correct word was: *{correct.capitalize()}*"
    
    await callback.message.edit_text(text, parse_mode="Markdown", 
                                   reply_markup=get_next_quiz_keyboard(dict_id))
    await callback.answer()

# --- Global Handlers ---

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
@router.callback_query(F.data == "quiz_next")
async def menu_quiz(event: types.Message | types.CallbackQuery):
    quiz = await get_quiz_data()
    if quiz:
        text = f"🌟 *Global Quiz*\n\n{quiz['question']}"
        if isinstance(event, types.Message):
            await event.answer(text, parse_mode="Markdown", reply_markup=get_quiz_keyboard(quiz["options"], quiz["correct"]))
        else:
            await event.message.edit_text(text, parse_mode="Markdown", reply_markup=get_quiz_keyboard(quiz["options"], quiz["correct"]))
            await event.answer()

@router.callback_query(F.data.startswith("view_saved:"))
async def callback_view_saved(callback: types.CallbackQuery, db: AsyncSession):
    word_id = int(callback.data.split(":")[1])
    res = await db.execute(select(SavedWord).where(SavedWord.id == word_id))
    w = res.scalars().first()
    if not w: return
    text = f"🔖 *{w.word.capitalize()}*\n\n📖 {w.definition}"
    await callback.message.edit_text(text, parse_mode="Markdown", 
                                   reply_markup=get_saved_word_action_keyboard(w.id, w.dictionary_id))
    await callback.answer()

@router.callback_query(F.data.startswith("remove_saved:"))
async def callback_remove_saved(callback: types.CallbackQuery, db: AsyncSession):
    _, word_id, dict_id = callback.data.split(":")
    await crud.remove_saved_word(db, int(word_id))
    await callback.answer("🗑️ Removed.")
    # Return to dict view
    words = await crud.get_words_by_dict(db, int(dict_id))
    await callback.message.edit_text(f"Words in dictionary:", reply_markup=get_dict_words_keyboard(words, int(dict_id)))
