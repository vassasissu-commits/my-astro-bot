import asyncio
import logging
import sys
import os
import sqlite3
import random
import math
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiohttp import web

# 🔧 ЛОГИРОВАНИЕ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# 🔑 КОНФИГ
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден в переменных окружения!")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 🗄️ БАЗА ДАННЫХ
DB_PATH = "astro.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, telegram_id INTEGER UNIQUE,
        username TEXT, first_name TEXT, birth_date TEXT,
        birth_time TEXT, birth_place TEXT, zodiac_sign TEXT,
        is_premium INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

async def get_user(tid):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id=?", (tid,))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None

async def add_user(tid, uname, fname):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (telegram_id, username, first_name) VALUES (?,?,?)",
              (tid, uname, fname))
    conn.commit()
    conn.close()

async def update_user(tid, **kwargs):
    if not kwargs: return
    set_clause = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [tid]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"UPDATE users SET {set_clause} WHERE telegram_id=?", vals)
    conn.commit()
    conn.close()

async def set_premium(tid, status: bool):
    await update_user(tid, is_premium=1 if status else 0)

# 🔒 ДЕКОРАТОР ПРОВЕРКИ PREMIUM
def premium_required(func):
    async def wrapper(message: types.Message, state: FSMContext = None, *args, **kwargs):
        user = await get_user(message.from_user.id)
        if not user or not user.get("is_premium"):
            await message.answer(
                "💎 Эта функция доступна только в Premium.\n\n"
                "Преимущества Premium:\n"
                "📊 Полная натальная карта\n"
                "💕 Детальная совместимость по датам\n"
                "🌌 Прогноз транзитов планет\n"
                "🔮 Персональные рекомендации\n\n"
                "Для активации напиши админу или используй /premium",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="👤 Написать админу", url="https://t.me/ТВОЙ_НИК")
                ]])
            )
            return
        return await func(message, state, *args, **kwargs)
    return wrapper

# ⌨️ КЛАВИАТУРЫ
def main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🔮 Гороскоп"), KeyboardButton(text="🌙 Луна")],
        [KeyboardButton(text="🎱 Магический шар"), KeyboardButton(text="💕 Совместимость")],
        [KeyboardButton(text="💎 Premium"), KeyboardButton(text="📊 Мой профиль")]
    ], resize_keyboard=True)

def zodiac_inline():
    signs = ["♈ Овен", "♉ Телец", "♊ Близнецы", "♋ Рак", "♌ Лев", "♍ Дева",
             "♎ Весы", "♏ Скорпион", "♐ Стрелец", "♑ Козерог", "♒ Водолей", "♓ Рыбы"]
    kb = [[InlineKeyboardButton(text=s, callback_data=f"sign_{s}")] for s in signs]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# 🌍 БЕСПЛАТНЫЕ API & РАСЧЁТЫ
STOICHIOMETRY = {"♈ Овен": "fire", "♉ Телец": "earth", "♊ Близнецы": "air", "♋ Рак": "water",
                 "♌ Лев": "fire", "♍ Дева": "earth", "♎ Весы": "air", "♏ Скорпион": "water",
                 "♐ Стрелец": "fire", "♑ Козерог": "earth", "♒ Водолей": "air", "♓ Рыбы": "water"}

COMPAT = {
    "fire": {"fire": "🔥🔥 Страсть и энергия!", "air": "💨🔥 Вдохновение и лёгкость", "water": "💧🔥 Пар и конфликты", "earth": "🌍🔥 Тормозит огонь"},
    "earth": {"earth": "🌍🌍 Стабильность и надёжность", "water": "💧🌍 Плодородие и рост", "fire": "🔥🌍 Огонь сушит землю", "air": "💨🌍 Пыль и ветер"},
    "air": {"air": "💨💨 Интеллект и идеи", "fire": "🔥💨 Ветер раздувает пламя", "earth": "🌍💨 Ветер уносит землю", "water": "💧💨 Туман и неясность"},
    "water": {"water": "💧💧 Глубина и эмпатия", "earth": "🌍💧 Увлажнение и рост", "fire": "🔥💧 Испарение и стресс", "air": "💨💧 Волны и переменчивость"}
}

