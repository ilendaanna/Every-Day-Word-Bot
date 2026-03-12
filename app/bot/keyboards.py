from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

def get_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🆕 Get Word"), types.KeyboardButton(text="🎮 Start Quiz"))
    builder.row(types.KeyboardButton(text="📚 My Dictionaries"), types.KeyboardButton(text="➕ Create Dictionary"))
    return builder.as_markup(resize_keyboard=True)

def get_word_keyboard(word: str, definition: str, length: int = 0, number: int = 1):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="⭐ Save", callback_data=f"save_step_1:{word}"))
    label = f"{length} letters" if length > 0 else "Random"
    builder.row(types.InlineKeyboardButton(text=f"🔄 Another ({label})", callback_data=f"new_word_msg:{length}:{number}"))
    return builder.as_markup()

def get_dict_selection_keyboard(word: str, dictionaries):
    builder = InlineKeyboardBuilder()
    for d in dictionaries:
        builder.row(types.InlineKeyboardButton(text=f"📁 {d.name}", callback_data=f"save_step_2:{word}:{d.id}"))
    builder.row(types.InlineKeyboardButton(text="➕ New Dictionary", callback_data=f"create_dict_and_save:{word}"))
    return builder.as_markup()

def get_dictionaries_keyboard(dictionaries):
    builder = InlineKeyboardBuilder()
    for d in dictionaries:
        builder.row(
            types.InlineKeyboardButton(text=f"📂 {d.name}", callback_data=f"view_dict:{d.id}"),
            types.InlineKeyboardButton(text="🗑️", callback_data=f"delete_dict_confirm:{d.id}")
        )
    return builder.as_markup()

def get_dict_words_keyboard(words, dict_id):
    builder = InlineKeyboardBuilder()
    # Квиз можно начать, если есть хотя бы 2 слова (остальные подмешаем)
    if len(words) >= 2:
        builder.row(types.InlineKeyboardButton(text="📝 Start Quiz (this folder)", callback_data=f"quiz_dict:{dict_id}"))
    for w in words:
        builder.row(types.InlineKeyboardButton(text=f"📖 {w.word.capitalize()}", callback_data=f"view_saved:{w.id}"))
    builder.row(types.InlineKeyboardButton(text="⬅️ Back", callback_data="view_dictionaries"))
    return builder.as_markup()

def get_saved_word_action_keyboard(word_id: int, dict_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🗑️ Remove Word", callback_data=f"remove_saved:{word_id}:{dict_id}"))
    builder.row(types.InlineKeyboardButton(text="⬅️ Back to Dictionary", callback_data=f"view_dict:{dict_id}"))
    return builder.as_markup()

def get_quiz_keyboard(options, correct_word, dict_id: int = 0):
    builder = InlineKeyboardBuilder()
    for opt in options:
        # Добавляем dict_id в callback, чтобы знать, какой это квиз
        builder.add(types.InlineKeyboardButton(
            text=opt.capitalize(), 
            callback_data=f"quiz_ans:{opt}:{correct_word}:{dict_id}"
        ))
    builder.adjust(2)
    return builder.as_markup()

def get_next_quiz_keyboard(dict_id: int = 0):
    builder = InlineKeyboardBuilder()
    # Если dict_id > 0, кнопка Next снова вызовет квиз по этой папке
    cb = f"quiz_dict:{dict_id}" if dict_id > 0 else "quiz_next"
    builder.row(types.InlineKeyboardButton(text="➡️ Next Question", callback_data=cb))
    if dict_id > 0:
        builder.row(types.InlineKeyboardButton(text="⬅️ Back to Folder", callback_data=f"view_dict:{dict_id}"))
    return builder.as_markup()
