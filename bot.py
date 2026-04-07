import asyncio
import logging
import os
import sqlite3
import random
import aiohttp
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiohttp import web

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not BOT_TOKEN or not GROQ_API_KEY:
    logging.error("❌ Ошибка: Проверь переменные окружения BOT_TOKEN и GROQ_API_KEY")
    exit()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
DB_NAME = "astro_users.db"

# ==================== FSM ====================
class OnboardingState(StatesGroup):
    name = State()
    birth_date = State()

class NatalChartState(StatesGroup):
    waiting_time = State()
    waiting_place = State()

class MagicBallState(StatesGroup):
    waiting_question = State()

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
        # Ежедневный сброс прогнозов
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
    """Начисляет рефереру +5 прогнозов"""
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
СТРУКТУРА ОТВЕТА:
🌙 Гороскоп для {name} на {date}
⭐ Энергетика дня
💼 Карьера/финансы
❤️ Отношения
💡 Совет
Правила: Пиши конкретно, без воды. Используй астрологические термины. Тон: мудрый, поддерживающий. Длина: 150-250 слов."""

PROMPT_NATAL = """Ты профессиональный астролог-наталог.
Составь НАТАЛЬНУЮ КАРТУ для:
Дата: {birth_date}
Время: {birth_time}
Место: {birth_place}
СТРУКТУРА:
🌌 Натальная карта
♈ Асцендент и Солнечный знак
🌙 Луна и эмоциональный фон
💫 Ключевые аспекты и дома
🎯 Сильные стороны кармы
⚠️ Зоны роста
Длина: 200-300 слов. Тон: глубокий, аналитический."""

PROMPT_MAGIC_BALL = """Ты — магический шар Веданы. Отвечай на вопрос мистически, но конкретно.
Вопрос: {question}
Знак пользователя: {sign}
Формат ответа:
🔮 Магический шар ответил:
[Краткий мистический ответ 2-3 предложения]
💡 Совет шара: [1 предложение]"""

# ==================== ТАРО ====================
TAROT_CARDS = [
    {"name": "Шут (0)", "desc": "Начало пути, спонтанность, вера в лучшее. Рискни!"},
    {"name": "Маг (I)", "desc": "Сила воли и мастерство. У тебя есть все ресурсы."},
    {"name": "Жрица (II)", "desc": "Интуиция и тайны. Слушай внутренний голос."},
    {"name": "Императрица (III)", "desc": "Плодородие и изобилие. Время творить."},
    {"name": "Император (IV)", "desc": "Власть и структура. Нужна дисциплина."},
    {"name": "Иерофант (V)", "desc": "Традиции и обучение. Ищи наставника."},
    {"name": "Влюбленные (VI)", "desc": "Выбор и любовь. Следуй за сердцем."},
    {"name": "Колесница (VII)", "desc": "Победа и движение вперед. Не сдавайся."},
    {"name": "Сила (VIII)", "desc": "Терпение и мужество. Мягкая сила."},
    {"name": "Отшельник (IX)", "desc": "Поиск истины внутри себя. Одиночество полезно."},
    {"name": "Колесо Фортуны (X)", "desc": "Перемены и судьба. Всё идет по плану."},
    {"name": "Справедливость (XI)", "desc": "Карма и правда. Ты получишь по заслугам."},
    {"name": "Повешенный (XII)", "desc": "Жертва и новый взгляд. Посмотри иначе."},
    {"name": "Смерть (XIII)", "desc": "Трансформация. Старое уходит, новое приходит."},
    {"name": "Умеренность (XIV)", "desc": "Баланс и терпение. Ищи золотую середину."},
    {"name": "Дьявол (XV)", "desc": "Искушения и зависимости. Освободись от цепей."},
    {"name": "Башня (XVI)", "desc": "Внезапные перемены. Разрушение старого."},
    {"name": "Звезда (XVII)", "desc": "Надежда и вдохновение. Верь в мечту."},
    {"name": "Луна (XVIII)", "desc": "Иллюзии и страхи. Не верь всему, что видишь."},
    {"name": "Солнце (XIX)", "desc": "Радость и успех. Ясный день в жизни."},
    {"name": "Суд (XX)", "desc": "Возрождение и призыв. Время действовать."},
    {"name": "Мир (XXI)", "desc": "Завершение и гармония. Ты на месте."}
]

# ==================== МЕНЮ ====================
def get_menu_grid(name, credits, is_prem):
    prem_text = "💎 PREMIUM (Активен)" if is_prem else "💎 Получить PREMIUM — 100 ⭐"
    prem_data = "premium_active" if is_prem else "buy_premium"
    timer_text = "✨ Прогнозов: ∞" if is_prem else f"✨ Осталось прогнозов: {credits}/3"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"👋 Привет, {name}!", callback_data="noop")],
        [InlineKeyboardButton(text=timer_text, callback_data="noop")],
        
        [InlineKeyboardButton(text="🌟 Гороскоп", callback_data="horoscope"),
         InlineKeyboardButton(text="🌌 Натальная карта", callback_data="natal")],
        
        [InlineKeyboardButton(text="🃏 Расклад Таро", callback_data="tarot"),
         InlineKeyboardButton(text="💕 Совместимость", callback_data="compat")],
        
        [InlineKeyboardButton(text="🔮 Магический шар", callback_data="magic_ball"),
         InlineKeyboardButton(text="🪐 Ретро Меркурий", callback_data="mercury")],
        
        [InlineKeyboardButton(text="🔢 Нумерология", callback_data="numerology"),
         InlineKeyboardButton(text="📅 Прогноз на неделю", callback_data="week")],
        
        [InlineKeyboardButton(text="💫 5 прогнозов — 50 ⭐", callback_data="buy_5"),
         InlineKeyboardButton(text="💫 15 прогнозов — 120 ⭐", callback_data="buy_15")],
        
        [InlineKeyboardButton(text=prem_text, callback_data=prem_data)],
        
        [InlineKeyboardButton(text="👥 Пригласить друга (+5 прогнозов)", callback_data="invite")],
        [InlineKeyboardButton(text="✏️ Изменить данные", callback_data="edit")]
    ])

# ==================== ОНБОРДИНГ ====================
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user = get_user(message.from_user.id)
    
    # Обработка реферальной ссылки
    if message.text and "ref_" in message.text and not user:
        try:
            ref_id = int(message.text.split("ref_")[1])
            update_referrer(ref_id)
        except:
            pass

    if user and user.get('name') and user.get('birth_date'):
        await message.answer("🔮 Добро пожаловать в мир астрологии!", 
                           reply_markup=get_menu_grid(user['name'], user['free_predictions'], user['is_premium']))
    else:
        welcome_text = (
            "🌌 **Я — Ведана.**\n\n"
            "Звёзды уже чувствуют твоё присутствие, но чтобы карты не ошиблись, назови себя.\n\n"
            "Напиши мне: **имя**, **число**, **месяц** и **год рождения**.\n"
            "Я бережно сохраню эти данные, чтобы каждый гороскоп и расклад были составлены лично для тебя.\n\n"
            "Как только ответишь, меню откроет свои тайны… 🔮"
        )
        try:
            photo_file = types.FSInputFile("vedana.jpg")
            await bot.send_photo(chat_id=message.chat.id, photo=photo_file, caption=welcome_text, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Ошибка фото: {e}")
            await message.answer(welcome_text, parse_mode="Markdown")
        
        await message.answer("✨ Как тебя зовут?")
        await state.set_state(OnboardingState.name)

@dp.message(OnboardingState.name)
async def onboarding_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(name=name)
    await message.answer(f"✨ Прекрасное имя, {name}!\n\n📅 Введи дату рождения: ДД.ММ.ГГГГ\nПример: 15.03.1989")
    await state.set_state(OnboardingState.birth_date)

@dp.message(OnboardingState.birth_date)
async def onboarding_birthdate(message: types.Message, state: FSMContext):
    birth_date = message.text.strip()
    try:
        datetime.strptime(birth_date, "%d.%m.%Y")
    except:
        await message.answer("❌ Неверный формат. Используй ДД.ММ.ГГГГ")
        return

    data = await state.get_data()
    name = data.get('name', message.from_user.first_name)
    zodiac = calculate_zodiac(birth_date)

    add_or_update_user(message.from_user.id, name, birth_date, zodiac)
    
    # Проверяем, есть ли реферер в сообщении (на случай если пропустили в start)
    if message.text and "ref_" in message.text:
        try:
            ref_id = int(message.text.split("ref_")[1])
            update_referrer(ref_id)
        except: pass

    await message.answer(f"♐ Твой знак: {zodiac}\n\nТеперь выбери раздел:", 
                        reply_markup=get_menu_grid(name, 3, False))
    await state.clear()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ====================
def calculate_zodiac(birth_date):
    try:
        date = datetime.strptime(birth_date, "%d.%m.%Y")
        day, month = date.day, date.month
        signs = [
            ((1, 20), (2, 18), "♒ Водолей"), ((2, 19), (3, 20), "♓ Рыбы"),
            ((3, 21), (4, 19), "♈ Овен"), ((4, 20), (5, 20), "♉ Телец"),
            ((5, 21), (6, 20), "♊ Близнецы"), ((6, 21), (7, 22), "♋ Рак"),
            ((7, 23), (8, 22), "♌ Лев"), ((8, 23), (9, 22), "♍ Дева"),
            ((9, 23), (10, 22), "♎ Весы"), ((10, 23), (11, 21), "♏ Скорпион"),
            ((11, 22), (12, 21), "♐ Стрелец"), ((12, 22), (12, 31), "♑ Козерог")
        ]
        for (m1, d1), (m2, d2), sign in signs:
            if (month == m1 and day >= d1) or (month == m2 and day <= d2):
                return sign
        return "♑ Козерог"
    except:
        return "Не определён"

def check_credits(user, callback_or_message):
    if not user['is_premium'] and user['free_predictions'] <= 0:
        msg = callback_or_message.message if hasattr(callback_or_message, 'message') else callback_or_message
        msg.answer("❌ Бесплатные прогнозы на сегодня закончились. Пригласи друга или купи пакет!", reply_markup=get_menu_grid(user['name'], 0, False))
        return False
    return True

# ==================== ОБРАБОТЧИКИ ====================
@dp.callback_query(F.data == "noop")
async def noop(callback: types.CallbackQuery): await callback.answer()

@dp.callback_query(F.data == "horoscope")
async def horoscope(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or not check_credits(user, callback): return
    use_prediction(callback.from_user.id)
    
    sign = user.get('zodiac', 'Овен')
    name = user.get('name', 'друг')
    today = datetime.now().strftime("%d.%m.%Y")
    prompt = PROMPT_HOROSCOPE.format(sign=sign, name=name, date=today)
    
    await callback.message.answer("🌟 Составляю гороскоп...")
    ans = await ask_groq(prompt, "Ты профессиональный астролог с 20-летним опытом.")
    await callback.message.answer(ans, parse_mode="Markdown", reply_markup=get_menu_grid(name, user['free_predictions']-1, user['is_premium']))
    await callback.answer()

@dp.callback_query(F.data == "natal")
async def natal(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or not check_credits(user, callback): return
    await callback.message.answer("🌌 Для точной натальной карты укажи **время рождения** (ЧЧ:ММ):")
    await callback.answer()
    await dp.message.register(natal_time_handler, F.text)

async def natal_time_handler(message: types.Message, state: FSMContext):
    await state.update_data(birth_time=message.text.strip())
    await message.answer("📍 Теперь укажи **место рождения** (Город, Страна):")
    await state.set_state(NatalChartState.waiting_place)

@dp.message(NatalChartState.waiting_place)
async def natal_place_handler(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if not user or not check_credits(user, message): return
    
    data = await state.get_data()
    birth_time = data.get('birth_time')
    birth_place = message.text.strip()
    
    await message.answer("🌌 Составляю натальную карту...")
    prompt = PROMPT_NATAL.format(birth_date=user['birth_date'], birth_time=birth_time, birth_place=birth_place)
    ans = await ask_groq(prompt, "Ты профессиональный астролог-наталог.")
    
    use_prediction(message.from_user.id)
    add_or_update_user(message.from_user.id, birth_time=birth_time, birth_place=birth_place)
    await message.answer(ans, parse_mode="Markdown", reply_markup=get_menu_grid(user['name'], user['free_predictions']-1, user['is_premium']))
    await state.clear()

@dp.callback_query(F.data == "magic_ball")
async def magic_ball(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or not check_credits(user, callback): return
    await callback.message.answer("🔮 Напиши свой вопрос магическому шару:")
    await callback.answer()
    await dp.message.register(magic_ball_handler, F.text)

async def magic_ball_handler(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if not user or not check_credits(user, message): return
    
    await message.answer("🔮 Шар думает...")
    prompt = PROMPT_MAGIC_BALL.format(question=message.text, sign=user.get('zodiac', 'общий'))
    ans = await ask_groq(prompt, "Ты магический шар Веданы. Отвечай мистически и кратко.")
    
    use_prediction(message.from_user.id)
    await message.answer(ans, parse_mode="Markdown", reply_markup=get_menu_grid(user['name'], user['free_predictions']-1, user['is_premium']))
    await state.clear()

@dp.callback_query(F.data == "tarot")
async def tarot(callback: types.CallbackQuery):
    card = random.choice(TAROT_CARDS)
    await callback.message.answer(f"🃏 Твоя карта: {card['name']}\n\n{card['desc']}", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "compat")
async def compat_menu(callback: types.CallbackQuery):
    await callback.message.answer("💕 Введи знак партнёра (например: Телец, Лев):")
    await callback.answer()
    await dp.message.register(compat_handler, F.text)

async def compat_handler(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if not user or not check_credits(user, message): return
    await message.answer("💕 Рассчитываю совместимость...")
    prompt = PROMPT_COMPAT.format(sign1=user.get('zodiac', ''), sign2=message.text.strip())
    ans = await ask_groq(prompt, "Ты астролог-эксперт по совместимости.")
    use_prediction(message.from_user.id)
    await message.answer(ans, parse_mode="Markdown", reply_markup=get_menu_grid(user['name'], user['free_predictions']-1, user['is_premium']))
    await state.clear()

@dp.callback_query(F.data == "mercury")
async def mercury(callback: types.CallbackQuery):
    await callback.message.answer("🪐 Проверяю статус Меркурия...")
    ans = await ask_groq("Сейчас ретроградный Меркурий? Дай советы.", "Ты астролог.")
    await callback.message.answer(f"🪐 **Ретроградный Меркурий**\n\n{ans}", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "numerology")
async def numerology(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or not check_credits(user, callback): return
    await callback.message.answer("🔢 Рассчитываю число жизненного пути...")
    prompt = f"Рассчитай нумерологию для даты {user['birth_date']}. Число пути и трактовка."
    ans = await ask_groq(prompt, "Ты профессиональный нумеролог.")
    use_prediction(callback.from_user.id)
    await callback.message.answer(f"🔢 **Нумерология**\n\n{ans}", parse_mode="Markdown", reply_markup=get_menu_grid(user['name'], user['free_predictions']-1, user['is_premium']))
    await callback.answer()

@dp.callback_query(F.data == "week")
async def week(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or not check_credits(user, callback): return
    await callback.message.answer("📅 Составляю прогноз на неделю...")
    prompt = f"Прогноз на неделю для {user.get('zodiac', 'знака')}. Тема, карьера, отношения, совет."
    ans = await ask_groq(prompt, "Ты профессиональный астролог.")
    use_prediction(callback.from_user.id)
    await callback.message.answer(f"📅 **Прогноз на неделю**\n\n{ans}", parse_mode="Markdown", reply_markup=get_menu_grid(user['name'], user['free_predictions']-1, user['is_premium']))
    await callback.answer()

@dp.callback_query(F.data == "invite")
async def invite(callback: types.CallbackQuery):
    link = f"https://t.me/{(await bot.me()).username}?start=ref_{callback.from_user.id}"
    await callback.message.answer(f"👥 Твоя ссылка:\n{link}\n\n🎁 За каждого друга ты получишь **+5 бесплатных прогнозов**!")
    await callback.answer()

@dp.callback_query(F.data == "edit")
async def edit(callback: types.CallbackQuery):
    await callback.message.answer("✏️ Введи новую дату рождения (ДД.ММ.ГГГГ):")
    await callback.answer()
    await dp.message.register(save_edit, F.text)

async def save_edit(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    try:
        datetime.strptime(message.text.strip(), "%d.%m.%Y")
        zodiac = calculate_zodiac(message.text.strip())
        add_or_update_user(message.from_user.id, birth_date=message.text.strip(), zodiac=zodiac)
        await message.answer("✅ Данные обновлены!", reply_markup=get_menu_grid(user['name'], user['free_predictions'], user['is_premium']))
    except:
        await message.answer("❌ Неверный формат. ДД.ММ.ГГГГ")
    await state.clear()

# ==================== ОПЛАТА ====================
@dp.callback_query(F.data.startswith("buy_"))
async def buy_pack(callback: types.CallbackQuery):
    pack = callback.data.split("_")[1]
    amount = 50 if pack == "5" else 120
    await bot.send_invoice(chat_id=callback.from_user.id, title=f"💫 Пакет {pack} прогнозов",
        description=f"{pack} дополнительных прогнозов", payload=f"pack_{pack}", provider_token="", currency="XTR",
        prices=[LabeledPrice(label=f"Пакет {pack}", amount=amount)])
    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery): await bot.answer_pre_checkout_query(query.id, ok=True)

@dp.message(F.successful_payment)
async def pay_success(message: types.Message):
    if "premium" in message.successful_payment.invoice_payload:
        set_premium(message.from_user.id)
        await message.answer("🎉 Premium активирован! Прогнозы безлимитны.", reply_markup=get_menu_grid(get_user(message.from_user.id)['name'], 999, True))
    else:
        add_predictions(message.from_user.id, int(message.successful_payment.invoice_payload.split("_")[1]))
        user = get_user(message.from_user.id)
        await message.answer(f"✅ Добавлено прогнозов! Осталось: {user['free_predictions']}", reply_markup=get_menu_grid(user['name'], user['free_predictions'], user['is_premium']))

@dp.callback_query(F.data == "buy_premium")
async def buy_prem(callback: types.CallbackQuery):
    await bot.send_invoice(chat_id=callback.from_user.id, title="💎 Premium", description="Безлимитные прогнозы", payload="premium_sub", provider_token="", currency="XTR", prices=[LabeledPrice(label="Premium", amount=100)])
    await callback.answer()

# ==================== ЗАПУСК ====================
async def handle_health(request): return web.Response(text="OK")
async def start_web(port):
    app = web.Application(); app.add_routes([web.get('/', handle_health)])
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', port).start()
    logging.info(f"🌐 Server on :{port}")

async def main():
    init_db()
    logging.info("🚀 Бот Ведана запускается...")
    await start_web(int(os.getenv("PORT", 10000)))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())