async def get_aztro_horoscope(sign):
    try:
        url = f"https://aztro.sameerkumar.website/?sign={sign.replace(' ', '_').lower()}&lang=ru"
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=10) as r:
                data = await r.json()
                return f"🔮 {data.get('horoscope', 'Звёзды молчат...')}\n🍀 Цвет: {data.get('color','?')} | ⏰ Время: {data.get('lucky_time','?')}"
    except:
        return "🌌 Сервис временно недоступен. Попробуй позже!"

def get_moon_phase():
    # Расчёт фазы луны (алгоритм на основе known new moon: 6.01.2000)
    known = datetime(2000, 1, 6, 18, 14)
    synodic = 29.53058867
    days = (datetime.now() - known).total_seconds() / 86400
    phase = days % synodic
    age = int(phase) + 1
    if phase < 1.84566: return "🌑 Новолуние", 1
    elif phase < 5.53699: return "🌓 Растущий серп", int(phase/1.84566)+1
    elif phase < 9.22831: return "🌗 Первая четверть", int((phase-5.53699)/1.84566)+8
    elif phase < 12.91963: return "🌔 Растущая луна", int((phase-9.22831)/1.84563)+15
    elif phase < 16.61096: return "🌕 Полнолуние", int((phase-12.91963)/1.84563)+16
    elif phase < 20.30228: return "🌖 Убывающая луна", int((phase-16.61096)/1.84563)+17
    elif phase < 23.99361: return "🌘 Последняя четверть", int((phase-20.30228)/1.84563)+23
    else: return "🌒 Убывающий серп", int((phase-23.99361)/1.84563)+24

def get_astro_tip():
    tips = [
        "🌿 Луна в знаке Земли: время для планирования бюджета.",
        "⚡ Меркурий активен: не отправляй важные сообщения после 22:00.",
        "🌊 Ретроградный период: перепроверяй билеты и документы.",
        "☀️ Солнечный аспект: отличное время для начала новых проектов.",
        "🌙 Лунный день: посвяти его очищению пространства и мыслей.",
        "🔮 Венера в гармонии: день для свиданий и творческих задач."
    ]
    return random.choice(tips)

# 🎯 FSM ДЛЯ ПРОФИЛЯ
class ProfileState(StatesGroup):
    date = State()
    time = State()
    place = State()

# 🧩 ОБРАБОТЧИКИ
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(
        f"🌟 Привет, {message.from_user.first_name}!\n"
        "Я твой астрологический компас. Бесплатно: гороскопы, луна, совместимость.\n"
        "💎 Premium: натальные карты, транзиты, персональные прогнозы.\n"
        "Выбери действие:",
        reply_markup=main_kb()
    )

@dp.message(Command("profile"))
@dp.message(F.text == "📊 Мой профиль")
async def cmd_profile(message: types.Message):
    u = await get_user(message.from_user.id)
    if not u: return
    prem = "💎 Да" if u["is_premium"] else "🆓 Нет"
    bd = u["birth_date"] or "Не указано"
    sign = u["zodiac_sign"] or "Не выбран"
    await message.answer(f"👤 {u['first_name']}\n♐ Знак: {sign}\n📅 Дата: {bd}\n💎 Premium: {prem}")

@dp.message(F.text == "🔮 Гороскоп")
async def horoscope_menu(message: types.Message):
    await message.answer("Выбери знак 👇", reply_markup=zodiac_inline())

