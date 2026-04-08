import asyncio
import logging
import os
import sqlite3
import random
import aiohttp
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiohttp import web

# ================= НАСТРОЙКИ =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not BOT_TOKEN or not GROQ_API_KEY:
    logging.error("❌ Ошибка: Проверь переменные окружения BOT_TOKEN и GROQ_API_KEY")
    exit()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
DB_NAME = "astro_users.db"

# ================= FSM =================
class OnboardingState(StatesGroup):
    name = State()
    birth_date = State()

class NatalState(StatesGroup):
    time = State()
    place = State()

class BallState(StatesGroup):
    question = State()

class CompatState(StatesGroup):
    partner = State()

class RuneState(StatesGroup):
    question = State()

# ================= БАЗА ДАННЫХ =================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        telegram_id INTEGER UNIQUE,
        name TEXT,
        birth_date TEXT,
        zodiac TEXT,
        free_credits INTEGER DEFAULT 3,
        vedana_credits INTEGER DEFAULT 0,
        last_reset_date TEXT,
        is_premium INTEGER DEFAULT 0,
        referred INTEGER DEFAULT 0
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
        if user['last_reset_date'] != today and not user['is_premium']:
            conn = sqlite3.connect(DB_NAME)
            conn.execute("UPDATE users SET free_credits=3, last_reset_date=? WHERE telegram_id=?", (today, tid))
            conn.commit()
            conn.close()
            user['free_credits'] = 3
            user['last_reset_date'] = today
        return user
    return None

def add_or_update_user(tid, name=None, birth_date=None, zodiac=None):
    conn = sqlite3.connect(DB_NAME)
    today = datetime.now().strftime("%Y-%m-%d")
    user = conn.execute("SELECT * FROM users WHERE telegram_id=?", (tid,)).fetchone()
    if not user:
        conn.execute("""INSERT INTO users 
            (telegram_id, name, birth_date, zodiac, free_credits, vedana_credits, last_reset_date, is_premium, referred) 
            VALUES (?, ?, ?, ?, 3, 0, ?, 0, 0)""",
            (tid, name, birth_date, zodiac, today))
    else:
        conn.execute("""UPDATE users SET 
            name=COALESCE(?, name), birth_date=COALESCE(?, birth_date), 
            zodiac=COALESCE(?, zodiac) WHERE telegram_id=?""",
            (name, birth_date, zodiac, tid))
    conn.commit()
    conn.close()

def use_free_credit(tid):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("UPDATE users SET free_credits = free_credits - 1 WHERE telegram_id=?", (tid,))
    conn.commit()
    conn.close()

def use_vedana_credit(tid):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("UPDATE users SET vedana_credits = vedana_credits - 1 WHERE telegram_id=?", (tid,))
    conn.commit()
    conn.close()

def add_credits(tid, free_amt=0, vedana_amt=0, set_prem=False):
    conn = sqlite3.connect(DB_NAME)
    if set_prem:
        conn.execute("UPDATE users SET is_premium=1, vedana_credits = vedana_credits + ? WHERE telegram_id=?", (vedana_amt, tid))
    else:
        conn.execute("UPDATE users SET free_credits = free_credits + ?, vedana_credits = vedana_credits + ? WHERE telegram_id=?",
            (free_amt, vedana_amt, tid))
    conn.commit()
    conn.close()

def refer_user(tid):
    conn = sqlite3.connect(DB_NAME)
    user = conn.execute("SELECT referred FROM users WHERE telegram_id=?", (tid,)).fetchone()
    if user and user['referred'] == 0:
        conn.execute("UPDATE users SET referred=1, free_credits = free_credits + 5 WHERE telegram_id=?", (tid,))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

# ================= GROQ AI =================
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

# ================= ПРОМПТЫ =================
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
Дата: {birth_date}, Время: {time}, Место: {place}
СТРУКТУРА:
🌌 Натальная карта
♈ Асцендент и Солнечный знак
🌙 Луна и эмоции
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

PROMPT_BALL = """Ты — магический шар Веданы. Отвечай мистически, но конкретно.
Вопрос: {q}
Знак: {sign}
Формат:
🔮 Магический шар ответил:
[Ответ 2-3 предложения]
💡 Совет шара: [1 предложение]"""

PROMPT_WEEK = """Ты профессиональный астролог.
Составь ПРОГНОЗ НА НЕДЕЛЮ для {sign}.
СТРУКТУРА:
📅 Прогноз на неделю
✨ Общая тема
💼 Карьера
❤️ Отношения
💡 Совет
Длина: 150-200 слов."""

