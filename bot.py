import asyncio
import logging
import sys
import os
import sqlite3
import random
import re
import hashlib
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiohttp import web

# 🔧 НАСТРОЙКИ
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []
PAYMENT_LINK = os.getenv("PAYMENT_LINK", "https://t.me/YOUR_ADMIN")  # Ссылка на оплату

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден!"); sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 🖼️ КАРТИНКИ
WELCOME_IMAGE = "https://cdn.pixabay.com/photo/2017/08/16/22/38/universe-2650272_1280.jpg"
ASTRO_AI_IMAGE = "https://cdn.pixabay.com/photo/2018/01/14/17/14/christmas-3082211_1280.jpg"

# 🗄️ БАЗА ДАННЫХ
DB_PATH = "astro.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, telegram_id INTEGER UNIQUE, username TEXT, first_name TEXT,
        zodiac_sign TEXT, birth_date TEXT, is_premium INTEGER DEFAULT 0,
        daily_credits INTEGER DEFAULT 1, last_credit_date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit(); conn.close()

async def get_user(tid):
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    c = conn.cursor(); c.execute("SELECT * FROM users WHERE telegram_id=?", (tid,))
    res = c.fetchone(); conn.close()
    return dict(res) if res else None

def get_safe_name(user):
    return user.first_name or user.username or "Таинственный странник"

async def add_user(tid, uname, fname):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("""INSERT OR IGNORE INTO users (telegram_id, username, first_name, daily_credits, last_credit_date) 
                 VALUES (?,?,?,?,?)""", (tid, uname, fname, 1, today))
    conn.commit(); conn.close()

async def get_daily_credits(tid):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT daily_credits, last_credit_date FROM users WHERE telegram_id=?", (tid,))
    res = c.fetchone()
    
    if not res or res[1] != today:
        c.execute("UPDATE users SET daily_credits=1, last_credit_date=? WHERE telegram_id=?", (today, tid))
        conn.commit(); conn.close()
        return 1
    conn.close()
    return res[0] if res[0] else 1

async def use_credit(tid):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("UPDATE users SET daily_credits=daily_credits-1 WHERE telegram_id=?", (tid,))
    conn.commit(); conn.close()

async def save_zodiac(tid, sign):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("UPDATE users SET zodiac_sign=? WHERE telegram_id=?", (sign, tid))
    if c.rowcount == 0:
        c.execute("INSERT INTO users (telegram_id, zodiac_sign) VALUES (?, ?)", (tid, sign))
    conn.commit(); conn.close()

async def set_premium(tid, status: bool):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    val = 1 if status else 0
    c.execute("UPDATE users SET is_premium=? WHERE telegram_id=?", (val, tid))
    if c.rowcount == 0:
        c.execute("INSERT INTO users (telegram_id, is_premium) VALUES (?, ?)", (tid, val))
    conn.commit(); conn.close()

# 🔒 PREMIUM CHECK
def premium_required(func):
    async def wrapper(message: types.Message, *args, **kwargs):
        user = await get_user(message.from_user.id)
        if not user or not user.get("is_premium"):
            await message.answer("💎 **Premium-функция**\n\nПолучи доступ к:\n• Натальным картам\n• Детальной совместимости\n• Персональным прогнозам\n\n💰 299₽/мес", 
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💳 Купить Premium", url=PAYMENT_LINK)]]),
                parse_mode="Markdown")
            return
        return await func(message, *args, **kwargs)
    return wrapper

