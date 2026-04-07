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

# ==================== FSM (машина состояний) ====================
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
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 600,
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
СТРУКТУРА ОТВЕТА (строго следуй!):
🌙 Гороскоп для {name} на {date}
⭐ Энергетика дня
2-3 предложения об общей атмосфере дня
💼 Карьера/финансы
2-3 предложения о работе и деньгах
❤️ Отношения
2-3 предложения о любви и общении
💡 Совет
1-2 предложения с практической рекомендацией
Правила:
- Пиши конкретно, без воды
- Используй астрологические термины (Луна, Меркурий, аспекты)
- Тон: поддерживающий, но честный
- Длина: 150-250 слов"""

PROMPT_NATAL = """Ты профессиональный астролог.
Составь НАТАЛЬНУЮ КАРТУ для человека, родившегося {birth_date}.
СТРУКТУРА:
🌌 Натальная карта
♈ Твой знак зодиака: [знак]
🌙 Луна: [эмоциональная природа]
☀️ Солнце: [основная энергия]
💫 Основные аспекты: [2-3 ключевых аспекта]
🎯 Твои сильные стороны: [список]
⚠️ Зоны роста: [список]
Длина: 200-300 слов"""

PROMPT_COMPAT = """Ты астролог-эксперт по совместимости.
Рассчитай СОВМЕСТИМОСТЬ: {sign1} и {sign2}.
СТРУКТУРА:
💕 Совместимость: {sign1} + {sign2}
🔥 Общая вибрация: [описание]
✅ Сильные стороны союза: [2-3 пункта]
⚠️ Зоны риска: [2-3 пункта]
💡 Совет звёзд: [практический совет]
Длина: 150-200 слов"""

PROMPT_PERSONAL = """Ты Ведана — опытная гадалка и астролог с многолетним стажем.
Составь ЛИЧНОЕ ПРЕДСКАЗАНИЕ для {name}, родившегося {birth_date} (знак {sign}).

СТРУКТУРА:
🔮 Личное предсказание от Веданы

✨ Что говорят звёзды именно тебе
3-4 предложения о текущем периоде жизни

💫 Ближайшие события
2-3 конкретных предсказания на ближайшие недели

🌙 Тайное послание
Мистическое послание от вселенной

💡 Мой совет как гадалки
Личная рекомендация от Веданы