PROMPT_VEDANA = """
Ты — Ведана, мудрый астролог с 20-летним стажем. Ты видишь людей насквозь.
ДАННЫЕ: Имя: {name}, Знак: {sign}, Дата: {birth_date}
ПРОВЕДИ ЛИЧНУЮ КОНСУЛЬТАЦИЮ:
👁️ Взгляд в душу (обрати к имени, опиши суть и текущую энергию)
🔮 Карта судьбы (3 сферы: Любовь, Карьера, Рост + астротермины)
🕯️ Тайное послание (короткая мудрость)
✨ Совет от Веданы (практика: цвет, камень, действие)
Тон: авторитетный, мягкий. Без общих фраз. 200-300 слов.
"""

PROMPT_RUNE = """Ты — эксперт по рунам.
Вопрос: {q}
Знак: {sign}
Выбери 1-3 руны и дай трактовку.
Формат:
🔮 Руны открылись:
[Название рун и их значение]
💡 Послание рун: [2-3 предложения]"""

# ================= ТАРО =================
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

# ================= КЛАВИАТУРЫ =================
def get_bottom_menu():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="/start")]],
        resize_keyboard=True,
        is_persistent=False
    )

def get_after_pred_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔮 Узнать, что скрыто", callback_data="shop")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])

def get_shop_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💫 5 прогнозов + 1 Веда — 50 ⭐", callback_data="buy_starter")],
        [InlineKeyboardButton(text="🔥 15 прогнозов + 3 Веды — 120 ⭐", callback_data="buy_optimal")],
        [InlineKeyboardButton(text="💎 Безлимит + 6 Вед — 200 ⭐", callback_data="buy_premium_pack")],
        [InlineKeyboardButton(text="👥 Пригласи друга (+5 прогнозов)", callback_data="invite_friend")],
        [InlineKeyboardButton(text="🏠 Назад в меню", callback_data="main_menu")]
    ])

def get_menu_grid(name, free_c, vedana_c, is_prem):
    free_txt = "✨ ∞ прогнозов" if is_prem else f"✨ Осталось: {free_c}/3"
    vedana_txt = f"🔮 Вед: {vedana_c}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=free_txt, callback_data="noop")],
        [InlineKeyboardButton(text=vedana_txt, callback_data="shop")],
        
        [InlineKeyboardButton(text="🌟 Гороскоп", callback_data="horoscope"),
         InlineKeyboardButton(text="🌌 Натальная карта", callback_data="natal")],
        
        [InlineKeyboardButton(text="🃏 Таро", callback_data="tarot"),
         InlineKeyboardButton(text="💕 Совместимость", callback_data="compat")],
        
        [InlineKeyboardButton(text="🔮 Магический шар", callback_data="ball"),
         InlineKeyboardButton(text="🔮 Руны", callback_data="runes")],
        
        [InlineKeyboardButton(text="🔢 Нумерология", callback_data="numerology"),
         InlineKeyboardButton(text="📅 На неделю", callback_data="week")],
        
        [InlineKeyboardButton(text="✏️ Изменить данные", callback_data="edit")]
    ])

# ================= ЗАГРУЗКА (MP4) =================
async def show_loading(msg):
    try:
        await msg.answer_animation(
            animation="https://cdn.pixabay.com/video/2023/10/15/186249-856305280_large.mp4",
            caption="🔮 Звёзды думают..."
        )
    except:
        await msg.answer("⏳ Генерирую...")
    await asyncio.sleep(random.uniform(3, 5))

# ================= ОНБОРДИНГ =================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user = get_user(message.from_user.id)
    
    # Проверка реферальной ссылки
    if message.text and message.text.startswith("/start ref_"):
        ref_code = message.text.split("_")[1]
        if ref_code.isdigit() and int(ref_code) != message.from_user.id:
            if refer_user(message.from_user.id):
                await message.answer("🎉 Друг приглашён! Тебе начислено +5 прогнозов!")
    
    if user and user.get('name'):
        await message.answer("🔮 Главное меню", 
                           reply_markup=get_menu_grid(user['name'], user['free_credits'], user['vedana_credits'], user['is_premium']))
    else:
        welcome = "🌌 **Я — Ведана.**\nНапиши: **имя**, **дату рождения** (ДД.ММ.ГГГГ).\nКарты откроют тайны… 🔮"
        try:
            photo = types.FSInputFile("vedana.jpg")
            await bot.send_photo(message.chat.id, photo, welcome, parse_mode="Markdown")
        except Exception as e:
            logging.warning(f"Фото не найдено: {e}")
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
                        reply_markup=get_menu_grid(name, 3, 0, False))
    await state.clear()

