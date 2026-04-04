import asyncio
import logging
import sys
import os
import sqlite3
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# 🔧 НАСТРОЙКА ЛОГОВ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# 🔑 ТОКЕН
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден!")
    sys.exit(1)

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
    logger.info("✅ База данных готова")

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
    logger.info(f"📨 /start от {message.from_user.id}")
    conn = sqlite3.connect('astro.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)', 
                       (message.from_user.id, message.from_user.username))
        conn.commit()
    except Exception as e:
        logger.error(f"❌ Ошибка БД: {e}")
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

# 🔧 ТЕСТ: эхо на все сообщения
@dp.message()
async def echo_all(message: types.Message):
    logger.info(f"📨 Сообщение: {message.text}")
    await message.answer("🔊 Я тебя слышу! (тест)")

# 🌐 ВЕБ-СЕРВЕР ДЛЯ RENDER (чтобы не убивал процесс)
async def handle_health(request):
    return web.Response(text="OK - Bot is alive! 🤖")

async def start_webserver(port):
    app = web.Application()
    app.add_routes([web.get('/', handle_health), web.get('/health', handle_health)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"🌐 Веб-сервер запущен на порту {port}")
    return runner

# 🚀 ГЛАВНАЯ ФУНКЦИЯ
async def main():
    logger.info("🚀 Запуск бота...")
    
    # Проверка токена
    try:
        me = await bot.me()
        logger.info(f"✅ Авторизован как @{me.username}")
    except Exception as e:
        logger.error(f"❌ Ошибка авторизации: {e}")
        return
    
    init_db()
    
    # 🔥 Запускаем веб-сервер для Render (порт из ENV или 10000 по умолчанию)
    port = int(os.getenv("PORT", 10000))
    web_runner = await start_webserver(port)
    
    # 🔥 Запускаем polling параллельно
    logger.info("🔄 Запускаем Telegram polling...")
    polling_task = asyncio.create_task(dp.start_polling(bot))
    
    # 🔥 Держим процесс живым: ждём либо остановки polling, либо сигнала от Render
    try:
        await polling_task
    except asyncio.CancelledError:
        logger.info("🛑 Polling остановлен")
    finally:
        await web_runner.cleanup()
        logger.info("🔚 Бот завершил работу")

# 🔥 ТОЧКА ВХОДА
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Остановка по Ctrl+C")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}", exc_info=True)
