from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_word_keyboard(word: str, definition: str, length: int = 0, number: int = 1):
    builder = InlineKeyboardBuilder()
    
    # Save button
    # We encode word in callback_data, but it might be long. 
    # For now, let's just use "save:{word}" and we'll handle definition separately or re-fetch.
    # Better: the handler already has the text.
    builder.row(types.InlineKeyboardButton(
        text="⭐ Save to Favorites", 
        callback_data=f"save_word:{word}"
    ))
    
    label = f"{length} letters" if length > 0 else "Random length"
    builder.row(types.InlineKeyboardButton(
        text=f"🔄 New Word ({label})", 
        callback_data=f"new_word:{length}:{number}"
    ))
    
    return builder.as_markup()

def get_quiz_keyboard(options, correct_word):
    builder = InlineKeyboardBuilder()
    for opt in options:
        builder.add(types.InlineKeyboardButton(
            text=opt.capitalize(), 
            callback_data=f"quiz:{opt}:{correct_word}"
        ))
    builder.adjust(2)
    return builder.as_markup()

def get_next_quiz_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="➡️ Next Question", callback_data="quiz_next"))
    return builder.as_markup()

def get_favorites_keyboard(words):
    builder = InlineKeyboardBuilder()
    for w in words:
        builder.row(types.InlineKeyboardButton(
            text=f"📖 {w.word.capitalize()}", 
            callback_data=f"view_saved:{w.id}"
        ))
    return builder.as_markup()

def get_saved_word_action_keyboard(word_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text="🗑️ Remove", 
        callback_data=f"remove_saved:{word_id}"
    ))
    builder.row(types.InlineKeyboardButton(
        text="⬅️ Back to List", 
        callback_data="back_to_favorites"
    ))
    return builder.as_markup()
