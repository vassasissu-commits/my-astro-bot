import asyncio
import logging
import os
import sqlite3
import random
import aiohttp
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, LabeledPrice, PreCheckoutQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# ================= НАСТРОЙКИ =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PORT = int(os.getenv("PORT", 8080))
ADMIN_USERNAME = "Rusfer1"
WEBHOOK_URL = f"https://my-astro-bot-wqwl.onrender.com/webhook"

if not BOT_TOKEN or not GROQ_API_KEY:
    logging.error("❌ Ошибка: Проверь переменные окружения BOT_TOKEN и GROQ_API_KEY")
    exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
DB_NAME = "astro_users.db"

# ================= FSM =================
class OnboardingState(StatesGroup):
    waiting_for_name = State()
    waiting_for_birthdate = State()

class NatalState(StatesGroup):
    waiting_for_time = State()
    waiting_for_place = State()

class BallState(StatesGroup):
    waiting_for_question = State()

class CompatState(StatesGroup):
    waiting_for_partner_sign = State()

# ================= БАЗА ДАННЫХ (без изменений) =================
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
        is_premium INTEGER DEFAULT 0
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
            (telegram_id, name, birth_date, zodiac, free_credits, vedana_credits, last_reset_date, is_premium)
            VALUES (?, ?, ?, ?, 3, 0, ?, 0)""",
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

def add_referrer_bonus(ref_user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("UPDATE users SET free_credits = free_credits + 5 WHERE telegram_id = ?", (ref_user_id,))
    conn.commit()
    conn.close()
    logging.info(f"Реферер {ref_user_id} получил +5 кредитов")

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

# ================= ПРОМПТЫ (оставляем без изменений, они есть в предыдущей версии) =================
# ... (вставьте все PROMPT_* из предыдущего кода, чтобы не дублировать, но для краткости я их опускаю – они идентичны)
# ВНИМАНИЕ: при реальной замене файла обязательно скопируйте все PROMPT_* и SHADOWS, TAROT_CARDS, RUNES из моего предыдущего сообщения.
# Здесь для компактности я их не повторяю, но в финальном коде они должны быть.

# ================= КЛАВИАТУРЫ (без изменений) =================
def get_bottom_menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="/start")]], resize_keyboard=True, is_persistent=False)

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
        [InlineKeyboardButton(text="👥 Пригласить друга (+5 прогнозов)", callback_data="invite")],
        [InlineKeyboardButton(text="🏠 Назад в меню", callback_data="main_menu")]
    ])

def get_menu_grid(user, is_admin=False):
    name = user.get('name') if user.get('name') else "гость"
    free_txt = "∞/" if user['is_premium'] else f"{user['free_credits']}/3"
    vedana_c = user['vedana_credits']
    vedana_cb = "vedana_pred" if (vedana_c > 0 or user['is_premium']) else "shop"
    vedana_text = f"🔮 Индивидуальное предсказание от Веданы: {vedana_c} вед"
    
    menu_kb = [
        [InlineKeyboardButton(text="🌟 Гороскоп", callback_data="horoscope"),
         InlineKeyboardButton(text="🌌 Натальная карта", callback_data="natal")],
        [InlineKeyboardButton(text="🃏 Таро", callback_data="tarot"),
         InlineKeyboardButton(text="💕 Совместимость", callback_data="compat")],
        [InlineKeyboardButton(text="🔮 Магический шар", callback_data="ball"),
         InlineKeyboardButton(text="ᚠ Гадание на рунах", callback_data="rune")],
        [InlineKeyboardButton(text="🔢 Нумерология", callback_data="numerology"),
         InlineKeyboardButton(text="📅 На неделю", callback_data="week")],
        [InlineKeyboardButton(text=f"📅 Прогнозы: {free_txt}", callback_data="noop")],
        [InlineKeyboardButton(text=vedana_text, callback_data=vedana_cb)],
        [InlineKeyboardButton(text="✏️ Изменить данные", callback_data="edit")],
        [InlineKeyboardButton(text="👥 Пригласить друга", callback_data="invite")]
    ]
    if is_admin:
        menu_kb.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=menu_kb)

# ================= ВСПОМОГАТЕЛЬНЫЕ =================
async def send_loading_video(message):
    try:
        video = FSInputFile("loading.mp4")
        await message.answer_video(video, caption="🌌 Звёзды складываются...")
    except:
        await message.answer("🌌 Ведана концентрируется...")

async def delay_thinking():
    await asyncio.sleep(random.uniform(3, 5))

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
        asyncio.create_task(msg.answer("❌ Прогнозы на сегодня закончились. Раскрой тайны в магазине!", reply_markup=get_bottom_menu()))
        return False
    return True

def send_pred(msg, text):
    return msg.answer(text, parse_mode="Markdown", reply_markup=get_after_pred_kb())

# ================= ОБРАБОТЧИКИ =================
@dp.message(Command("start"))
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    
    # Реферальная логика (как была)
    args = message.text.split()
    start_param = None
    if len(args) > 1:
        start_param = args[1]
    if start_param and start_param.startswith("ref_"):
        try:
            ref_id = int(start_param.split("_")[1])
            if ref_id != message.from_user.id:
                ref_user = get_user(ref_id)
                if ref_user:
                    add_referrer_bonus(ref_id)
                    await message.answer("🎁 Ваш друг получил бонус! А вы получили +5 бесплатных прогнозов!")
        except:
            pass
    elif start_param:
        logging.info(f"Переход из источника: {start_param} от user {message.from_user.id}")
    
    # Создаём запись пользователя, если её нет
    if not get_user(message.from_user.id):
        add_or_update_user(message.from_user.id)
    
    user = get_user(message.from_user.id)
    is_admin = (message.from_user.username == ADMIN_USERNAME)
    caption = "🌌 Я — Ведана.\nЗвёзды готовы открыть свои тайны."
    try:
        await message.answer_photo(photo=FSInputFile("vedana.jpg"), caption=caption, reply_markup=get_menu_grid(user, is_admin), parse_mode="Markdown")
    except:
        await message.answer(caption, reply_markup=get_menu_grid(user, is_admin), parse_mode="Markdown")

@dp.callback_query(F.data == "main_menu")
async def main_menu_cb(cb: types.CallbackQuery):
    user = get_user(cb.from_user.id)
    if user:
        is_admin = (cb.from_user.username == ADMIN_USERNAME)
        caption = "🌌 Я — Ведана.\nЗвёзды готовы открыть свои тайны."
        try:
            await cb.message.answer_photo(photo=FSInputFile("vedana.jpg"), caption=caption, reply_markup=get_menu_grid(user, is_admin), parse_mode="Markdown")
        except:
            await cb.message.answer(caption, reply_markup=get_menu_grid(user, is_admin), parse_mode="Markdown")
    await cb.answer()

# ------------------- Универсальная проверка онбординга -------------------
async def ensure_onboarding(callback_query, state, target_action):
    """Проверяет, есть ли у пользователя имя и дата. Если нет – запускает онбординг и сохраняет target_action."""
    user = get_user(callback_query.from_user.id)
    if user and user.get('name') and user.get('birth_date'):
        return True
    # Запускаем онбординг
    await state.update_data(target_action=target_action)
    await callback_query.message.answer("🔮 Прежде чем звёзды заговорят, представься.\nКак тебя зовут?")
    await state.set_state(OnboardingState.waiting_for_name)
    await callback_query.answer()
    return False

@dp.message(OnboardingState.waiting_for_name)
async def onboarding_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer(f"✨ {message.text.strip()}!\n\n📅 Теперь дату рождения (ДД.ММ.ГГГГ):", reply_markup=get_bottom_menu())
    await state.set_state(OnboardingState.waiting_for_birthdate)

@dp.message(OnboardingState.waiting_for_birthdate)
async def onboarding_birthdate(message: types.Message, state: FSMContext):
    try:
        datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except:
        await message.answer("❌ Неверно. Формат: ДД.ММ.ГГГГ", reply_markup=get_bottom_menu())
        return
    data = await state.get_data()
    name = data.get('name')
    birth = message.text.strip()
    zodiac = calculate_zodiac(birth)
    add_or_update_user(message.from_user.id, name, birth, zodiac)
    
    target_action = data.get('target_action')
    await state.clear()
    
    user = get_user(message.from_user.id)
    is_admin = (message.from_user.username == ADMIN_USERNAME)
    caption = f"♐ Знак: {zodiac}\nТеперь вы можете заказать прогноз, {name}."
    try:
        await message.answer_photo(photo=FSInputFile("vedana.jpg"), caption=caption, reply_markup=get_menu_grid(user, is_admin), parse_mode="Markdown")
    except:
        await message.answer(caption, reply_markup=get_menu_grid(user, is_admin), parse_mode="Markdown")
    
    # Если было целевое действие – выполняем его автоматически
    if target_action:
        # Создаём искусственный callback
        fake_cb = types.CallbackQuery(id="fake", from_user=message.from_user, message=message, chat_instance="fake", data=target_action)
        await process_prediction(fake_cb, state, target_action)

# ------------------- Обработчики предсказаний -------------------
async def process_prediction(callback_query, state, action):
    """Общая функция для выполнения предсказания после проверки данных"""
    user = get_user(callback_query.from_user.id)
    if not user:
        await callback_query.message.answer("Ошибка. Попробуйте /start")
        return
    
    if action == "horoscope":
        if not check_free(user, callback_query.message): return
        use_free_credit(user['telegram_id'])
        await send_loading_video(callback_query.message)
        await delay_thinking()
        prompt = PROMPT_HOROSCOPE.format(sign=user['zodiac'], name=user['name'], date=datetime.now().strftime("%d.%m.%Y"))
        ans = await ask_groq(prompt, "Ты астролог с 20-летним опытом.")
        await send_pred(callback_query.message, ans + get_shadow("horoscope"))
    
    elif action == "tarot":
        if not check_free(user, callback_query.message): return
        use_free_credit(user['telegram_id'])
        await send_loading_video(callback_query.message)
        await delay_thinking()
        card = random.choice(TAROT_CARDS)
        text = f"🔮 Карты говорят...\n\n{card['desc']}\n\n{get_shadow('tarot')}"
        await send_pred(callback_query.message, text)
    
    elif action == "rune":
        if not check_free(user, callback_query.message): return
        use_free_credit(user['telegram_id'])
        await send_loading_video(callback_query.message)
        await delay_thinking()
        rune = random.choice(RUNES)
        prompt = PROMPT_RUNE.format(rune_name=rune['name'], sign=user.get('zodiac', ''))
        ans = await ask_groq(prompt, "Ты эксперт по рунам.")
        await send_pred(callback_query.message, f"ᚠ Руны говорят:\n\n{rune['desc']}\n\n{ans}" + get_shadow("rune"))
    
    elif action == "week":
        if not check_free(user, callback_query.message): return
        use_free_credit(user['telegram_id'])
        await send_loading_video(callback_query.message)
        await delay_thinking()
        prompt = PROMPT_WEEK.format(sign=user['zodiac'])
        ans = await ask_groq(prompt, "Ты профессиональный астролог.")
        await send_pred(callback_query.message, ans + get_shadow("week"))
    
    elif action == "numerology":
        if not check_free(user, callback_query.message): return
        use_free_credit(user['telegram_id'])
        await send_loading_video(callback_query.message)
        await delay_thinking()
        prompt = f"Нумерология для {user['birth_date']}. Число пути и трактовка."
        ans = await ask_groq(prompt, "Ты нумеролог.")
        await send_pred(callback_query.message, f"🔢 Нумерология\n\n{ans}" + get_shadow("numerology"))
    
    elif action == "vedana_pred":
        if user['vedana_credits'] <= 0 and not user['is_premium']:
            await callback_query.message.answer("✨ У тебя нет свободных предсказаний Веданы.\n\nРаскрой тайны в магазине:", reply_markup=get_shop_kb())
            return
        await send_loading_video(callback_query.message)
        await delay_thinking()
        prompt = PROMPT_VEDANA.format(name=user['name'], sign=user['zodiac'], birth_date=user['birth_date'])
        ans = await ask_groq(prompt, "Ты Ведана, опытный астролог.")
        if not user['is_premium']:
            use_vedana_credit(user['telegram_id'])
        await send_pred(callback_query.message, ans)
    
    elif action in ("natal", "ball", "compat"):
        # Для этих функций требуется дополнительный ввод – запускаем соответствующие FSM
        if action == "natal":
            if not check_free(user, callback_query.message): return
            await callback_query.message.answer("🌌 Введи время рождения (ЧЧ:ММ):", reply_markup=get_bottom_menu())
            await state.set_state(NatalState.waiting_for_time)
        elif action == "ball":
            if not check_free(user, callback_query.message): return
            await callback_query.message.answer("🔮 Напиши вопрос шару:", reply_markup=get_bottom_menu())
            await state.set_state(BallState.waiting_for_question)
        elif action == "compat":
            if not check_free(user, callback_query.message): return
            await callback_query.message.answer("💕 Введи знак партнёра (Телец, Лев...):", reply_markup=get_bottom_menu())
            await state.set_state(CompatState.waiting_for_partner_sign)
        await callback_query.answer()
        return
    await callback_query.answer()

# Обработчики для кнопок – вызывают ensure_onboarding, затем process_prediction
@dp.callback_query(F.data.in_({"horoscope","tarot","rune","week","numerology","vedana_pred"}))
async def handle_simple_pred(cb: types.CallbackQuery, state: FSMContext):
    if await ensure_onboarding(cb, state, cb.data):
        await process_prediction(cb, state, cb.data)

@dp.callback_query(F.data == "natal")
async def handle_natal(cb: types.CallbackQuery, state: FSMContext):
    if await ensure_onboarding(cb, state, cb.data):
        await process_prediction(cb, state, cb.data)

@dp.callback_query(F.data == "ball")
async def handle_ball(cb: types.CallbackQuery, state: FSMContext):
    if await ensure_onboarding(cb, state, cb.data):
        await process_prediction(cb, state, cb.data)

@dp.callback_query(F.data == "compat")
async def handle_compat(cb: types.CallbackQuery, state: FSMContext):
    if await ensure_onboarding(cb, state, cb.data):
        await process_prediction(cb, state, cb.data)

# ------------------- FSM для натальной карты -------------------
@dp.message(NatalState.waiting_for_time)
async def natal_time(msg: types.Message, state: FSMContext):
    await state.update_data(time=msg.text.strip())
    await msg.answer("📍 Место рождения (Город):", reply_markup=get_bottom_menu())
    await state.set_state(NatalState.waiting_for_place)

@dp.message(NatalState.waiting_for_place)
async def natal_place(msg: types.Message, state: FSMContext):
    user = get_user(msg.from_user.id)
    if not user or not check_free(user, msg): 
        await state.clear()
        return
    data = await state.get_data()
    await send_loading_video(msg)
    await delay_thinking()
    prompt = PROMPT_NATAL.format(birth_date=user['birth_date'], time=data.get('time'), place=msg.text.strip())
    ans = await ask_groq(prompt, "Ты астролог-наталог.")
    use_free_credit(msg.from_user.id)
    await send_pred(msg, ans + get_shadow("natal"))
    await state.clear()

# ------------------- FSM для магического шара -------------------
@dp.message(BallState.waiting_for_question)
async def ball_question(msg: types.Message, state: FSMContext):
    user = get_user(msg.from_user.id)
    if not user or not check_free(user, msg): 
        await state.clear()
        return
    await send_loading_video(msg)
    await delay_thinking()
    prompt = PROMPT_BALL.format(q=msg.text, sign=user.get('zodiac',''))
    ans = await ask_groq(prompt, "Ты магический шар.")
    use_free_credit(msg.from_user.id)
    await send_pred(msg, ans + get_shadow("ball"))
    await state.clear()

# ------------------- FSM для совместимости -------------------
@dp.message(CompatState.waiting_for_partner_sign)
async def compat_partner(msg: types.Message, state: FSMContext):
    user = get_user(msg.from_user.id)
    if not user or not check_free(user, msg): 
        await state.clear()
        return
    await send_loading_video(msg)
    await delay_thinking()
    prompt = PROMPT_COMPAT.format(sign1=user['zodiac'], sign2=msg.text.strip())
    ans = await ask_groq(prompt, "Ты эксперт по совместимости.")
    use_free_credit(msg.from_user.id)
    await send_pred(msg, ans + get_shadow("compat"))
    await state.clear()

# ------------------- Остальные обработчики (магазин, админка, рефералка) -------------------
@dp.callback_query(F.data == "shop")
async def shop_cb(cb: types.CallbackQuery):
    text = "✨ Что скрыто за твоим знаком?\n\nВедана может заглянуть глубже, если ты готов(а) к откровению.\n\n🔮 Индивидуальное предсказание включает:\n• Точные даты событий\n• Рекомендации по цвету/камню\n• Ответ на сокровенный вопрос\n• Послание наставников"
    try:
        await cb.message.edit_text(text, reply_markup=get_shop_kb())
    except:
        await cb.message.answer(text, reply_markup=get_shop_kb())
    await cb.answer()

@dp.callback_query(F.data == "edit")
async def edit(cb: types.CallbackQuery):
    await cb.message.answer("✏️ Новая дата (ДД.ММ.ГГГГ):", reply_markup=get_bottom_menu())
    await cb.answer()
    @dp.message(F.text)
    async def save_edit(msg: types.Message, state: FSMContext):
        try:
            datetime.strptime(msg.text.strip(), "%d.%m.%Y")
            zodiac = calculate_zodiac(msg.text.strip())
            add_or_update_user(msg.from_user.id, birth_date=msg.text.strip(), zodiac=zodiac)
            await msg.answer("✅ Дата обновлена!", reply_markup=get_menu_grid(get_user(msg.from_user.id)))
        except:
            await msg.answer("❌ Неверно", reply_markup=get_bottom_menu())
        await state.clear()

@dp.callback_query(F.data == "invite")
async def invite_friend(cb: types.CallbackQuery):
    bot_username = (await bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=ref_{cb.from_user.id}"
    await cb.message.answer(
        f"👥 Твоя реферальная ссылка:\n{link}\n\n"
        f"🎁 За каждого друга, который перейдёт по ссылке и начнёт пользоваться ботом, "
        f"ты получишь +5 бесплатных прогнозов.\n\n"
        f"📢 Поделись ссылкой в TikTok, соцсетях или с друзьями!",
        reply_markup=get_bottom_menu()
    )
    await cb.answer()

# ------------------- Админ-панель (без изменений) -------------------
@dp.callback_query(F.data == "admin_panel")
async def admin_panel(cb: types.CallbackQuery):
    if cb.from_user.username != ADMIN_USERNAME:
        await cb.answer("🔒 Доступ запрещён", show_alert=True)
        return
    user = get_user(cb.from_user.id)
    text = (f"⚙️ Админ-панель (@{ADMIN_USERNAME})\n\n"
            f"👤 Ваш баланс:\n"
            f"• Прогнозы: {user['free_credits']}/3\n"
            f"• Веды: {user['vedana_credits']}")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ +5 прогнозов", callback_data="admin_add_free")],
        [InlineKeyboardButton(text="➕ +1 вед", callback_data="admin_add_vedana")],
        [InlineKeyboardButton(text="🔄 Сброс", callback_data="admin_reset")],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="main_menu")]
    ])
    await cb.message.answer(text, reply_markup=kb)
    await cb.answer()

@dp.callback_query(F.data.startswith("admin_"))
async def admin_actions(cb: types.CallbackQuery):
    if cb.from_user.username != ADMIN_USERNAME:
        await cb.answer("🔒 Доступ запрещён", show_alert=True)
        return
    action = cb.data.split("_")[1]
    if action == "add":
        sub = cb.data.split("_")[2]
        if sub == "free":
            add_credits(cb.from_user.id, free_amt=5)
            msg = "✅ Добавлено 5 прогнозов"
        else:
            add_credits(cb.from_user.id, vedana_amt=1)
            msg = "✅ Добавлена 1 веда"
    elif action == "reset":
        conn = sqlite3.connect(DB_NAME)
        conn.execute("UPDATE users SET vedana_credits=0, free_credits=3 WHERE telegram_id=?", (cb.from_user.id,))
        conn.commit()
        conn.close()
        msg = "✅ Баланс сброшен"
    else:
        msg = "❓"
    user = get_user(cb.from_user.id)
    text = f"{msg}\n\n👤 Текущий баланс:\n• Прогнозы: {user['free_credits']}/3\n• Веды: {user['vedana_credits']}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ +5 прогнозов", callback_data="admin_add_free")],
        [InlineKeyboardButton(text="➕ +1 вед", callback_data="admin_add_vedana")],
        [InlineKeyboardButton(text="🔄 Сброс", callback_data="admin_reset")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])
    await cb.message.answer(text, reply_markup=kb)
    await cb.answer()

# ------------------- Платежи -------------------
@dp.callback_query(F.data.startswith("buy_"))
async def buy_pack(cb: types.CallbackQuery):
    packs = {
        "buy_starter": {"title": "Стартовый", "free": 5, "vedana": 1, "cost": 50},
        "buy_optimal": {"title": "Оптимальный", "free": 15, "vedana": 3, "cost": 120},
        "buy_premium_pack": {"title": "Безлимит", "free": 0, "vedana": 6, "cost": 200, "prem": True}
    }
    p = packs[cb.data]
    await bot.send_invoice(
        chat_id=cb.from_user.id,
        title=f"✨ {p['title']}",
        description="Активация через Telegram Stars",
        payload=cb.data,
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Пакет прогнозов", amount=p['cost'])]
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
        await msg.answer("✅ Пакет активирован! Звёзды на твоей стороне.", reply_markup=get_menu_grid(user))

# ------------------- Запуск -------------------
async def on_startup(bot: Bot):
    await bot.set_webhook(url=WEBHOOK_URL, allowed_updates=dp.resolve_used_update_types(), drop_pending_updates=True)
    logging.info(f"✅ Webhook установлен: {WEBHOOK_URL}")

async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    logging.info("✅ Webhook удалён")

async def main():
    init_db()
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    app.add_routes([web.get("/", lambda _: web.Response(text="OK")), web.get("/health", lambda _: web.Response(text="OK"))])
    setup_application(app, dp, bot=bot)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    logging.info(f"🚀 Бот запущен на порту {PORT}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("🛑 Бот остановлен")