Тон: мудрый, загадочный, но заботливый. Пиши как настоящая ведунья.
Длина: 250-350 слов"""

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

# ==================== МЕНЮ (ОБНОВЛЁННОЕ!) ====================
def get_menu_grid(name, credits, next_free_time, is_prem):
    # Рассчитываем время до следующего бесплатного
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
                timer_text = "✨ Прогнозов: ∞" if is_prem else f"✨ Прогнозов: {credits}"
        except:
            timer_text = f"✨ Прогнозов: {credits}"
    else:
        timer_text = f"✨ Прогнозов: {credits}"
    
    prem_text = "💎 PREMIUM (Активен)" if is_prem else "💎 Получить PREMIUM — 100 ⭐"
    prem_data = "premium_active" if is_prem else "buy_premium"

    # СЕТКА 2 КОЛОНКИ + НИЖНЕЕ МЕНЮ
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # Основные функции
        [InlineKeyboardButton(text="🌟 Гороскоп", callback_data="horoscope"),
         InlineKeyboardButton(text="🌌 Натальная карта", callback_data="natal")],
        
        [InlineKeyboardButton(text="🃏 Расклад Таро", callback_data="tarot"),
         InlineKeyboardButton(text="💕 Совместимость", callback_data="compat")],
        
        [InlineKeyboardButton(text="🔮 Вопрос астрологу", callback_data="ask_ai"),
         InlineKeyboardButton(text="🪐 Ретро Меркурий", callback_data="mercury")],
        
        [InlineKeyboardButton(text="🔢 Нумерология", callback_data="numerology"),
         InlineKeyboardButton(text="📅 Прогноз на неделю", callback_data="week")],
        
        # Покупки
        [InlineKeyboardButton(text="💫 5 прогнозов — 50 ⭐", callback_data="buy_5"),
         InlineKeyboardButton(text="💫 15 прогнозов — 120 ⭐", callback_data="buy_15")],
        
        # Premium
        [InlineKeyboardButton(text=prem_text, callback_data=prem_data)],
        
        # Личное предсказание (за премиум)
        [InlineKeyboardButton(text="🔮 Личное предсказание от Веданы", callback_data="personal_prediction")],
        
        # Рефералка и настройки
        [InlineKeyboardButton(text="👥 Пригласить друга", callback_data="invite")],
        [InlineKeyboardButton(text="✏️ Изменить данные", callback_data="edit")],
        
        # Нижнее меню навигации
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        [InlineKeyboardButton(text="🔄 Старт", callback_data="start_bot")]
    ])
    
    return keyboard

# Нижнее меню для всех сообщений
def get_bottom_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        [InlineKeyboardButton(text="🔄 Старт", callback_data="start_bot")]
    ])

# ==================== ОНБОРДИНГ ====================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user = get_user(message.from_user.id)
    
    if user and user.get('name') and user.get('birth_date'):
        # Уже зарегистрирован — показываем меню
        await message.answer("🔮 Добро пожаловать в мир астрологии!", 
                           reply_markup=get_menu_grid(user['name'], user['free_credits'], 
                                                    user.get('next_free_time'), user['is_premium']))
    else:
        # Новый пользователь — начинаем онбординг С ФОТО
        welcome_text = (
            "🌌 **Я — Ведана.**\n\n"
            "Звёзды уже чувствуют твоё присутствие, но чтобы карты не ошиблись, назови себя.\n\n"
            "Напиши мне: **имя**, **число**, **месяц** и **год рождения**.\n"
            "Я бережно сохраню эти данные, чтобы каждый гороскоп, расклад Таро "
            "и нумерологический прогноз были составлены лично для тебя.\n\n"
            "Как только ответишь, меню откроет свои тайны… 🔮"
        )
        
        # Отправка фото Vedana
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
            await message.answer("⚠️ Не удалось загрузить изображение Веданы, но магия продолжается...\n\n" + welcome_text, parse_mode="Markdown")
        
        await message.answer("✨ Как тебя зовут?", reply_markup=get_bottom_menu())
        await state.set_state(OnboardingState.name)

@dp.message(OnboardingState.name)
async def onboarding_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(name=name)
    await message.answer(f"✨ Прекрасное имя, {name}!\n\n"
                        f"📅 Введи дату рождения в формате ДД.ММ.ГГГГ\n"
                        f"Например: 15.03.1989", reply_markup=get_bottom_menu())
    await state.set_state(OnboardingState.birth_date)

@dp.message(OnboardingState.birth_date)
async def onboarding_birthdate(message: types.Message, state: FSMContext):
    birth_date = message.text.strip()
    # Простая валидация
    try:
        datetime.strptime(birth_date, "%d.%m.%Y")
    except:
        await message.answer("❌ Неверный формат. Используй ДД.ММ.ГГГГ\nНапример: 15.03.1989", 
                           reply_markup=get_bottom_menu())
        return

    data = await state.get_data()
    name = data.get('name', message.from_user.first_name)

    # Определяем знак зодиака
    zodiac = calculate_zodiac(birth_date)

    # Сохраняем в БД
    add_or_update_user(message.from_user.id, name, birth_date, zodiac)

    await message.answer(f"♐ Твой знак: {zodiac}\n\n"
                        f"Теперь выбери раздел:", 
                        reply_markup=get_menu_grid(name, 1, None, False))
    await state.clear()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def calculate_zodiac(birth_date):
    """Определяет знак зодиака по дате рождения"""
    try:
        date = datetime.strptime(birth_date, "%d.%m.%Y")
        day, month = date.day, date.month
        
        if (month == 3 and day >= 21) or (month == 4 and day <= 19): return "♈ Овен"
        if (month == 4 and day >= 20) or (month == 5 and day <= 20): return "♉ Телец"
        if (month == 5 and day >= 21) or (month == 6 and day <= 20): return "♊ Близнецы"
        if (month == 6 and day >= 21) or (month == 7 and day <= 22): return "♋ Рак"
        if (month == 7 and day >= 23) or (month == 8 and day <= 22): return "♌ Лев"
        if (month == 8 and day >= 23) or (month == 9 and day <= 22): return "♍ Дева"
        if (month == 9 and day >= 23) or (month == 10 and day <= 22): return "♎ Весы"
        if (month == 10 and day >= 23) or (month == 11 and day <= 21): return "♏ Скорпион"
        if (month == 11 and day >= 22) or (month == 12 and day <= 21): return "♐ Стрелец"
        if (month == 12 and day >= 22) or (month == 1 and day <= 19): return "♑ Козерог"
        if (month == 1 and day >= 20) or (month == 2 and day <= 18): return "♒ Водолей"
        return "♓ Рыбы"
    except:
        return "Не определён"

# ==================== ОБРАБОТЧИКИ КНОПОК ====================
@dp.callback_query(F.data == "noop")
async def noop(callback: types.CallbackQuery):
    await callback.answer()

@dp.callback_query(F.data == "main_menu")
async def main_menu(callback: types.CallbackQuery):
    """Возврат в главное меню"""
    user = get_user(callback.from_user.id)
    if user:
        await callback.message.edit_text("🔮 **Главное меню**", 
                                       reply_markup=get_menu_grid(user['name'], user['free_credits'], 
                                                                user.get('next_free_time'), user['is_premium']))
    await callback.answer()

@dp.callback_query(F.data == "start_bot")
async def start_bot_callback(callback: types.CallbackQuery):
    """Кнопка Старт"""
    user = get_user(callback.from_user.id)
    if user and user.get('name') and user.get('birth_date'):
        await callback.message.edit_text("🔮 Добро пожаловать в мир астрологии!", 
                                       reply_markup=get_menu_grid(user['name'], user['free_credits'], 
                                                                user.get('next_free_time'), user['is_premium']))
    else:
        await callback.message.edit_text("✨ Добро пожаловать в AstroAI!\n\n"
                                       "Я твой персональный астролог и провидец.\n"
                                       "Получи бесплатный астропрогноз прямо сейчас!\n\n"
                                       "✨ Как тебя зовут?")
        await callback.answer()
        await dp.message.register(onboarding_name, F.text)
    await callback.answer()

@dp.callback_query(F.data == "horoscope")
async def horoscope(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Сначала пройди /start", show_alert=True)
        return
    
    if not user['is_premium'] and user['free_credits'] <= 0:
        await callback.answer("❌ Нет бесплатных прогнозов. Купи пакет!", show_alert=True)
        return

    use_credit(callback.from_user.id)
    await callback.message.answer("🌟 Составляю гороскоп...", reply_markup=get_bottom_menu())

    sign = user.get('zodiac', 'Овен')
    name = user.get('name', 'друг')
    today = datetime.now().strftime("%d.%m.%Y")

    prompt = PROMPT_HOROSCOPE.format(sign=sign, name=name, date=today)
    ans = await ask_groq(prompt, "Ты профессиональный астролог с 20-летним опытом.")

    await callback.message.answer(ans, parse_mode="Markdown", reply_markup=get_bottom_menu())
    await callback.answer()

@dp.callback_query(F.data == "tarot")
async def tarot(callback: types.CallbackQuery):
    card = random.choice(TAROT_CARDS)
    await callback.message.answer(f"🃏 Твоя карта: {card['name']}\n\n{card['desc']}", 
                                parse_mode="Markdown", reply_markup=get_bottom_menu())
    await callback.answer()

@dp.callback_query(F.data == "ask_ai")
async def ask_ai_menu(callback: types.CallbackQuery):
    await callback.message.answer("🔮 Напиши свой вопрос астрологу:", reply_markup=get_bottom_menu())
    await callback.answer()
    await dp.message.register(handle_ai_question, F.text)

async def handle_ai_question(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Сначала пройди /start", reply_markup=get_bottom_menu())
        return
    
    if not user['is_premium'] and user['free_credits'] <= 0:
        await message.answer("❌ Нет кредитов. Купи пакет!", reply_markup=get_bottom_menu())
        return

    await message.answer("🤖 Составляю ответ...", reply_markup=get_bottom_menu())

    sign = user.get('zodiac', 'общий')
    prompt = f"Вопрос от {sign}: {message.text}"
    ans = await ask_groq(prompt, "Ты профессиональный астролог. Отвечай конкретно и по делу.")

    await message.answer(f"🔮 **Ответ астролога:**\n\n{ans}", parse_mode="Markdown", reply_markup=get_bottom_menu())
    use_credit(message.from_user.id)
    await state.clear()

@dp.callback_query(F.data == "natal")
async def natal(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or not user.get('birth_date'):
        await callback.message.answer("📅 Сначала укажи дату рождения через /start", reply_markup=get_bottom_menu())
        await callback.answer()
        return
    
    await callback.message.answer("🌌 Составляю натальную карту...", reply_markup=get_bottom_menu())

    prompt = PROMPT_NATAL.format(birth_date=user['birth_date'])
    ans = await ask_groq(prompt, "Ты профессиональный астролог-наталог.")

    await callback.message.answer(ans, parse_mode="Markdown", reply_markup=get_bottom_menu())
    await callback.answer()

@dp.callback_query(F.data == "compat")
async def compat_menu(callback: types.CallbackQuery):
    await callback.message.answer("💕 Введи знак партнёра (например: Телец, Лев, Скорпион):", 
                                reply_markup=get_bottom_menu())
    await callback.answer()
    await dp.message.register(handle_compat_input, F.text)

async def handle_compat_input(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Сначала пройди /start", reply_markup=get_bottom_menu())
        return
    
    my_sign = user.get('zodiac', 'неизвестен')
    partner_sign = message.text.strip()

    await message.answer("💕 Рассчитываю совместимость...", reply_markup=get_bottom_menu())

    prompt = PROMPT_COMPAT.format(sign1=my_sign, sign2=partner_sign)
    ans = await ask_groq(prompt, "Ты астролог-эксперт по совместимости.")

    await message.answer(ans, parse_mode="Markdown", reply_markup=get_bottom_menu())
    await state.clear()

@dp.callback_query(F.data == "mercury")
async def mercury(callback: types.CallbackQuery):
    await callback.message.answer("🪐 Проверяю статус Меркурия...", reply_markup=get_bottom_menu())
    prompt = "Сейчас ретроградный Меркурий? Дай советы на этот период."
    ans = await ask_groq(prompt, "Ты астролог. Отвечай конкретно.")

    await callback.message.answer(f"🪐 **Ретроградный Меркурий**\n\n{ans}", 
                                parse_mode="Markdown", reply_markup=get_bottom_menu())
    await callback.answer()

@dp.callback_query(F.data == "numerology")
async def numerology(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or not user.get('birth_date'):
        await callback.message.answer("📅 Сначала укажи дату рождения", reply_markup=get_bottom_menu())
        await callback.answer()
        return
    
    await callback.message.answer("🔢 Рассчитываю число жизненного пути...", reply_markup=get_bottom_menu())

    prompt = f"Рассчитай нумерологию для даты {user['birth_date']}. Найди число жизненного пути и дай трактовку."
    ans = await ask_groq(prompt, "Ты профессиональный нумеролог.")

    await callback.message.answer(f"🔢 **Нумерология**\n\n{ans}", parse_mode="Markdown", reply_markup=get_bottom_menu())
    await callback.answer()

@dp.callback_query(F.data == "week")
async def week(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Сначала пройди /start", show_alert=True)
        return
    
    sign = user.get('zodiac', 'общий')
    await callback.message.answer("📅 Составляю прогноз на неделю...", reply_markup=get_bottom_menu())

    prompt = f"Составь прогноз на неделю для знака {sign}. Структура: общая тема, карьера, отношения, совет."
    ans = await ask_groq(prompt, "Ты профессиональный астролог.")

    await callback.message.answer(f"📅 **Прогноз на неделю ({sign})**\n\n{ans}", 
                                parse_mode="Markdown", reply_markup=get_bottom_menu())
    await callback.answer()

@dp.callback_query(F.data == "personal_prediction")
async def personal_prediction(callback: types.CallbackQuery):
    """Личное предсказание от Веданы (только для PREMIUM)"""
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Сначала пройди /start", show_alert=True)
        return
    
    if not user['is_premium']:
        await callback.message.answer(
            "🔮 **Личное предсказание от Веданы**\n\n"
            "Это эксклюзивная услуга доступна только обладателям PREMIUM.\n\n"
            "Ведана составит для тебя персональное предсказание с учётом:\n"
            "• Твоей даты рождения\n"
            "• Знака зодиака\n"
            "• Текущего положения звёзд\n\n"
            "💎 Приобрети PREMIUM за 100 ⭐ и получи безлимитный доступ ко всем функциям!",
            parse_mode="Markdown",
            reply_markup=get_bottom_menu()
        )
        await callback.answer()
        return

    await callback.message.answer("🔮 Ведана составляет твоё личное предсказание...", reply_markup=get_bottom_menu())

    sign = user.get('zodiac', 'Овен')
    name = user.get('name', 'друг')
    birth_date = user.get('birth_date', '')

    prompt = PROMPT_PERSONAL.format(sign=sign, name=name, birth_date=birth_date)
    ans = await ask_groq(prompt, "Ты Ведана — опытная гадалка и астролог с многолетним стажем.")

    await callback.message.answer(ans, parse_mode="Markdown", reply_markup=get_bottom_menu())
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
    await callback.message.answer(f"👥 Твоя реферальная ссылка:\n{invite_link}\n\n+1 прогноз за каждого друга!",
                                reply_markup=get_bottom_menu())
    await callback.answer()

@dp.callback_query(F.data == "edit")
async def edit(callback: types.CallbackQuery):
    await callback.message.answer("✏️ Введи новую дату рождения (ДД.ММ.ГГГГ):", reply_markup=get_bottom_menu())
    await callback.answer()
    await dp.message.register(save_edit, F.text)

async def save_edit(message: types.Message, state: FSMContext):
    birth_date = message.text.strip()
    try:
        datetime.strptime(birth_date, "%d.%m.%Y")
        zodiac = calculate_zodiac(birth_date)
        add_or_update_user(message.from_user.id, birth_date=birth_date, zodiac=zodiac)
        await message.answer("✅ Данные обновлены!", reply_markup=get_bottom_menu())
    except:
        await message.answer("❌ Неверный формат. Используй ДД.ММ.ГГГГ", reply_markup=get_bottom_menu())
    await state.clear()

# ==================== WEB SERVER ДЛЯ RENDER ====================
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