# ⌨️ МЕНЮ (СТИЛЬНОЕ INLINE)
def main_menu_kb(user_name=None, sign=None, credits=1):
    sign_emoji = sign.split()[0] if sign else "❓"
    credits_text = f"🎁 Прогнозов: {credits}"
    
    kb = [
        [InlineKeyboardButton(text="🔮 Гороскоп на день", callback_data="nav_horoscope")],
        [InlineKeyboardButton(text="🤖 Astro AI — умный прогноз", callback_data="nav_astro_ai")],
        [InlineKeyboardButton(text="🌙 Луна", callback_data="nav_moon"),
         InlineKeyboardButton(text="🎱 Магический шар", callback_data="nav_orb")],
        [InlineKeyboardButton(text="💕 Совместимость", callback_data="nav_compat")],
        [InlineKeyboardButton(text="💎 Premium", callback_data="nav_premium"),
         InlineKeyboardButton(text="📊 Профиль", callback_data="nav_profile")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def zodiac_kb():
    signs = ["♈ Овен", "♉ Телец", "♊ Близнецы", "♋ Рак", "♌ Лев", "♍ Дева", 
             "♎ Весы", "♏ Скорпион", "♐ Стрелец", "♑ Козерог", "♒ Водолей", "♓ Рыбы"]
    kb = [[InlineKeyboardButton(text=s, callback_data=f"sign_{s}")] for s in signs]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_main")]])

# 🌍 ДАННЫЕ
STOICHIOMETRY = {
    "♈ Овен": "fire", "♉ Телец": "earth", "♊ Близнецы": "air", "♋ Рак": "water",
    "♌ Лев": "fire", "♍ Дева": "earth", "♎ Весы": "air", "♏ Скорпион": "water",
    "♐ Стрелец": "fire", "♑ Козерог": "earth", "♒ Водолей": "air", "♓ Рыбы": "water"
}

COMPAT_VIBES = {
    ("fire", "fire"): {"vibe": "🔥🔥 Огненный союз", "plus": "Страсть и драйв", "minus": "Конкуренция", "advice": "Направляйте энергию в общие цели"},
    ("fire", "air"): {"vibe": "💨🔥 Вдохновение", "plus": "Идеи и лёгкость", "minus": "Нестабильность", "advice": "Дайте друг другу свободу"},
    ("fire", "water"): {"vibe": "💧🔥 Контрасты", "plus": "Глубина эмоций", "minus": "Непонимание", "advice": "Учитесь слушать друг друга"},
    ("fire", "earth"): {"vibe": "🌍🔥 Баланс", "plus": "Энергия + стабильность", "minus": "Разный темп", "advice": "Найдите золотую середину"},
    ("earth", "earth"): {"vibe": "🌍🌍 Надёжность", "plus": "Стабильность", "minus": "Рутина", "advice": "Добавляйте новизну"},
    ("earth", "water"): {"vibe": "💧🌍 Гармония", "plus": "Забота и уют", "minus": "Замкнутость", "advice": "Говорите о чувствах"},
    ("earth", "air"): {"vibe": "💨🌍 Практичность", "plus": "Идеи + реализация", "minus": "Разные ценности", "advice": "Уважайте различия"},
    ("air", "air"): {"vibe": "💨💨 Интеллект", "plus": "Общение и идеи", "minus": "Поверхностность", "advice": "Переходите от слов к делу"},
    ("air", "water"): {"vibe": "💧💨 Творчество", "plus": "Интуиция + логика", "minus": "Непонимание", "advice": "Слушайте сердцем и умом"},
    ("water", "water"): {"vibe": "💧💧 Глубина", "plus": "Эмпатия", "minus": "Драма", "advice": "Сохраняйте границы"}
}

ORACLE_ANSWERS = [
    "🌟 Звёзды говорят: ДА", "✨ Судьба решила: ТОЧНО ДА", "🌕 Луна благоволит",
    "🌙 Подожди", "⏳ Сатурн требует терпения", "🌍 Проверь детали",
    "💨 Нет", "🔥 ДЕЙСТВУЙ СЕЙЧАС!", "💧 Доверься интуиции",
    "🌌 Спроси позже", "🌀 Отпусти старое", "🕊️ Венера дарит шанс"
]

ASTRO_TIPS = [
    "🌿 Луна в Земле: планируйте бюджет", "⚡ Меркурий активен: проверяйте сообщения",
    "🌊 Ретроградность: перепроверяйте билеты", "☀️ Солнечный аспект: начинайте новое",
    "🌙 Очистите пространство", "🔮 Венера в гармонии: время для любви"
]

def get_moon_phase():
    known = datetime(2000, 1, 6, 18, 14); synodic = 29.53058867
    days = (datetime.now() - known).total_seconds() / 86400; phase = days % synodic
    if phase < 1.84566: return "🌑 Новолуние", 1, "🌱 Начинайте новое"
    elif phase < 5.53699: return "🌓 Растущая", int(phase/1.84566)+1, "🌿 Действуйте"
    elif phase < 9.22831: return "🌗 Первая четверть", 8, "⚖️ Корректируйте"
    elif phase < 12.91963: return "🌔 Растущая", 15, "📈 Масштабируйте"
    elif phase < 16.61096: return "🌕 Полнолуние", 16, "✨ Завершайте"
    elif phase < 20.30228: return "🌖 Убывающая", 17, "🔄 Анализируйте"
    elif phase < 23.99361: return "🌘 Последняя четверть", 23, "🧹 Очищайте"
    else: return "🌒 Убывающая", 24, "🌌 Отдыхайте"

def get_horoscope(sign):
    today = datetime.now().strftime("%Y-%m-%d")
    seed = int(hashlib.md5(f"{today}_{sign}".encode()).hexdigest(), 16)
    rng = random.Random(seed)
    
    intros = ["Звёзды выстраиваются в гармонию", "Луна обостряет интуицию", 
              "Планеты благоприятствуют смелым шагам", "Космос подсказывает: замедлись"]
    career = ["💼 Удача в системных действиях", "💼 Гибкость будет вознаграждена", 
              "💼 Отличный день для переговоров", "💼 Избегайте спонтанных трат"]
    love = ["❤️ Время для искренних разговоров", "❤️ Избегайте провокаций", 
            "❤️ Романтическая энергия на пике", "❤️ Проявите эмпатию"]
    advice = ["💡 Отпустите уходящее", "💡 Доверяйте интуиции", 
              "💡 Позаботьтесь о здоровье", "💡 Сделайте первый шаг"]
    
    return (f"🌟 {rng.choice(intros)}\n\n"
            f"{rng.choice(career)}\n\n{rng.choice(love)}\n\n{rng.choice(advice)}\n\n"
            f"🍀 Талисман: {rng.choice(['аметист', 'хрусталь', 'тигровый глаз'])} | "
            f"🎨 Цвет: {rng.choice(['изумрудный', 'голубой', 'золотой'])}")

# 🤖 ASTRO AI — УМНЫЙ ПРОГНОЗ
def generate_astro_ai_prediction(user_sign, user_name):
    """Генерирует «персонализированный» прогноз на основе знака и даты"""
    today = datetime.now()
    seed = int(hashlib.md5(f"{today}_{user_sign}_{user_name}".encode()).hexdigest(), 16)
    rng = random.Random(seed)
    
    themes = {
        "fire": ["карьера", "лидерство", "творчество", "смелые решения"],
        "earth": ["финансы", "стабильность", "здоровье", "практические дела"],
        "air": ["общение", "обучение", "путешествия", "новые идеи"],
        "water": ["отношения", "эмоции", "интуиция", "внутренний мир"]
    }
    
    element = STOICHIOMETRY.get(user_sign, "earth")
    theme = rng.choice(themes[element])
    
    predictions = [
        f"🔮 **Astro AI для {user_name}**\n\n"
        f"📅 **Сегодняшний фокус:** {theme}\n\n"
        f"✨ **Энергия дня:** {rng.choice(['высокая', 'средняя', 'трансформирующая'])}\n"
        f"🎯 **Лучшее время:** {rng.choice(['09:00-11:00', '14:00-16:00', '19:00-21:00'])}\n"
        f"⚠️ **Остерегайся:** {rng.choice(['поспешных решений', 'эмоциональных всплесков', 'прокрастинации'])}\n\n"
        f"💡 **Совет AI:** {rng.choice(['Действуйте решительно', 'Проявите терпение', 'Доверьтесь интуиции', 'Планируйте заранее'])}",
        
        f"🌌 **Космический анализ для {user_name}**\n\n"
        f"🪐 **Планета дня:** {rng.choice(['Меркурий', 'Венера', 'Марс', 'Юпитер'])}\n"
        f"💫 **Аспект:** {rng.choice(['гармоничный', 'напряжённый', 'трансформирующий'])}\n\n"
        f"📊 **Сферы влияния:**\n"
        f"• {theme}: {rng.choice(['85%', '72%', '91%'])}\n"
        f"• Здоровье: {rng.choice(['78%', '82%', '65%'])}\n"
        f"• Отношения: {rng.choice(['90%', '67%', '88%'])}\n\n"
        f"🎁 **Твой космический подарок дня:** {rng.choice(['неожиданная встреча', 'инсайт', 'финансовая удача'])}"
    ]
    
    return rng.choice(predictions)

# 🎯 ОБРАБОТЧИКИ

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await add_user(message.from_user.id, message.from_user.username, get_safe_name(message.from_user))
    user = await get_user(message.from_user.id)
    name = get_safe_name(message.from_user)
    sign = user.get("zodiac_sign") if user else None
    credits = await get_daily_credits(message.from_user.id)
    
    sign_text = f"⭐ Знак: {sign}" if sign else "⭐ Знак: не выбран"
    
    caption = (
        f"🔮 С возвращением, {name}!\n\n"
        f"{sign_text} | 🎁 Прогнозов: {credits}\n\n"
        "Я — проводник между мирами видимого и скрытого.\n"
        "Выбери раздел, чтобы узнать свою судьбу ✨"
    )
    
    try:
        await message.answer_photo(
            photo=WELCOME_IMAGE,
            caption=caption,
            reply_markup=main_menu_kb(name, sign, credits)
        )
    except:
        await message.answer(caption, reply_markup=main_menu_kb(name, sign, credits))
    
    logger.info(f"✅ /start от {message.from_user.id}")

@dp.callback_query(F.data == "back_main")
async def back_main(cb: types.CallbackQuery):
    user = await get_user(cb.from_user.id)
    name = get_safe_name(types.User(id=cb.from_user.id, first_name=user.get("first_name") if user else None, username=user.get("username") if user else None))
    sign = user.get("zodiac_sign") if user else None
    credits = await get_daily_credits(cb.from_user.id)
    
    caption = f"🔮 Главное меню\n\n{get_safe_name(types.User(id=cb.from_user.id, first_name=user.get("first_name") if user else None))}, выбери раздел:"
    
    await cb.message.edit_text(caption, reply_markup=main_menu_kb(name, sign, credits))
    await cb.answer()

@dp.callback_query(F.data == "nav_horoscope")
async def nav_horoscope(cb: types.CallbackQuery):
    await cb.message.edit_text("🔮 **Выбери свой знак**\n\nЯ рассчитаю персональный прогноз на сегодня:", reply_markup=zodiac_kb())
    await cb.answer()

@dp.callback_query(F.data.startswith("sign_"))
async def show_horoscope(cb: types.CallbackQuery):
    sign = cb.data.replace("sign_", "")
    credits = await get_daily_credits(cb.from_user.id)
    
    if credits <= 0:
        await cb.answer("⚠️ Бесплатный прогноз на сегодня закончился!\n\n💎 Premium: безлимитные прогнозы", show_alert=True)
        return
    
    await use_credit(cb.from_user.id)
    await save_zodiac(cb.from_user.id, sign)
    
    text = get_horoscope(sign)
    new_credits = credits - 1
    
    await cb.message.edit_text(
        f"{sign}\n\n{text}\n\n🎁 Осталось прогнозов: {new_credits}",
        reply_markup=back_kb()
    )
    await cb.answer()

@dp.callback_query(F.data == "nav_astro_ai")
async def nav_astro_ai(cb: types.CallbackQuery):
    user = await get_user(cb.from_user.id)
    name = get_safe_name(types.User(id=cb.from_user.id, first_name=user.get("first_name") if user else None))
    sign = user.get("zodiac_sign") if user else None
    
    if not sign:
        await cb.message.edit_text(
            "🤖 **Astro AI**\n\n"
            "Сначала выбери свой знак в разделе 🔮 Гороскоп,\n"
            "и я создам персональный AI-прогноз!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔮 Выбрать знак", callback_data="nav_horoscope")]])
        )
        await cb.answer()
        return
    
    # Генерируем «умный» прогноз
    prediction = generate_astro_ai_prediction(sign, name)
    
    try:
        await cb.message.answer_photo(
            photo=ASTRO_AI_IMAGE,
            caption=prediction,
            reply_markup=back_kb(),
            parse_mode="Markdown"
        )
        await cb.message.delete()
    except:
        await cb.message.edit_text(prediction, reply_markup=back_kb(), parse_mode="Markdown")
    
    await cb.answer()