# ================= ВСПОМОГАТЕЛЬНЫЕ =================
def calculate_zodiac(birth_date):
    try:
        date = datetime.strptime(birth_date, "%d.%m.%Y")
        day, month = date.day, date.month
        signs = [((3,21),(4,19), "♈ Овен"), ((4,20),(5,20), "♉ Телец"), ((5,21),(6,20), "♊ Близнецы"),
                 ((6,21),(7,22), "♋ Рак"), ((7,23),(8,22), "♌ Лев"), ((8,23),(9,22), "♍ Дева"),
                 ((9,23),(10,22), "♎ Весы"), ((10,23),(11,21), "♏ Скорпион"), ((11,22),(12,21), "♐ Стрелец"),
                 ((12,22),(12,31), "♑ Козерог"), ((1,1),(1,19), "♑ Козерог"), ((1,20),(2,18), "♒ Водолей"),
                 ((2,19),(3,20), "♓ Рыбы")]
        for (m1,d1),(m2,d2),sign in signs:
            if (month==m1 and day >=d1) or (month==m2 and day <=d2): return sign
        return "♓ Рыбы"
    except: return "Не определён"

def check_free(user, msg):
    if not user['is_premium'] and user['free_credits'] <= 0:
        # Показываем кнопку магазина даже если нет кредитов
        msg.answer("❌ Прогнозы на сегодня закончились. Раскрой тайны в магазине!", reply_markup=get_shop_kb())
        return False
    return True

async def send_pred(msg, text):
    await asyncio.sleep(random.uniform(3, 5))  # Замедление
    await msg.answer(text, parse_mode="Markdown", reply_markup=get_after_pred_kb())

# ================= ОБРАБОТЧИКИ =================
@dp.callback_query(F.data == "noop")
async def noop(cb: types.CallbackQuery): 
    await cb.answer()

@dp.message(F.text == "/start")
async def start_btn(msg: types.Message, state: FSMContext):
    await cmd_start(msg, state)

@dp.callback_query(F.data == "main_menu")
async def main_menu_cb(cb: types.CallbackQuery):
    user = get_user(cb.from_user.id)
    if user:
        await cb.message.edit_text("🔮 Главное меню", reply_markup=get_menu_grid(user['name'], user['free_credits'], user['vedana_credits'], user['is_premium']))
        await cb.answer()

@dp.callback_query(F.data == "shop")
async def shop_cb(cb: types.CallbackQuery):
    user = get_user(cb.from_user.id)
    if not user:
        await cb.answer("❌ Сначала /start", show_alert=True)
        return
    text = "✨ Что скрыто за твоим знаком?\n\nВедана может заглянуть глубже, если ты готов(а) к откровению.\n\n🔮 Индивидуальное предсказание включает:\n• Точные даты событий\n• Рекомендации по цвету/камню\n• Ответ на сокровенный вопрос\n• Послание наставников"
    await cb.message.edit_text(text, reply_markup=get_shop_kb())
    await cb.answer()

@dp.callback_query(F.data == "horoscope")
async def horoscope(cb: types.CallbackQuery):
    user = get_user(cb.from_user.id)
    if not user: 
        await cb.answer("❌ Сначала /start", show_alert=True)
        return
    
    if not check_free(user, cb): 
        return
    
    use_free_credit(cb.from_user.id)
    await show_loading(cb.message)
    
    prompt = PROMPT_HOROSCOPE.format(sign=user['zodiac'], name=user['name'], date=datetime.now().strftime("%d.%m.%Y"))
    ans = await ask_groq(prompt, "Ты астролог с 20-летним опытом.")
    await send_pred(cb.message, ans)
    await cb.answer()

@dp.callback_query(F.data == "natal")
async def natal(cb: types.CallbackQuery):
    user = get_user(cb.from_user.id)
    if not user: 
        await cb.answer("❌ Сначала /start", show_alert=True)
        return
    
    if not check_free(user, cb): 
        return
    
    await cb.message.answer("🌌 Введи время рождения (ЧЧ:ММ):", reply_markup=get_bottom_menu())
    await cb.answer()
    
    @dp.message()
    async def natal_time_handler(msg: types.Message, state: FSMContext):
        await state.update_data(time=msg.text.strip())
        await msg.answer("📍 Место рождения (Город):", reply_markup=get_bottom_menu())
        
        @dp.message()
        async def natal_place_handler(msg: types.Message):
            user = get_user(msg.from_user.id)
            if not user: 
                return
            data = await state.get_data()
            await show_loading(msg)
            prompt = PROMPT_NATAL.format(birth_date=user['birth_date'], time=data.get('time'), place=msg.text.strip())
            ans = await ask_groq(prompt, "Ты астролог-наталог.")
            use_free_credit(msg.from_user.id)
            await send_pred(msg, ans)
            dp.message.unregister(natal_time_handler)
            dp.message.unregister(natal_place_handler)
            await state.clear()
        
        dp.message.register(natal_place_handler)

