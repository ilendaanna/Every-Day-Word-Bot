import os
import asyncio
import aiohttp
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Use environment variable for the token
TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    # Fallback to the hardcoded token if for some reason the env var is not set
    TOKEN = '8638491798:AAEoVdMbu1vOGphhKCzKj2X-yU56vao63j8'


def get_new_word_keyboard(length=0, number=1):
    # Use 0 as a flag for "Random length"
    label = f"{length} letters" if length > 0 else "Random length"
    buttons = [
        [types.InlineKeyboardButton(
            text=f"🔄 New Word ({label})", 
            callback_data=f"new_word:{length}:{number}"
        )]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


# --- Logic to fetch words ---
async def get_word_definitions(length=None, number=1):
    results = []
    attempts = 0
    max_attempts = 5  # Prevent infinite loops
    
    async with aiohttp.ClientSession() as session:
        while len(results) < number and attempts < max_attempts:
            attempts += 1
            # Fetch slightly more words than needed to increase chances of finding definitions
            needed = number - len(results)
            fetch_count = needed * 2 
            
            url = f"https://random-word-api.herokuapp.com/word?number={fetch_count}"
            if length and length > 0:
                url += f"&length={length}"
            
            # 1. Get random words
            async with session.get(url) as rw_response:
                if rw_response.status != 200:
                    break
                words = await rw_response.json()

            for word in words:
                if len(results) >= number:
                    break
                
                # 2. Get the definition for each word
                dict_url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
                async with session.get(dict_url) as d_response:
                    if d_response.status == 200:
                        data = await d_response.json()
                        try:
                            # Verify definition exists
                            definition = data[0]['meanings'][0]['definitions'][0]['definition']
                            label_len = f" ({len(word)} letters)"
                            results.append(f"🌟 *Word:* {word.capitalize()}{label_len}\n📖 {definition}")
                        except (IndexError, KeyError):
                            continue # Skip if no definition
                    else:
                        continue # Skip if word not in dictionary
        
    if not results:
        return "Could not find any words with definitions after several attempts. 😢"
        
    return "\n\n---\n\n".join(results)

# --- The Scheduled Task ---
async def send_daily_word(bot: Bot, chat_id: int):
    # Daily word now uses random length (None)
    text = await get_word_definitions(length=None, number=1)
    await bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=get_new_word_keyboard(0, 1))

# --- Quiz Logic ---
async def get_quiz_data(length=0):
    # Fetch more words to find a good mix
    url = f"https://random-word-api.herokuapp.com/word?number=10"
    if length > 0:
        url += f"&length={length}"
        
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                return None
            words = await response.json()
            
        # Find 1 word with a definition
        correct_word = None
        definition = None
        
        for word in words:
            dict_url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            async with session.get(dict_url) as d_response:
                if d_response.status == 200:
                    data = await d_response.json()
                    try:
                        definition = data[0]['meanings'][0]['definitions'][0]['definition']
                        correct_word = word
                        break
                    except (IndexError, KeyError):
                        continue
        
        if not correct_word:
            return None
            
        # Get 3 other unique words as distractors
        distractors = [w for w in words if w != correct_word][:3]
        if len(distractors) < 3:
            # Fallback if not enough words in first batch
            distractors += ["apple", "ocean", "cloud"]
            distractors = distractors[:3]
            
        options = distractors + [correct_word]
        random.shuffle(options)
        
        return {
            "question": f"❓ *Guess the word by its definition:*\n\n📖 \"{definition}\"",
            "correct": correct_word,
            "options": options
        }

def get_quiz_keyboard(options, correct_word):
    buttons = []
    # Create a grid of buttons (2x2)
    row = []
    for opt in options:
        # callback_data format: quiz:selected_word:correct_word
        row.append(types.InlineKeyboardButton(
            text=opt.capitalize(), 
            callback_data=f"quiz:{opt}:{correct_word}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
        
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

# --- Command Handlers ---
dp = Dispatcher()

@dp.message(Command("quiz"))
async def cmd_quiz(message: types.Message, command: CommandObject):
    length = 0
    if command.args:
        try:
            length = int(command.args.split()[0])
        except (ValueError, IndexError):
            pass
            
    loading_msg = await message.answer("⏳ Generating a quiz for you...")
    quiz = await get_quiz_data(length)
    
    if not quiz:
        await loading_msg.edit_text("❌ Could not generate a quiz. Try again!")
        return
        
    await loading_msg.delete()
    await message.answer(
        quiz["question"], 
        parse_mode="Markdown", 
        reply_markup=get_quiz_keyboard(quiz["options"], quiz["correct"])
    )

@dp.callback_query(F.data.startswith("quiz:"))
async def callback_quiz(callback: types.CallbackQuery):
    # data format: quiz:selected:correct
    _, selected, correct = callback.data.split(":")
    
    if selected == correct:
        text = f"✅ *Correct!*\n\nThe word was: *{correct.capitalize()}*"
    else:
        text = f"❌ *Wrong!*\n\nThe correct word was: *{correct.capitalize()}*\n(You picked: {selected})"
    
    # Add a "Next Question" button
    next_kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="➡️ Next Question", callback_data="quiz_next")]
    ])
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=next_kb)
    await callback.answer()

@dp.callback_query(F.data == "quiz_next")
async def callback_quiz_next(callback: types.CallbackQuery):
    await callback.answer("Loading next question...")
    quiz = await get_quiz_data() # Default random length
    
    if not quiz:
        await callback.message.edit_text("❌ Could not generate next question. Use /quiz to restart.")
        return
        
    await callback.message.edit_text(
        quiz["question"], 
        parse_mode="Markdown", 
        reply_markup=get_new_word_keyboard() if not quiz else get_quiz_keyboard(quiz["options"], quiz["correct"])
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message, scheduler: AsyncIOScheduler, bot: Bot):
    chat_id = message.chat.id
    
    scheduler.add_job(
        send_daily_word, 
        trigger="cron", 
        hour=9, 
        minute=0, 
        args=[bot, chat_id],
        id=f"daily_{chat_id}",
        replace_existing=True
    )
    
    await message.answer("Registered! You'll get a word (random length) every morning at 9:00 AM.\n\n"
                         "Try: `/word` for a random word\n"
                         "Try: `/word 5` for a 5-letter word\n"
                         "Or: `/word 0 3` for three words with random lengths!", parse_mode="Markdown")

@dp.message(Command("word"))
async def cmd_word(message: types.Message, command: CommandObject):
    length = 0 # Default to random
    number = 1
    
    if command.args:
        args = command.args.split()
        try:
            length = int(args[0])
            if len(args) > 1:
                number = min(int(args[1]), 5)
        except (ValueError, IndexError):
            pass

    text = await get_word_definitions(length=length, number=number)
    await message.answer(text, parse_mode="Markdown", reply_markup=get_new_word_keyboard(length, number))

@dp.callback_query(F.data.startswith("new_word:"))
async def callback_new_word(callback: types.CallbackQuery):
    _, length, number = callback.data.split(":")
    length = int(length)
    number = int(number)
    
    text = await get_word_definitions(length=length, number=number)
    
    if callback.message.text == text:
        await callback.answer("Generated the same content, try again!")
        return
        
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_new_word_keyboard(length, number))
    await callback.answer()

# --- Main Startup ---
async def main():
    bot = Bot(token=TOKEN)
    scheduler = AsyncIOScheduler()
    
    # Start the scheduler
    scheduler.start()
    
    # Pass the scheduler to handlers via dependency injection
    print("Bot is starting...")
    await dp.start_polling(bot, scheduler=scheduler)

if __name__ == "__main__":
    asyncio.run(main())