@dp.callback_query(F.data.startswith("sign_"))
async def show_horoscope(cb: types.CallbackQuery):
    sign = cb.data.replace("sign_", "")
    text = await get_aztro_horoscope(sign)
    await update_user(cb.from_user.id, zodiac_sign=sign)
    await cb.message.answer(f"{sign}\n{text}")
    await cb.answer()

@dp.message(F.text == "🌙 Луна")
async def cmd_moon(message: types.Message):
    phase, day = get_moon_phase()
    rec = "🌱 Начинать дела" if "Растущ" in phase else "🔄 Завершать дела" if "Убыв" in phase else "⚡ Действовать интуитивно"
    await message.answer(f"🌙 Фаза: {phase}\n📅 Лунный день: {day}\n💡 Рекомендация: {rec}\n\n{get_astro_tip()}")

@dp.message(F.text == "🎱 Магический шар")
async def cmd_orb(message: types.Message):
    answers = [
        "🌟 Звёзды говорят: ДА", "🌙 Луна шепчет: ПОДОЖДИ", "🌍 Земля советует: ПРОВЕРЬ",
        "💨 Ветер дует: НЕТ", "🔥 Огонь горит: СЕЙЧАС!", "💧 Вода течёт: ДОВЕРЬСЯ ИНТУИЦИИ",
        "🌌 Космос молчит: СПРОСИ ПОЗЖЕ", "✨ Судьба решила: ТОЧНО ДА"
    ]
    await message.answer(f"🎱 {random.choice(answers)}")

@dp.message(F.text == "💕 Совместимость")
async def cmd_compat(message: types.Message):
    await message.answer("Напиши имя партнёра и его знак зодиака.\nПример: `Аня ♌ Лев`")

@dp.message(F.text.contains("♈") | F.text.contains("♉") | F.text.contains("♊") | F.text.contains("♋") | F.text.contains("♌") | F.text.contains("♍") | F.text.contains("♎") | F.text.contains("♏") | F.text.contains("♐") | F.text.contains("♑") | F.text.contains("♒") | F.text.contains("♓"))
async def calc_compat(message: types.Message):
    text = message.text.strip()
    # Извлекаем знак
    sign = next((s for s in STOICHIOMETRY if s in text), None)
    if not sign:
        return await message.answer("🔍 Не удалось найти знак. Напиши, например: `Аня ♌ Лев`")
    
    user = await get_user(message.from_user.id)
    if not user or not user.get("zodiac_sign"):
        return await message.answer("❓ Сначала узнай свой знак в разделе 🔮 Гороскоп!")
    
    my_el = STOICHIOMETRY[user["zodiac_sign"]]
    their_el = STOICHIOMETRY[sign]
    result = COMPAT[my_el][their_el]
    
    await message.answer(f"💕 {user['first_name']} ({user['zodiac_sign']}) + {text.split()[0]} ({sign})\n\n{result}\n\n💡 Это упрощённый расчёт по стихиям. Для детального анализа по датам нужен Premium.")

# 💎 PREMIUM ФУНКЦИИ
@dp.message(F.text == "💎 Premium")
async def cmd_premium(message: types.Message):
    await message.answer(
        "💎 **Premium возможности:**\n"
        "📊 Полная натальная карта (планеты, дома, аспекты)\n"
        "💕 Детальная совместимость по точным датам и городам\n"
        "🌌 Ежемесячный прогноз транзитов\n"
        "🔮 Персональные рекомендации без рекламы\n"
        "⚡ Приоритетная поддержка\n\n"
        "💰 Стоимость: 299₽/мес\n"
        "📩 Для активации напиши: `/buy` или свяжись с админом",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🛒 Купить Premium", callback_data="buy_premium")
        ]])
    )

@dp.callback_query(F.data == "buy_premium")
async def buy_premium(cb: types.CallbackQuery):
    await cb.message.answer("📩 Для оплаты и активации напиши админу: @ТВОЙ_НИК\nПосле подтверждения бот автоматически обновит твой статус.")
    await cb.answer()