@dp.callback_query(F.data == "nav_moon")
async def nav_moon(cb: types.CallbackQuery):
    phase, day, rec = get_moon_phase()
    text = (f"🌙 **Фаза Луны**: {phase}\n"
            f"📅 **Лунный день**: {day}\n"
            f"💡 **Рекомендация**: {rec}\n\n"
            f"🌌 {random.choice(ASTRO_TIPS)}")
    
    await cb.message.edit_text(text, reply_markup=back_kb(), parse_mode="Markdown")
    await cb.answer()

@dp.callback_query(F.data == "nav_orb")
async def nav_orb(cb: types.CallbackQuery):
    await cb.message.edit_text(f"🎱 {random.choice(ORACLE_ANSWERS)}", reply_markup=back_kb())
    await cb.answer()

@dp.callback_query(F.data == "nav_compat")
async def nav_compat(cb: types.CallbackQuery):
    await cb.message.edit_text(
        "💕 **Совместимость по стихиям**\n\n"
        "Напиши имя и знак партнёра.\n"
        "Пример: `Света Близнецы` или `Макс ♏`",
        reply_markup=back_kb(),
        parse_mode="Markdown"
    )
    await cb.answer()

@dp.callback_query(F.data == "nav_premium")
async def nav_premium(cb: types.CallbackQuery):
    text = (
        "💎 **Premium-доступ**\n\n"
        "📊 **Полная натальная карта**\n"
        "💕 **Детальная совместимость** по датам\n"
        "🌌 **Прогноз транзитов** планет\n"
        "🔮 **Персональные рекомендации**\n"
        "⚡ **Безлимитные прогнозы**\n\n"
        "💰 **299₽ / месяц**\n\n"
        "Нажми кнопку для оплаты:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить Premium", url=PAYMENT_LINK)],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ])
    
    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()

