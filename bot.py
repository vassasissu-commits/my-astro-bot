import asyncio
import logging
import os
import sqlite3
import random
import aiohttp
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
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

class QuestionState(StatesGroup):
    waiting_question = State()

class CompatibilityState(StatesGroup):
    waiting_partner_sign = State()

# ==================== БАЗА ДАННЫХ ====================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        telegram_id INTEGER UNIQUE,
        name TEXT,
        birth_date TEXT,
        zodiac TEXT,
        free_credits INTEGER DEFAULT 1,
        last_login DATE,
        is_premium INTEGER DEFAULT 0,
        next_free_time TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def get_user(tid):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT * FROM users WHERE telegram_id=?", (tid,)).fetchone()
    conn.close()
    return dict(user) if user else None

def add_or_update_user(tid, name=None, birth_date=None, zodiac=None):
    conn = sqlite3.connect(DB_NAME)
    today = datetime.now().strftime("%Y-%m-%d")
    user = conn.execute("SELECT * FROM users WHERE telegram_id=?", (tid,)).fetchone()
    
    if not user:
        next_free = datetime.now() + timedelta(hours=24)
        conn.execute("""INSERT INTO users 
            (telegram_id, name, birth_date, zodiac, free_credits, last_login, next_free_time) 
            VALUES (?, ?, ?, ?, 1, ?, ?)""",
            (tid, name, birth_date, zodiac, today, next_free))
    else:
        if user['last_login'] != today:
            next_free = datetime.now() + timedelta(hours=24)
            conn.execute("""UPDATE users SET 
                free_credits=1, last_login=?, next_free_time=?, 
                name=COALESCE(?, name), birth_date=COALESCE(?, birth_date), 
                zodiac=COALESCE(?, zodiac) WHERE telegram_id=?""",
                (today, next_free, name, birth_date, zodiac, tid))
        else:
            conn.execute("""UPDATE users SET 
                name=COALESCE(?, name), birth_date=COALESCE(?, birth_date), 
                zodiac=COALESCE(?, zodiac) WHERE telegram_id=?""",
                (name, birth_date, zodiac, tid))
    conn.commit()
    conn.close()

def use_credit(tid):
    conn = sqlite3.connect(DB_NAME)
    next_free = datetime.now() + timedelta(hours=24)
    conn.execute("UPDATE users SET free_credits = free_credits - 1, next_free_time=? WHERE telegram_id=?",
                (next_free, tid))
    conn.commit()
    conn.close()

def set_premium(tid):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("UPDATE users SET is_premium=1 WHERE telegram_id=?", (tid,))
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