@dp.message(Command("natal"))
@premium_required
async def cmd_natal(message: types.Message, state: FSMContext):
    await message.answer("📅 Введи дату рождения (ДД.ММ.ГГГГ):")
    await state.set_state(ProfileState.date)

@dp.message(ProfileState.date)
async def natal_date(message: types.Message, state: FSMContext):
    await state.update_data(birth_date=message.text)
    await message.answer("🕐 Введи время рождения (ЧЧ:ММ):")
    await state.set_state(ProfileState.time)

@dp.message(ProfileState.time)
async def natal_time(message: types.Message, state: FSMContext):
    await state.update_data(birth_time=message.text)
    await message.answer("🌍 Введи место рождения (город):")
    await state.set_state(ProfileState.place)

@dp.message(ProfileState.place)
async def natal_place(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await update_user(message.from_user.id, birth_date=data["birth_date"], birth_time=data["birth_time"], birth_place=data["birth_place"])
    await message.answer(
        "📊 **Натальная карта сгенерирована!**\n\n"
        f"📅 {data['birth_date']} | 🕐 {data['birth_time']} | 🌍 {data['birth_place']}\n\n"
        "☀️ Солнце в расчёте\n🌙 Луна в расчёте\n🪐 Асцендент: вычисляется...\n\n"
        "📜 Полный PDF-отчёт отправим в личку в течение 5 минут.\n(Демо-режим: здесь упрощённый вывод)"
    )
    await state.clear()

@dp.message(Command("transits"))
@premium_required
async def cmd_transits(message: types.Message):
    await message.answer(
        "🌌 **Прогноз транзитов на месяц**\n\n"
        "♄ Сатурн в Рыбах: время терпения и долгосрочных планов.\n"
        "♃ Юпитер в Близнецах: удача в обучении и коммуникациях.\n"
        "🪐 Плутон в Водолее: трансформация социальных связей.\n\n"
        "💡 Совет месяца: Не форсируй события. Адаптируйся к переменам."
    )

# 🔧 АДМИН КОМАНДЫ
@dp.message(Command("addpremium"))
async def cmd_addpremium(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.split()
    if len(parts) < 2: return await message.answer("Использование: `/addpremium <user_id>`")
    try:
        tid = int(parts[1])
        await set_premium(tid, True)
        await message.answer(f"✅ Пользователь {tid} получил Premium!")
    except:
        await message.answer("❌ Ошибка ID.")

@dp.message(Command("rmpremium"))
async def cmd_rmpremium(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    parts = message.text.split()
    if len(parts) < 2: return
    try:
        await set_premium(int(parts[1]), False)
        await message.answer("✅ Premium отключён.")
    except: pass

# 🌐 ВЕБ-СЕРВЕР ДЛЯ RENDER
async def handle_health(request):
    return web.Response(text="OK 🤖")

async def start_webserver(port):
    app = web.Application()
    app.add_routes([web.get('/', handle_health), web.get('/health', handle_health)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"🌐 Веб-сервер на порту {port}")
    return runner

# ♻️ АВТО-ПЕРЕЗАПУСК
async def run_with_restart():
    while True:
        try:
            logger.info("🔄 Запуск polling...")
            await dp.start_polling(bot)
        except Exception as e:
            logger.error(f"💥 Ошибка polling: {e}. Перезапуск через 15с...")
            await asyncio.sleep(15)
        await asyncio.sleep(5)

# 🚀 ГЛАВНАЯ
async def main():
    logger.info("🚀 Бот запускается...")
    init_db()
    
    try:
        me = await bot.me()
        logger.info(f"✅ Авторизован: @{me.username}")
    except Exception as e:
        logger.error(f"❌ Ошибка токена: {e}")
        return

    port = int(os.getenv("PORT", 10000))
    await start_webserver(port)
    await run_with_restart()

if __name__ == "__main__":
    asyncio.run(main())