@dp.callback_query(F.data == "ball")
async def ball_menu(cb: types.CallbackQuery):
    user = get_user(cb.from_user.id)
    if not user: 
        await cb.answer("❌ Сначала /start", show_alert=True)
        return
    
    if not check_free(user, cb): 
        return
    
    await cb.message.answer("🔮 Напиши вопрос шару:", reply_markup=get_bottom_menu())
    await cb.answer()
    
    @dp.message()
    async def ball_handler(msg: types.Message):
        user = get_user(msg.from_user.id)
        if not user: 
            return
        await show_loading(msg)
        prompt = PROMPT_BALL.format(q=msg.text, sign=user.get('zodiac',''))
        ans = await ask_groq(prompt, "Ты магический шар.")
        use_free_credit(msg.from_user.id)
        await send_pred(msg, ans)
        dp.message.unregister(ball_handler)

@dp.callback_query(F.data == "compat")
async def compat_menu(cb: types.CallbackQuery):
    user = get_user(cb.from_user.id)
    if not user: 
        await cb.answer("❌ Сначала /start", show_alert=True)
        return
    
    if not check_free(user, cb): 
        return
    
    await cb.message.answer("💕 Введи знак партнёра (Телец, Лев...):", reply_markup=get_bottom_menu())
    await cb.answer()
    
    @dp.message()
    async def compat_handler(msg: types.Message):
        user = get_user(msg.from_user.id)
        if not user: 
            return
        await show_loading(msg)
        prompt = PROMPT_COMPAT.format(sign1=user['zodiac'], sign2=msg.text.strip())
        ans = await ask_groq(prompt, "Ты эксперт по совместимости.")
        use_free_credit(msg.from_user.id)
        await send_pred(msg, ans)
        dp.message.unregister(compat_handler)

@dp.callback_query(F.data == "week")
async def week_forecast(cb: types.CallbackQuery):
    user = get_user(cb.from_user.id)
    if not user: 
        await cb.answer("❌ Сначала /start", show_alert=True)
        return
    
    if not check_free(user, cb): 
        return
    
    await show_loading(cb.message)
    prompt = PROMPT_WEEK.format(sign=user['zodiac'])
    ans = await ask_groq(prompt, "Ты профессиональный астролог.")
    use_free_credit(cb.from_user.id)
    await send_pred(cb.message, ans)
    await cb.answer()

@dp.callback_query(F.data == "numerology")
async def numerology(cb: types.CallbackQuery):
    user = get_user(cb.from_user.id)
    if not user: 
        await cb.answer("❌ Сначала /start", show_alert=True)
        return
    
    if not check_free(user, cb): 
        return
    
    await show_loading(cb.message)
    prompt = f"Нумерология для {user['birth_date']}. Число пути и трактовка."
    ans = await ask_groq(prompt, "Ты нумеролог.")
    use_free_credit(cb.from_user.id)
    await send_pred(cb.message, f"🔢 Нумерология\n\n{ans}")
    await cb.answer()

@dp.callback_query(F.data == "runes")
async def runes(cb: types.CallbackQuery):
    user = get_user(cb.from_user.id)
    if not user: 
        await cb.answer("❌ Сначала /start", show_alert=True)
        return
    
    if not check_free(user, cb): 
        return
    
    await cb.message.answer("🔮 Напиши вопрос рунам:", reply_markup=get_bottom_menu())
    await cb.answer()
    
    @dp.message()
    async def rune_handler(msg: types.Message):
        user = get_user(msg.from_user.id)
        if not user: 
            return
        await show_loading(msg)
        prompt = PROMPT_RUNE.format(q=msg.text, sign=user.get('zodiac',''))
        ans = await ask_groq(prompt, "Ты эксперт по рунам.")
        use_free_credit(msg.from_user.id)
        await send_pred(msg, ans)
        dp.message.unregister(rune_handler)