@dp.callback_query(F.data == "nav_profile")
async def nav_profile(cb: types.CallbackQuery):
    user = await get_user(cb.from_user.id)
    if not user: return
    
    name = user.get("first_name") or "Пользователь"
    sign = user.get("zodiac_sign") or "Не выбран"
    prem = "💎 Да" if user.get("is_premium") else "🆓 Нет"
    credits = await get_daily_credits(cb.from_user.id)
    
    text = (f"👤 **Профиль**\n\n"
            f"Имя: {name}\n"
            f"♐ Знак: {sign}\n"
            f"💎 Premium: {prem}\n"
            f"🎁 Прогнозов сегодня: {credits}")
    
    await cb.message.edit_text(text, reply_markup=back_kb(), parse_mode="Markdown")
    await cb.answer()

@dp.message()
async def handle_compat_input(message: types.Message):
    # Простой парсинг: ищем знак в сообщении
    text = message.text.strip().lower()
    sign_map = {"овен": "♈ Овен", "телец": "♉ Телец", "близнецы": "♊ Близнецы", "рак": "♋ Рак",
                "лев": "♌ Лев", "дева": "♍ Дева", "весы": "♎ Весы", "скорпион": "♏ Скорпион",
                "стрелец": "♐ Стрелец", "козерог": "♑ Козерог", "водолей": "♒ Водолей", "рыбы": "♓ Рыбы"}
    
    found_sign = None
    for key, full in sign_map.items():
        if key in text:
            found_sign = full
            break
    
    if not found_sign:
        return  # Игнорируем, если не команда совместимости
    
    user = await get_user(message.from_user.id)
    user_sign = user.get("zodiac_sign") if user else None
    
    if not user_sign:
        await message.answer("❓ Сначала выбери свой знак в меню 🔮", reply_markup=main_menu_kb())
        return
    
    # Расчёт
    my_el = STOICHIOMETRY[user_sign]
    their_el = STOICHIOMETRY[found_sign]
    data = COMPAT_VIBES.get((my_el, their_el)) or COMPAT_VIBES.get((their_el, my_el)) or {"vibe": "💫 Уникальный союз", "plus": "Гармония", "minus": "Нет", "advice": "Доверяйте друг другу"}
    
    name_part = message.text.replace(found_sign, "").replace(list(sign_map.keys())[list(sign_map.values()).index(found_sign)], "").strip().capitalize()
    name = name_part or "Партнёр"
    
    text = (f"💕 {user.get('first_name', 'Вы')} ({user_sign}) + {name} ({found_sign})\n\n"
            f"**{data['vibe']}**\n"
            f"✅ {data['plus']}\n"
            f"⚠️ {data['minus']}\n"
            f"💡 {data['advice']}")
    
    await message.answer(text, reply_markup=main_menu_kb(), parse_mode="Markdown")

# 🌐 WEB SERVER
async def handle_health(request): return web.Response(text="OK 🤖")
async def start_webserver(port):
    app = web.Application(); app.add_routes([web.get('/', handle_health), web.get('/health', handle_health)])
    runner = web.AppRunner(app); await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port); await site.start()
    logger.info(f"🌐 Server on port {port}")

async def run_with_restart():
    while True:
        try: logger.info("🔄 Polling..."); await dp.start_polling(bot)
        except Exception as e: logger.error(f"💥 {e}"); await asyncio.sleep(15)

async def main():
    logger.info("🚀 Starting..."); init_db()
    try: me = await bot.me(); logger.info(f"✅ @{me.username}")
    except Exception as e: logger.error(f"❌ {e}"); return
    await start_webserver(int(os.getenv("PORT", 10000)))
    await run_with_restart()

if __name__ == "__main__": asyncio.run(main())
