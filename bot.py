import asyncio
import logging
import os
import sqlite3
import random
import aiohttp
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiohttp import web

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not BOT_TOKEN or not GROQ_API_KEY:
    logging.error("❌ Ошибка: Проверь переменные окружения")
    exit()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
DB_NAME = "astro_users.db"

# ==================== FSM ====================
class OnboardingState(StatesGroup):
    name = State()
    birth_date = State()

class MagicBallState(StatesGroup):
    waiting_question = State()

class CompatibilityState(StatesGroup):
    waiting_partner_sign = State()

class NatalChartState(StatesGroup):
    waiting_time = State()
    waiting_place = State()

# ==================== БАЗА ДАННЫХ ====================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        telegram_id INTEGER UNIQUE,
        name TEXT,
        birth_date TEXT,
        birth_time TEXT,
        birth_place TEXT,
        zodiac TEXT,
        free_predictions INTEGER DEFAULT 3,
        last_reset_date DATE,
        is_premium INTEGER DEFAULT 0,
        referred_by INTEGER
    )''')
    conn.commit()
    conn.close()

def get_user(tid):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT * FROM users WHERE telegram_id=?", (tid,)).fetchone()
    conn.close()
    
    if user:
        user = dict(user)
        today = datetime.now().strftime("%Y-%m-%d")
        if user['last_reset_date'] != today:
            conn = sqlite3.connect(DB_NAME)
            conn.execute("UPDATE users SET free_predictions=3, last_reset_date=? WHERE telegram_id=?", 
                        (today, tid))
            conn.commit()
            conn.close()
            user['free_predictions'] = 3
            user['last_reset_date'] = today
        return user
    return None

def add_or_update_user(tid, name=None, birth_date=None, zodiac=None, birth_time=None, birth_place=None):
    conn = sqlite3.connect(DB_NAME)
    today = datetime.now().strftime("%Y-%m-%d")
    user = conn.execute("SELECT * FROM users WHERE telegram_id=?", (tid,)).fetchone()
    
    if not user:
        conn.execute("""INSERT INTO users 
            (telegram_id, name, birth_date, zodiac, free_predictions, last_reset_date, birth_time, birth_place) 
            VALUES (?, ?, ?, ?, 3, ?, ?, ?)""",
            (tid, name, birth_date, zodiac, today, birth_time, birth_place))
    else:
        conn.execute("""UPDATE users SET 
            name=COALESCE(?, name), birth_date=COALESCE(?, birth_date), 
            zodiac=COALESCE(?, zodiac), birth_time=COALESCE(?, birth_time), 
            birth_place=COALESCE(?, birth_place) WHERE telegram_id=?""",
            (name, birth_date, zodiac, birth_time, birth_place, tid))
    conn.commit()
    conn.close()

def use_prediction(tid):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("UPDATE users SET free_predictions = free_predictions - 1 WHERE telegram_id=?", (tid,))
    conn.commit()
    conn.close()

def add_predictions(tid, amount):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("UPDATE users SET free_predictions = free_predictions + ? WHERE telegram_id=?", (amount, tid))
    conn.commit()
    conn.close()

def set_premium(tid):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("UPDATE users SET is_premium=1 WHERE telegram_id=?", (tid,))
    conn.commit()
    conn.close()

def update_referrer(tid):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("UPDATE users SET free_predictions = free_predictions + 5 WHERE telegram_id=?", (tid,))
    conn.commit()
    conn.close()

# ==================== GROQ AI ====================
async def ask_groq(prompt, system_prompt):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                    "max_tokens": 800,
                    "temperature": 0.7
                }
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data['choices'][0]['message']['content']
                return f"Ошибка AI: {resp.status}"
    except Exception as e:
        return f"Ошибка: {e}"

# ==================== ПРОМПТЫ ====================
PROMPT_HOROSCOPE = """Ты профессиональный астролог с 20-летним опытом.
Составь ГОРОСКОП НА СЕГОДНЯ для знака {sign}.
СТРУКТУРА:
🌙 Гороскоп для {name} на {date}
⭐ Энергетика дня
💼 Карьера/финансы
❤️ Отношения
💡 Совет
Пиши конкретно. Длина: 150-250 слов."""

PROMPT_NATAL = """Ты профессиональный астролог-наталог.
Составь НАТАЛЬНУЮ КАРТУ для:
Дата: {birth_date}
Время: {birth_time}
Место: {birth_place}
СТРУКТУРА:
🌌 Натальная карта
♈ Асцендент и Солнечный знак
🌙 Луна
💫 Ключевые аспекты
🎯 Сильные стороны
⚠️ Зоны роста
Длина: 200-300 слов."""

PROMPT_COMPAT = """Ты астролог-эксперт по совместимости.
Рассчитай СОВМЕСТИМОСТЬ: {sign1} и {sign2}.
СТРУКТУРА:
💕 Совместимость
🔥 Общая вибрация
✅ Сильные стороны
⚠️ Зоны риска
💡 Совет
Длина: 150-200 слов."""

PROMPT_MAGIC_BALL = """Ты — магический шар Веданы. Отвечай на вопрос мистически, но конкретно.
Вопрос: {question}
Знак: {sign}
Формат:
🔮 Магический шар ответил:
[Ответ 2-3 предложения]
💡 Совет шара: [1 предложение]"""

PROMPT_WEEK = """Ты профессиональный астролог.
Составь ПРОГНОЗ НА НЕДЕЛЮ для {sign}.
СТРУКТУРА:
📅 Прогноз на неделю
✨ Общая тема недели
💼 Карьера
❤️ Отношения
💡 Совет на неделю
Длина: 150-200 слов."""

PROMPT_VEDANA_CONSULT = """
Ты — Ведана, мудрый и опытный астролог с 20-летним стажем. Ты видишь людей насквозь.
Твой стиль: спокойный, уверенный, мистический, но заботливый.

ДАННЫЕ КЛИЕНТА:
- Имя: {name}
- Знак: {sign}
- Дата рождения: {birth_date}

ПРОВЕДИ ЛИЧНУЮ КОНСУЛЬТАЦИЮ:

1. 👁️ **Взгляд в душу**
   Обратись к {name}. Опиши его суть и текущую энергетику.

2. 🔮 **Карта судьбы**
   Выдели 3 сферы (Любовь, Карьера, Рост). Для каждой — совет с астрологическими терминами.

3. 🕯️ **Тайное послание**
   Короткая мудрость-манифест.

4. ✨ **Совет от Веданы**
   Практическая рекомендация (цвет, камень, действие).

Правила:
- Тон: авторитетный, мягкий
- Не используй "Как AI"
- Избегай общих фраз
- Объем: 200-300 слов
"""

# ==================== ТАРО ====================
TAROT_CARDS = [
    {"name": "Шут (0)", "desc": "Начало пути, спонтанность. Рискни!"},
    {"name": "Маг (I)", "desc": "Сила воли. У тебя есть все ресурсы."},
    {"name": "Жрица (II)", "desc": "Интуиция. Слушай внутренний голос."},
    {"name": "Императрица (III)", "desc": "Плодородие. Время творить."},
    {"name": "Император (IV)", "desc": "Власть. Нужна дисциплина."},
    {"name": "Иерофант (V)", "desc": "Традиции. Ищи наставника."},
    {"name": "Влюбленные (VI)", "desc": "Выбор и любовь."},
    {"name": "Колесница (VII)", "desc": "Победа. Не сдавайся."},
    {"name": "Сила (VIII)", "desc": "Терпение. Мягкая сила."},
    {"name": "Отшельник (IX)", "desc": "Поиск истины внутри."},
    {"name": "Колесо Фортуны (X)", "desc": "Перемены. Всё идет по плану."},
    {"name": "Справедливость (XI)", "desc": "Карма. По заслугам."},
    {"name": "Повешенный (XII)", "desc": "Новый взгляд."},
    {"name": "Смерть (XIII)", "desc": "Трансформация."},
    {"name": "Умеренность (XIV)", "desc": "Баланс."},
    {"name": "Дьявол (XV)", "desc": "Искушения."},
    {"name": "Башня (XVI)", "desc": "Внезапные перемены."},
    {"name": "Звезда (XVII)", "desc": "Надежда."},
    {"name": "Луна (XVIII)", "desc": "Иллюзии."},
    {"name": "Солнце (XIX)", "desc": "Радость."},
    {"name": "Суд (XX)", "desc": "Возрождение."},
    {"name": "Мир (XXI)", "desc": "Гармония."}
]

# ==================== КЛАВИАТУРЫ ====================
def get_bottom_menu():
    """Нижнее постоянное меню"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏠 Главное меню"), KeyboardButton(text="👤 Профиль")],
            [KeyboardButton(text="🔮 Консультация Веданы"), KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_menu_grid(name, credits, is_prem):
    prem_text = "💎 PREMIUM (Активен)" if is_prem else "💎 PREMIUM — 100 ⭐"
    prem_data = "premium_active" if is_prem else "buy_premium"
    timer_text = "✨ ∞ прогнозов" if is_prem else f"✨ Осталось: {credits}/3"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"👋 {name}!", callback_data="noop")],
        [InlineKeyboardButton(text=timer_text, callback_data="noop")],
        [InlineKeyboardButton(text="🌟 Гороскоп", callback_data="horoscope"),
         InlineKeyboardButton(text="🌌 Натальная карта", callback_data="natal")],
        [InlineKeyboardButton(text="🃏 Таро", callback_data="tarot"),
         InlineKeyboardButton(text="💕 Совместимость", callback_data="compat")],
        [InlineKeyboardButton(text="🔮 Магический шар", callback_data="magic_ball"),
         InlineKeyboardButton(text="🪐 Ретро Меркурий", callback_data="mercury")],
        [InlineKeyboardButton(text="🔢 Нумерология", callback_data="numerology"),
         InlineKeyboardButton(text="📅 На неделю", callback_data="week")],
        [InlineKeyboardButton(text="💫 5 прогнозов — 50 ⭐", callback_data="buy_5"),
         InlineKeyboardButton(text="💫 15 прогнозов — 120 ⭐", callback_data="buy_15")],
        [InlineKeyboardButton(text=prem_text, callback_data=prem_data)],
        [InlineKeyboardButton(text="👥 Друг (+5 прогнозов)", callback_data="invite")],
        [InlineKeyboardButton(text="✏️ Изменить данные", callback_data="edit")]
    ])

# ==================== ОНБОРДИНГ ====================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user = get_user(message.from_user.id)
    
    if message.text and "ref_" in message.text and not user:
        try:
            ref_id = int(message.text.split("ref_")[1])
            update_referrer(ref_id)
        except: pass

    if user and user.get('name'):
        await message.answer("🔮 Главное меню", reply_markup=get_menu_grid(user['name'], user['free_predictions'], user['is_premium']))
    else:
        welcome = "🌌 **Я — Ведана.**\n\nНапиши: **имя**, **дату рождения** (ДД.ММ.ГГГГ).\n\nКарты откроют тайны… 🔮"
        try:
            photo = types.FSInputFile("vedana.jpg")
            await bot.send_photo(message.chat.id, photo, welcome, parse_mode="Markdown")
        except:
            await message.answer(welcome, parse_mode="Markdown")
        await message.answer("✨ Как тебя зовут?", reply_markup=get_bottom_menu())
        await state.set_state(OnboardingState.name)

@dp.message(OnboardingState.name)
async def onboarding_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer(f"✨ {message.text.strip()}!\n\n📅 Дата рождения (ДД.ММ.ГГГГ):", reply_markup=get_bottom_menu())
    await state.set_state(OnboardingState.birth_date)

@dp.message(OnboardingState.birth_date)
async def onboarding_birthdate(message: types.Message, state: FSMContext):
    try:
        datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except:
        await message.answer("❌ Неверно. Формат: ДД.ММ.ГГГГ", reply_markup=get_bottom_menu())
        return
    
    data = await state.get_data()
    name = data.get('name')
    zodiac = calculate_zodiac(message.text.strip())
    add_or_update_user(message.from_user.id, name, message.text.strip(), zodiac)
    
    await message.answer(f"♐ Знак: {zodiac}\n\nВыбери раздел:", 
                        reply_markup=get_menu_grid(name, 3, False))
    await state.clear()

# ==================== ФУНКЦИИ ====================
def calculate_zodiac(birth_date):
    try:
        date = datetime.strptime(birth_date, "%d.%m.%Y")
        day, month = date.day, date.month
        signs = [((3,21),(4,19),"♈ Овен"), ((4,20),(5,20),"♉ Телец"), ((5,21),(6,20),"♊ Близнецы"),
                 ((6,21),(7,22),"♋ Рак"), ((7,23),(8,22),"♌ Лев"), ((8,23),(9,22),"♍ Дева"),
                 ((9,23),(10,22),"♎ Весы"), ((10,23),(11,21),"♏ Скорпион"), ((11,22),(12,21),"♐ Стрелец"),
                 ((12,22),(12,31),"♑ Козерог"), ((1,1),(1,19),"♑ Козерог"), ((1,20),(2,18),"♒ Водолей"),
                 ((2,19),(3,20),"♓ Рыбы")]
        for (m1,d1),(m2,d2),sign in signs:
            if (month==m1 and day>=d1) or (month==m2 and day<=d2): return sign
        return "♓ Рыбы"
    except: return "Не определён"

def check_credits(user, msg):
    if not user['is_premium'] and user['free_predictions'] <= 0:
        msg.answer("❌ Прогнозы закончились. Пригласи друга или купи пакет!", reply_markup=get_bottom_menu())
        return False
    return True

# ==================== ОБРАБОТЧИКИ МЕНЮ ====================
@dp.callback_query(F.data == "noop")
async def noop(cb: types.CallbackQuery): await cb.answer()

@dp.callback_query(F.data == "horoscope")
async def horoscope(cb: types.CallbackQuery):
    user = get_user(cb.from_user.id)
    if not user or not check_credits(user, cb): return
    use_prediction(cb.from_user.id)
    
    prompt = PROMPT_HOROSCOPE.format(sign=user['zodiac'], name=user['name'], date=datetime.now().strftime("%d.%m.%Y"))
    await cb.message.answer("🌟 Составляю гороскоп...")
    ans = await ask_groq(prompt, "Ты астролог с 20-летним опытом.")
    await cb.message.answer(ans, parse_mode="Markdown", reply_markup=get_bottom_menu())
    await cb.answer()

@dp.callback_query(F.data == "natal")
async def natal(cb: types.CallbackQuery):
    user = get_user(cb.from_user.id)
    if not user or not check_credits(user, cb): return
    await cb.message.answer("🌌 Введи **время рождения** (ЧЧ:ММ):", parse_mode="Markdown", reply_markup=get_bottom_menu())
    await cb.answer()
    await dp.message.register(natal_time_handler, F.text)

async def natal_time_handler(msg: types.Message, state: FSMContext):
    await state.update_data(birth_time=msg.text.strip())
    await msg.answer("📍 **Место рождения** (Город):", parse_mode="Markdown", reply_markup=get_bottom_menu())
    await state.set_state(NatalChartState.waiting_place)

@dp.message(NatalChartState.waiting_place)
async def natal_place_handler(msg: types.Message, state: FSMContext):
    user = get_user(msg.from_user.id)
    if not user or not check_credits(user, msg): return
    
    data = await state.get_data()
    prompt = PROMPT_NATAL.format(birth_date=user['birth_date'], birth_time=data.get('birth_time'), birth_place=msg.text.strip())
    await msg.answer("🌌 Составляю карту...")
    ans = await ask_groq(prompt, "Ты астролог-наталог.")
    use_prediction(msg.from_user.id)
    add_or_update_user(msg.from_user.id, birth_time=data.get('birth_time'), birth_place=msg.text.strip())
    await msg.answer(ans, parse_mode="Markdown", reply_markup=get_bottom_menu())
    await state.clear()

@dp.callback_query(F.data == "magic_ball")
async def magic_ball_menu(cb: types.CallbackQuery):
    user = get_user(cb.from_user.id)
    if not user or not check_credits(user, cb): return
    await cb.message.answer("🔮 Напиши вопрос шару:", reply_markup=get_bottom_menu())
    await cb.answer()
    await dp.message.register(magic_ball_handler, F.text)

async def magic_ball_handler(msg: types.Message, state: FSMContext):
    user = get_user(msg.from_user.id)
    if not user or not check_credits(user, msg): return
    
    prompt = PROMPT_MAGIC_BALL.format(question=msg.text, sign=user.get('zodiac',''))
    await msg.answer("🔮 Шар думает...")
    ans = await ask_groq(prompt, "Ты магический шар.")
    use_prediction(msg.from_user.id)
    await msg.answer(ans, parse_mode="Markdown", reply_markup=get_bottom_menu())
    await state.clear()

@dp.callback_query(F.data == "compat")
async def compat_menu(cb: types.CallbackQuery):
    user = get_user(cb.from_user.id)
    if not user or not check_credits(user, cb): return
    await cb.message.answer("💕 Введи знак партнёра (Телец, Лев...):", reply_markup=get_bottom_menu())
    await cb.answer()
    await dp.message.register(compat_handler, F.text)

async def compat_handler(msg: types.Message, state: FSMContext):
    user = get_user(msg.from_user.id)
    if not user or not check_credits(user, msg): return
    
    prompt = PROMPT_COMPAT.format(sign1=user['zodiac'], sign2=msg.text.strip())
    await msg.answer("💕 Рассчитываю...")
    ans = await ask_groq(prompt, "Ты эксперт по совместимости.")
    use_prediction(msg.from_user.id)
    await msg.answer(ans, parse_mode="Markdown", reply_markup=get_bottom_menu())
    await state.clear()

@dp.callback_query(F.data == "week")
async def week_forecast(cb: types.CallbackQuery):
    user = get_user(cb.from_user.id)
    if not user or not check_credits(user, cb): return
    
    prompt = PROMPT_WEEK.format(sign=user['zodiac'])
    await cb.message.answer("📅 Составляю прогноз...")
    ans = await ask_groq(prompt, "Ты профессиональный астролог.")
    use_prediction(cb.from_user.id)
    await cb.message.answer(ans, parse_mode="Markdown", reply_markup=get_bottom_menu())
    await cb.answer()

@dp.callback_query(F.data == "vedana_consult")
async def vedana_consultation(cb: types.CallbackQuery):
    user = get_user(cb.from_user.id)
    if not user:
        await cb.answer("❌ Сначала /start", show_alert=True)
        return
    if not user.get('is_premium') and user.get('free_predictions', 0) <= 0:
        await cb.answer("❌ Нет прогнозов", show_alert=True)
        return
    
    prompt = PROMPT_VEDANA_CONSULT.format(name=user['name'], sign=user['zodiac'], birth_date=user['birth_date'])
    await cb.message.answer("🔮 Ведана изучает вашу карту...")
    ans = await ask_groq(prompt, "Ты Ведана, опытный астролог.")
    use_prediction(cb.from_user.id)
    await cb.message.answer(ans, parse_mode="Markdown", reply_markup=get_bottom_menu())
    await cb.answer()

@dp.callback_query(F.data == "tarot")
async def tarot(cb: types.CallbackQuery):
    card = random.choice(TAROT_CARDS)
    await cb.message.answer(f"🃏 {card['name']}\n\n{card['desc']}", parse_mode="Markdown", reply_markup=get_bottom_menu())
    await cb.answer()

@dp.callback_query(F.data == "mercury")
async def mercury(cb: types.CallbackQuery):
    await cb.message.answer("🪐 Проверяю...")
    ans = await ask_groq("Ретроградный Меркурий сейчас? Советы.", "Ты астролог.")
    await cb.message.answer(f"🪐 **Меркурий**\n\n{ans}", parse_mode="Markdown", reply_markup=get_bottom_menu())
    await cb.answer()

@dp.callback_query(F.data == "numerology")
async def numerology(cb: types.CallbackQuery):
    user = get_user(cb.from_user.id)
    if not user or not check_credits(user, cb): return
    
    await cb.message.answer("🔢 Рассчитываю...")
    prompt = f"Нумерология для {user['birth_date']}. Число пути и трактовка."
    ans = await ask_groq(prompt, "Ты нумеролог.")
    use_prediction(cb.from_user.id)
    await cb.message.answer(f"🔢 **Нумерология**\n\n{ans}", parse_mode="Markdown", reply_markup=get_bottom_menu())
    await cb.answer()

@dp.callback_query(F.data.startswith("buy_"))
async def buy_pack(cb: types.CallbackQuery):
    pack = cb.data.split("_")[1]
    amount = 50 if pack=="5" else 120
    await bot.send_invoice(cb.from_user.id, f"💫 {pack} прогнозов", f"{pack} прогнозов", f"pack_{pack}", "", "XTR", [LabeledPrice(f"Пакет {pack}", amount)])
    await cb.answer()

@dp.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery): await bot.answer_pre_checkout_query(q.id, ok=True)

@dp.message(F.successful_payment)
async def pay_success(msg: types.Message):
    user = get_user(msg.from_user.id)
    if "premium" in msg.successful_payment.invoice_payload:
        set_premium(msg.from_user.id)
        await msg.answer("🎉 Premium активирован!", reply_markup=get_menu_grid(user['name'], 999, True))
    else:
        add_predictions(msg.from_user.id, int(msg.successful_payment.invoice_payload.split("_")[1]))
        user = get_user(msg.from_user.id)
        await msg.answer(f"✅ Добавлено! Осталось: {user['free_predictions']}", reply_markup=get_menu_grid(user['name'], user['free_predictions'], user['is_premium']))

@dp.callback_query(F.data == "buy_premium")
async def buy_premium(cb: types.CallbackQuery):
    await bot.send_invoice(cb.from_user.id, "💎 Premium", "Безлимит", "premium_sub", "", "XTR", [LabeledPrice("Premium", 100)])
    await cb.answer()

@dp.callback_query(F.data == "invite")
async def invite(cb: types.CallbackQuery):
    link = f"https://t.me/{(await bot.me()).username}?start=ref_{cb.from_user.id}"
    await cb.message.answer(f"👥 Ссылка:\n{link}\n\n🎁 +5 прогнозов за друга!", reply_markup=get_bottom_menu())
    await cb.answer()

@dp.callback_query(F.data == "edit")
async def edit(cb: types.CallbackQuery):
    await cb.message.answer("✏️ Новая дата (ДД.ММ.ГГГГ):", reply_markup=get_bottom_menu())
    await cb.answer()
    await dp.message.register(save_edit, F.text)

async def save_edit(msg: types.Message, state: FSMContext):
    user = get_user(msg.from_user.id)
    try:
        datetime.strptime(msg.text.strip(), "%d.%m.%Y")
        zodiac = calculate_zodiac(msg.text.strip())
        add_or_update_user(msg.from_user.id, birth_date=msg.text.strip(), zodiac=zodiac)
        await msg.answer("✅ Обновлено!", reply_markup=get_menu_grid(user['name'], user['free_predictions'], user['is_premium']))
    except:
        await msg.answer("❌ Неверно", reply_markup=get_bottom_menu())
    await state.clear()

# ==================== НИЖНЕЕ МЕНЮ ====================
@dp.message(F.text == "🏠 Главное меню")
async def main_menu_btn(msg: types.Message):
    user = get_user(msg.from_user.id)
    if user:
        await msg.answer("🔮 Главное меню", reply_markup=get_menu_grid(user['name'], user['free_predictions'], user['is_premium']))

@dp.message(F.text == "👤 Профиль")
async def profile_btn(msg: types.Message):
    user = get_user(msg.from_user.id)
    if user:
        text = f"👤 **Профиль**\n\nИмя: {user['name']}\nЗнак: {user['zodiac']}\nДата: {user['birth_date']}\nПрогнозов: {user['free_predictions']}/3"
        await msg.answer(text, parse_mode="Markdown", reply_markup=get_bottom_menu())

@dp.message(F.text == "🔮 Консультация Веданы")
async def vedana_btn(msg: types.Message):
    user = get_user(msg.from_user.id)
    if not user:
        await msg.answer("❌ Сначала /start", reply_markup=get_bottom_menu())
        return
    if not user.get('is_premium') and user.get('free_predictions', 0) <= 0:
        await msg.answer("❌ Нет прогнозов. Купи пакет!", reply_markup=get_bottom_menu())
        return
    
    prompt = PROMPT_VEDANA_CONSULT.format(name=user['name'], sign=user['zodiac'], birth_date=user['birth_date'])
    await msg.answer("🔮 Ведана изучает карту...")
    ans = await ask_groq(prompt, "Ты Ведана.")
    use_prediction(msg.from_user.id)
    await msg.answer(ans, parse_mode="Markdown", reply_markup=get_bottom_menu())

@dp.message(F.text == "❓ Помощь")
async def help_btn(msg: types.Message):
    await msg.answer("""❓ **Помощь**

🌟 Гороскоп — ежедневный прогноз
🌌 Натальная карта — полная карта рождения
🃏 Таро — расклад
💕 Совместимость — с партнёром
🔮 Магический шар — ответ на вопрос
 Нумерология — число пути
📅 На неделю — прогноз на 7 дней
👥 Друг — +5 прогнозов

3 бесплатных прогноза в сутки!""", parse_mode="Markdown", reply_markup=get_bottom_menu())

# ==================== ЗАПУСК ====================
async def handle_health(req): return web.Response(text="OK")
async def start_web(port):
    app = web.Application(); app.add_routes([web.get('/', handle_health)])
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', port).start()
    logging.info(f"🌐 Server :{port}")

async def main():
    init_db()
    logging.info("🚀 Запуск...")
    await start_web(int(os.getenv("PORT", 10000)))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())