PROMPT_NATAL = """Ты профессиональный астролог.
Составь НАТАЛЬНУЮ КАРТУ для человека, родившегося {birth_date}.
СТРУКТУРА:
🌌 Натальная карта
♈ Твой знак зодиака
🌙 Луна
☀️ Солнце
💫 Основные аспекты
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

# ==================== МЕНЮ ====================
def get_menu_grid(name, credits, next_free_time, is_prem):
    if next_free_time:
        try:
            nf_time = datetime.fromisoformat(next_free_time)
            now = datetime.now()
            if nf_time > now and not is_prem:
                delta = nf_time - now
                hours, remainder = divmod(int(delta.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)
                timer_text = f"⏳ Следующий: {hours}ч {minutes}мин"
            else:
                timer_text = "✨ ∞ прогнозов" if is_prem else f"✨ Осталось: {credits}/3"
        except:
            timer_text = f"✨ Осталось: {credits}/3"
    else:
        timer_text = f"✨ Осталось: {credits}/3"
    
    prem_text = "💎 PREMIUM (Активен)" if is_prem else "💎 PREMIUM — 100 ⭐"
    prem_data = "premium_active" if is_prem else "buy_premium"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"👋 {name}!", callback_data="noop")],
        [InlineKeyboardButton(text=timer_text, callback_data="noop")],
        [InlineKeyboardButton(text="🌟 Гороскоп", callback_data="horoscope"),
         InlineKeyboardButton(text="🌌 Натальная карта", callback_data="natal")],
        [InlineKeyboardButton(text="🃏 Таро", callback_data="tarot"),
         InlineKeyboardButton(text="💕 Совместимость", callback_data="compat")],
        [InlineKeyboardButton(text="🔮 Магический шар", callback_data="ask_ai"),
         InlineKeyboardButton(text="🪐 Ретро Меркурий", callback_data="mercury")],
        [InlineKeyboardButton(text="🔢 Нумерология", callback_data="numerology"),
         InlineKeyboardButton(text="📅 На неделю", callback_data="week")],
        [InlineKeyboardButton(text="🔮 Консультация Веданы", callback_data="vedana_consult")],
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
    
    if user and user.get('name') and user.get('birth_date'):
        await message.answer("🔮 Главное меню", 
                           reply_markup=get_menu_grid(user['name'], user['free_credits'], 
                                                    user.get('next_free_time'), user['is_premium']))
    else:
        welcome_text = (
            "🌌 **Я — Ведана.**\n\n"
            "Звёзды уже чувствуют твоё присутствие, но чтобы карты не ошиблись, назови себя.\n\n"
            "Напиши мне: **имя**, **число**, **месяц** и **год рождения**.\n"
            "Я бережно сохраню эти данные, чтобы каждый гороскоп и расклад были составлены лично для тебя.\n\n"
            "Как только ответишь, меню откроет свои тайны… 🔮"
        )
        
        # ОТПРАВКА ФОТО ВЕДАНЫ
        try:
            photo_file = types.FSInputFile("vedana.jpg")
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=photo_file,
                caption=welcome_text,
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Ошибка отправки фото: {e}")
            await message.answer("⚠️ Не удалось загрузить изображение Веданы.\n\n" + welcome_text, parse_mode="Markdown")
        
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

    await message.answer(f"♐ Твой знак: {zodiac}\n\nТеперь выбери раздел:", 
                        reply_markup=get_menu_grid(name, 3, None, False))
    await state.clear()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ====================
def calculate_zodiac(birth_date):
    try:
        date = datetime.strptime(birth_date, "%d.%m.%Y")
        day, month = date.day, date.month
        signs = [
            ((3,21),(4,19),"♈ Овен"), ((4,20),(5,20),"♉ Телец"), ((5,21),(6,20),"♊ Близнецы"),
            ((6,21),(7,22),"♋ Рак"), ((7,23),(8,22),"♌ Лев"), ((8,23),(9,22),"♍ Дева"),
            ((9,23),(10,22),"♎ Весы"), ((10,23),(11,21),"♏ Скорпион"), ((11,22),(12,21),"♐ Стрелец"),
            ((12,22),(12,31),"♑ Козерог"), ((1,1),(1,19),"♑ Козерог"), ((1,20),(2,18),"♒ Водолей"),
            ((2,19),(3,20),"♓ Рыбы")
        ]
        for (m1,d1),(m2,d2),sign in signs:
            if (month==m1 and day>=d1) or (month==m2 and day<=d2):
                return sign
        return "♓ Рыбы"
    except:
        return "Не определён"

# ==================== ОБРАБОТЧИКИ ====================
@dp.callback_query(F.data == "noop")
async def noop(callback: types.CallbackQuery):
    await callback.answer()

@dp.callback_query(F.data == "horoscope")
async def horoscope(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Сначала пройди /start", show_alert=True)
        return
    if not user['is_premium'] and user['free_credits'] <= 0:
        await callback.answer("❌ Нет прогнозов. Купи пакет!", show_alert=True)
        return

    use_credit(callback.from_user.id)
    await callback.message.answer("🌟 Составляю гороскоп...")

    sign = user.get('zodiac', 'Овен')
    name = user.get('name', 'друг')
    today = datetime.now().strftime("%d.%m.%Y")

    prompt = PROMPT_HOROSCOPE.format(sign=sign, name=name, date=today)
    ans = await ask_groq(prompt, "Ты профессиональный астролог с 20-летним опытом.")

    await callback.message.answer(ans, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "vedana_consult")
async def vedana_consultation(callback: types.CallbackQuery):
    """КОНСУЛЬТАЦИЯ ВЕДАНЫ - ПЛАТНАЯ (тратит кредит)"""
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Сначала пройди /start", show_alert=True)
        return
    
    if not user['is_premium'] and user['free_credits'] <= 0:
        await callback.answer("❌ Нет бесплатных консультаций. Купи пакет!", show_alert=True)
        return

    # Тратим кредит
    use_credit(callback.from_user.id)
    await callback.message.answer("🔮 Ведана изучает вашу карту...")

    sign = user.get('zodiac', 'Овен')
    name = user.get('name', 'друг')
    birth_date = user.get('birth_date', '')

    prompt = PROMPT_VEDANA_CONSULT.format(sign=sign, name=name, birth_date=birth_date)
    ans = await ask_groq(prompt, "Ты Ведана — опытный астролог с 20-летним стажем.")

    await callback.message.answer(ans, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "tarot")
async def tarot(callback: types.CallbackQuery):
    card = random.choice(TAROT_CARDS)
    await callback.message.answer(f"🃏 Твоя карта: {card['name']}\n\n{card['desc']}", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "ask_ai")
async def ask_ai_menu(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Сначала пройди /start", show_alert=True)
        return
    if not user['is_premium'] and user['free_credits'] <= 0:
        await callback.answer("❌ Нет прогнозов", show_alert=True)
        return
    
    await callback.message.answer("🔮 Напиши свой вопрос магическому шару:")
    await callback.answer()
    await dp.message.register(handle_ai_question, F.text)

async def handle_ai_question(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Сначала пройди /start")
        return
    
    if not user['is_premium'] and user['free_credits'] <= 0:
        await message.answer("❌ Нет кредитов")
        return

    await message.answer("🔮 Шар думает...")

    sign = user.get('zodiac', 'общий')
    prompt = f"Ты магический шар. Вопрос от {sign}: {message.text}. Ответь мистически, но конкретно (2-3 предложения)."
    ans = await ask_groq(prompt, "Ты магический шар Веданы.")

    await message.answer(f"🔮 **Магический шар ответил:**\n\n{ans}", parse_mode="Markdown")
    use_credit(message.from_user.id)
    await state.clear()

@dp.callback_query(F.data == "natal")
async def natal(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or not user.get('birth_date'):
        await callback.message.answer("📅 Сначала укажи дату рождения через /start")
        await callback.answer()
        return
    
    if not user['is_premium'] and user['free_credits'] <= 0:
        await callback.answer("❌ Нет прогнозов", show_alert=True)
        return
    
    await callback.message.answer("🌌 Составляю натальную карту...")
    use_credit(callback.from_user.id)

    prompt = PROMPT_NATAL.format(birth_date=user['birth_date'])
    ans = await ask_groq(prompt, "Ты профессиональный астролог-наталог.")

    await callback.message.answer(ans, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "compat")
async def compat_menu(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Сначала пройди /start", show_alert=True)
        return
    if not user['is_premium'] and user['free_credits'] <= 0:
        await callback.answer("❌ Нет прогнозов", show_alert=True)
        return
    
    await callback.message.answer("💕 Введи знак партнёра (например: Телец, Лев):")
    await callback.answer()
    await dp.message.register(handle_compat_input, F.text)

async def handle_compat_input(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Сначала пройди /start")
        return
    
    my_sign = user.get('zodiac', 'неизвестен')
    partner_sign = message.text.strip()

    await message.answer("💕 Рассчитываю совместимость...")
    use_credit(message.from_user.id)

    prompt = PROMPT_COMPAT.format(sign1=my_sign, sign2=partner_sign)
    ans = await ask_groq(prompt, "Ты астролог-эксперт по совместимости.")

    await message.answer(ans, parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data == "mercury")
async def mercury(callback: types.CallbackQuery):
    await callback.message.answer("🪐 Проверяю статус Меркурия...")
    prompt = "Сейчас ретроградный Меркурий? Дай советы на этот период."
    ans = await ask_groq(prompt, "Ты астролог. Отвечай конкретно.")

    await callback.message.answer(f"🪐 **Ретроградный Меркурий**\n\n{ans}", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "numerology")
async def numerology(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or not user.get('birth_date'):
        await callback.message.answer("📅 Сначала укажи дату рождения")
        await callback.answer()
        return
    
    if not user['is_premium'] and user['free_credits'] <= 0:
        await callback.answer("❌ Нет прогнозов", show_alert=True)
        return
    
    await callback.message.answer("🔢 Рассчитываю число жизненного пути...")
    use_credit(callback.from_user.id)

    prompt = f"Рассчитай нумерологию для даты {user['birth_date']}. Найди число жизненного пути и дай трактовку."
    ans = await ask_groq(prompt, "Ты профессиональный нумеролог.")

    await callback.message.answer(f"🔢 **Нумерология**\n\n{ans}", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "week")
async def week(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Сначала пройди /start", show_alert=True)
        return
    
    if not user['is_premium'] and user['free_credits'] <= 0:
        await callback.answer("❌ Нет прогнозов", show_alert=True)
        return
    
    sign = user.get('zodiac', 'общий')
    await callback.message.answer("📅 Составляю прогноз на неделю...")
    use_credit(callback.from_user.id)

    prompt = f"Составь прогноз на неделю для знака {sign}. Структура: общая тема, карьера, отношения, совет."
    ans = await ask_groq(prompt, "Ты профессиональный астролог.")

    await callback.message.answer(f"📅 **Прогноз на неделю ({sign})**\n\n{ans}", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "buy_premium")
async def buy_premium_callback(callback: types.CallbackQuery):
    prices = [LabeledPrice(label="Premium подписка", amount=100)]
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="💎 Premium доступ",
        description="Безлимитные прогнозы и AI-астролог",
        payload="premium_sub",
        provider_token="",
        currency="XTR",
        prices=prices
    )
    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    set_premium(message.from_user.id)
    user = get_user(message.from_user.id)
    await message.answer("🎉 Оплата прошла! Premium активирован.",
                        parse_mode="Markdown",
                        reply_markup=get_menu_grid(user['name'], 999, None, True))

@dp.callback_query(F.data.startswith("buy_"))
async def buy_pack(callback: types.CallbackQuery):
    pack = callback.data.split("_")[1]
    stars = 50 if pack == "5" else 120
    prices = [LabeledPrice(label=f"Пакет {pack} прогнозов", amount=stars)]
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"💫 Пакет {pack} прогнозов",
        description=f"{pack} дополнительных прогнозов",
        payload=f"pack_{pack}",
        provider_token="",
        currency="XTR",
        prices=prices
    )
    await callback.answer()

@dp.callback_query(F.data == "invite")
async def invite(callback: types.CallbackQuery):
    invite_link = f"https://t.me/{(await bot.me()).username}?start=ref_{callback.from_user.id}"
    await callback.message.answer(f"👥 Твоя реферальная ссылка:\n{invite_link}\n\n🎁 +5 прогнозов за каждого друга!")
    await callback.answer()

@dp.callback_query(F.data == "edit")
async def edit(callback: types.CallbackQuery):
    await callback.message.answer("✏️ Введи новую дату рождения (ДД.ММ.ГГГГ):")
    await callback.answer()
    await dp.message.register(save_edit, F.text)

async def save_edit(message: types.Message, state: FSMContext):
    birth_date = message.text.strip()
    try:
        datetime.strptime(birth_date, "%d.%m.%Y")
        zodiac = calculate_zodiac(birth_date)
        add_or_update_user(message.from_user.id, birth_date=birth_date, zodiac=zodiac)
        await message.answer("✅ Данные обновлены!")
    except:
        await message.answer("❌ Неверный формат. Используй ДД.ММ.ГГГГ")
    await state.clear()

# ==================== WEB SERVER ====================
async def handle_health(request):
    return web.Response(text="OK 🤖")

async def start_web_server(port):
    app = web.Application()
    app.add_routes([web.get('/', handle_health), web.get('/health', handle_health)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"🌐 Health server running on port {port}")

# ==================== ЗАПУСК ====================
async def main():
    init_db()
    logging.info("🚀 Бот запускается...")
    port = int(os.getenv("PORT", 10000))
    await start_web_server(port)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())