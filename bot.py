import asyncio
import sqlite3
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# 🔑 ВСТАВЬ СЮДА ТОКЕН ОТ BOTFATHER
BOT_TOKEN = "8668380531:AAFoIHelKXYpDJ3-r-WrFHfXbd2WMvglTZo"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 🗄️ БАЗА ДАННЫХ
def init_db():
    conn = sqlite3.connect('astro.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            telegram_id INTEGER UNIQUE,
            username TEXT,
            zodiac_sign TEXT
        )
    ''')
    conn.commit()
    conn.close()

# ⌨️ КНОПКИ
def main_menu():
    kb = [
        [KeyboardButton(text="🔮 Гороскоп"), KeyboardButton(text="🃏 Карта дня")],
        [KeyboardButton(text="📊 Мой знак"), KeyboardButton(text="📞 Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def zodiac_kb():
    signs = ["♈ Овен", "♉ Телец", "♊ Близнецы", "♋ Рак", "♌ Лев", "♍ Дева",
             "♎ Весы", "♏ Скорпион", "♐ Стрелец", "♑ Козерог", "♒ Водолей", "♓ Рыбы"]
    kb = [[InlineKeyboardButton(text=s, callback_data=f"sign_{s}")] for s in signs]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# 🔮 ГОРОСКОП
async def get_horoscope_text(sign):
    predictions = {
        "♈ Овен": "Сегодня день побед! Но не перегри голову.",
        "♉ Телец": "Финансы в порядке, но меньше трать на еду.",
        "♊ Близнецы": "Болтай меньше, делай больше.",
        "♋ Рак": "Дома уютнее, чем на улице.",
        "♌ Лев": "Ты сегодня звезда, но не затми других.",
        "♍ Дева": "Наведи порядок в файлах на компьютере.",
        "♎ Весы": "Не принимай важных решений сегодня.",
        "♏ Скорпион": "Твоя интуиция врёт. Проверь факты.",
        "♐ Стрелец": "Время для путешествий или новой книги.",
        "♑ Козерог": "Работа не волк, но сегодня покусает.",
        "♒ Водолей": "Идея века придет вечером. Запиши!",
        "♓ Рыбы": "Плыви по течению, не сопротивляйся."
    }
    return predictions.get(sign, "Звезды молчат...")

# 🎯 ОБРАБОТЧИКИ
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    conn = sqlite3.connect('astro.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (telegram_id, username) VALUES (?, ?)', 
                       (message.from_user.id, message.from_user.username))
        conn.commit()
    except:
        pass
    conn.close()
    
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\nЯ твой карманный астролог.\nВыбери действие:",
        reply_markup=main_menu()
    )

@dp.message(F.text == "🔮 Гороскоп")
async def horoscope_menu(message: types.Message):
    await message.answer("Выбери свой знак зодиака 👇", reply_markup=zodiac_kb())

@dp.callback_query(F.data.startswith("sign_"))
async def show_horoscope(callback: types.CallbackQuery):
    sign = callback.data.replace("sign_", "")
    text = await get_horoscope_text(sign)
    
    conn = sqlite3.connect('astro.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET zodiac_sign = ? WHERE telegram_id = ?', (sign, callback.from_user.id))
    conn.commit()
    conn.close()
    
    await callback.message.answer(f"{sign}\n\n🔮 {text}")
    await callback.answer()

@dp.message(F.text == "🃏 Карта дня")
async def tarot_card(message: types.Message):
    cards = ["Шут 🃏", "Маг 🪄", "Жрица 🌙", "Императрица 👑", "Солнце ☀️"]
    card = random.choice(cards)
    await message.answer(f"Твоя карта дня: {card}\nЭто к удаче!")

@dp.message(F.text == "📊 Мой знак")
async def my_sign(message: types.Message):
    conn = sqlite3.connect('astro.db')
    cursor = conn.cursor()
    cursor.execute('SELECT zodiac_sign FROM users WHERE telegram_id = ?', (message.from_user.id,))
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0]:
        await message.answer(f"Твой сохранённый знак: {result[0]}")
    else:
        await message.answer("Ты ещё не выбрал знак. Нажми 'Гороскоп'.")

@dp.message(F.text == "📞 Помощь")
async def help_msg(message: types.Message):
    await message.answer("Если что-то сломалось — напиши разработчику.")

# 🚀 ЗАПУСК
async def main():
    import logging
    logging.basicConfig(level=logging.INFO)
    
    init_db()
    print("🚀 Бот запущен на Render!")
    
    # 🔧 Важно для Render: используем вебхуки или long-polling
    await dp.start_polling(bot)