@dp.callback_query(F.data == "tarot")
async def tarot(cb: types.CallbackQuery):
    await asyncio.sleep(random.uniform(2, 4))
    card = random.choice(TAROT_CARDS)
    await cb.message.answer(f"🃏 {card['name']}\n\n{card['desc']}", reply_markup=get_after_pred_kb())
    await cb.answer()

@dp.callback_query(F.data == "vedana_pred")
async def vedana_pred(cb: types.CallbackQuery):
    user = get_user(cb.from_user.id)
    if not user:
        await cb.answer("❌ Сначала /start", show_alert=True)
        return
    if user['vedana_credits'] <= 0:
        await cb.message.answer("🔮 У тебя нет свободных предсказаний Веданы.\n\nРаскрой тайны в магазине:", reply_markup=get_shop_kb())
        await cb.answer()
        return
    await cb.message.answer("🕯️ Ведана изучает вашу карту...")
    prompt = PROMPT_VEDANA.format(name=user['name'], sign=user['zodiac'], birth_date=user['birth_date'])
    ans = await ask_groq(prompt, "Ты Ведана, опытный астролог.")
    use_vedana_credit(cb.from_user.id)
    await send_pred(cb.message, ans)
    await cb.answer()

@dp.callback_query(F.data == "edit")
async def edit(cb: types.CallbackQuery):
    await cb.message.answer("✏️ Новая дата (ДД.ММ.ГГГГ):", reply_markup=get_bottom_menu())
    await cb.answer()
    
    @dp.message()
    async def save_edit(msg: types.Message):
        user = get_user(msg.from_user.id)
        try:
            datetime.strptime(msg.text.strip(), "%d.%m.%Y")
            zodiac = calculate_zodiac(msg.text.strip())
            add_or_update_user(msg.from_user.id, birth_date=msg.text.strip(), zodiac=zodiac)
            await msg.answer("✅ Обновлено!", reply_markup=get_menu_grid(user['name'], user['free_credits'], user['vedana_credits'], user['is_premium']))
        except:
            await msg.answer("❌ Неверно", reply_markup=get_bottom_menu())
        dp.message.unregister(save_edit)

@dp.callback_query(F.data == "invite_friend")
async def invite_friend_cb(cb: types.CallbackQuery):
    invite_link = f"https://t.me/{(await bot.me()).username}?start=ref_{cb.from_user.id}"
    await cb.message.answer(f"👥 **Пригласи друга**\n\nОтправь эту ссылку другу:\n{invite_link}\n\nКогда друг зарегистрируется, ты получишь **+5 бесплатных прогнозов**!", parse_mode="Markdown", reply_markup=get_shop_kb())
    await cb.answer()

# ================= ОПЛАТА =================
@dp.callback_query(F.data.startswith("buy_"))
async def buy_pack(cb: types.CallbackQuery):
    packs = {
        "buy_starter": {"title": "Стартовый", "free": 5, "vedana": 1, "cost": 50},
        "buy_optimal": {"title": "Оптимальный", "free": 15, "vedana": 3, "cost": 120},
        "buy_premium_pack": {"title": "Безлимит", "free": 0, "vedana": 6, "cost": 200, "prem": True}
    }
    p = packs[cb.data]
    await bot.send_invoice(
        chat_id=cb.from_user.id, title=f"✨ {p['title']}", description=f"Активация через Telegram Stars",
        payload=cb.data, provider_token="", currency="XTR", prices=[LabeledPrice("Пакет", p['cost'])]
    )
    await cb.answer()

@dp.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(q.id, ok=True)

@dp.message(F.successful_payment)
async def pay_success(msg: types.Message):
    payload = msg.successful_payment.invoice_payload
    packs = {
        "buy_starter": {"free": 5, "vedana": 1},
        "buy_optimal": {"free": 15, "vedana": 3},
        "buy_premium_pack": {"free": 0, "vedana": 6, "prem": True}
    }
    p = packs.get(payload)
    if p:
        add_credits(msg.from_user.id, p.get('free',0), p.get('vedana',0), p.get('prem', False))
        user = get_user(msg.from_user.id)
        await msg.answer("✅ Пакет активирован! Звёзды на твоей стороне.", 
                     reply_markup=get_menu_grid(user['name'], user['free_credits'], user['vedana_credits'], user['is_premium']))

# ================= ЗАПУСК =================
async def handle_health(req): 
    return web.Response(text="OK")

async def start_web(port):
    app = web.Application()
    app.add_routes([web.get('/', handle_health)])
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', port).start()
    logging.info(f"🌐 Server :{port}")

async def main():
    init_db()
    logging.info("🚀 Запуск...")
    await start_web(int(os.getenv("PORT", 10000)))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())