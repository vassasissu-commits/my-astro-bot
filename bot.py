import asyncio
import logging
import os
import sqlite3
import random
import aiohttp
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiohttp import web

# ================= НАСТРОЙКИ =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not BOT_TOKEN or not GROQ_API_KEY:
    logging.error("❌ Ошибка: Проверь переменные окружения")
    exit()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
DB_NAME = "astro_users.db"

# ================= БАЗА ДАННЫХ =================
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
        is_premium INTEGER DEFAULT 0
    )''')
    conn.commit()
    conn.close()

def get_user(tid):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT * FROM users WHERE telegram_id=?", (tid,)).fetchone()
    conn.close()
    return dict(user) if user else None

def add_or_update_user(tid, name, birth_date=None, zodiac=None):
    conn = sqlite3.connect(DB_NAME)
    today = datetime.now().strftime("%Y-%m-%d")
    user = conn.execute("SELECT * FROM users WHERE telegram_id=?", (tid,)).fetchone()
    
    if not user:
        conn.execute("INSERT INTO users (telegram_id, name, birth_date, zodiac, free_credits, last_login) VALUES (?, ?, ?, ?, 1, ?)",
                     (tid, name, birth_date, zodiac, today))
    else:
        if user['last_login'] != today:
            conn.execute("UPDATE users SET free_credits=1, last_login=?, name=? WHERE telegram_id=?", (today, name, tid))
        else:
            conn.execute("UPDATE users SET name=?, birth_date=COALESCE(?, birth_date), zodiac=COALESCE(?, zodiac) WHERE telegram_id=?",
                         (name, birth_date, zodiac, tid))
    conn.commit()
    conn.close()

def use_credit(tid):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("UPDATE users SET free_credits = free_credits - 1 WHERE telegram_id=?", (tid,))
    conn.commit()
    conn.close()

def set_premium(tid):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("UPDATE users SET is_premium=1 WHERE telegram_id=?", (tid,))
    conn.commit()
    conn.close()

# ================= GROQ AI (с системным промптом!) =================
async def ask_groq(question, user_sign=None):
    system_prompt = """Ты профессиональный астролог с 20-летним опытом. 
Твоя специализация: натальные карты, транзиты, синастрия, прогнозирование.
Отвечай уверенно, без удивления вопросам про астрологию — это твоя работа.
Стиль: мудрый, поддерживающий, но честный.
Длина ответа: 100-200 слов."""
    
    if user_sign:
        question = f"Знак пользователя: {user_sign}. Вопрос: {question}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": question}
                    ],
                    "max_tokens": 400
                }
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data['choices'][0]['message']['content']
                return f"Ошибка AI: {resp.status}"
    except Exception as e:
        return f"Ошибка: {e}"

# ================= ТАРО =================
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

# ================= МЕНЮ (кнопки на всю ширину!) =================
def get_menu(c_name, credits, is_prem):
    prem_text = "💎 PREMIUM (Активен)" if is_prem else "💎 Получить PREMIUM — 100 ⭐"
    prem_data = "premium_active" if is_prem else "buy_premium"
    
    # Каждая кнопка в отдельной строке = на всю ширину
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"👋 Привет, {c_name}!", callback_data="noop")],
        [InlineKeyboardButton(text=f"✨ Прогнозов: {credits}", callback_data="noop")],
        
        [InlineKeyboardButton(text="🌟 Гороскоп сегодня", callback_data="horoscope")],
        [InlineKeyboardButton(text="🌌 Натальная карта", callback_data="natal")],
        [InlineKeyboardButton(text="🃏 Расклад Таро", callback_data="tarot")],
        [InlineKeyboardButton(text="💕 Совместимость", callback_data="compat")],
        [InlineKeyboardButton(text="🔮 Вопрос Астрологу", callback_data="ask_ai")],
        [InlineKeyboardButton(text="🪐 Ретро Меркурий", callback_data="mercury")],
        [InlineKeyboardButton(text="🔢 Нумерология", callback_data="numerology")],
        [InlineKeyboardButton(text="📅 Прогноз на неделю", callback_data="week")],
        
        [InlineKeyboardButton(text="💫 5 прогнозов — 50 ⭐", callback_data="buy_5")],
        [InlineKeyboardButton(text="💫 15 прогнозов — 120 ⭐", callback_data="buy_15")],
        
        [InlineKeyboardButton(text=prem_text, callback_data=prem_data)],
        
        [InlineKeyboardButton(text="👥 Пригласить друга", callback_data="invite")],
        [InlineKeyboardButton(text="✏️ Изменить данные", callback_data="edit")]
    ])

# ================= ОБРАБОТЧИКИ =================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    add_or_update_user(message.from_user.id, message.from_user.first_name)
    user = get_user(message.from_user.id)
    await message.answer("🔮 Добро пожаловать в мир астрологии!", reply_markup=get_menu(user['name'], user['free_credits'], user['is_premium']))

@dp.callback_query(F.data == "noop")
async def noop(callback: types.CallbackQuery):
    await callback.answer()

@dp.callback_query(F.data == "horoscope")
async def horoscope(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user['is_premium'] and user['free_credits'] <= 0:
        await callback.answer("❌ Нет бесплатных прогнозов. Купи пакет!", show_alert=True)
        return
    
    use_credit(callback.from_user.id)
    await callback.message.answer("🌟 Генерирую гороскоп...")
    
    sign = user.get('zodiac') or "общий"
    ans = await ask_groq(f"Составь гороскоп на сегодня для знака {sign}", sign)
    await callback.message.answer(f"🌟 **Гороскоп ({sign})**\n\n{ans}", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "tarot")
async def tarot(callback: types.CallbackQuery):
    card = random.choice(TAROT_CARDS)
    await callback.message.answer(f"🃏 **Твоя карта:** {card['name']}\n\n{card['desc']}", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "ask_ai")
async def ask_ai_menu(callback: types.CallbackQuery):
    await callback.message.answer("🔮 Напиши свой вопрос астрологу:")
    await callback.answer()
    
    # Ждём сообщение с вопросом
    @dp.message()
    async def handle_ai_question(message: types.Message):
        user = get_user(message.from_user.id)
        if not user['is_premium'] and user['free_credits'] <= 0:
            await message.answer("❌ Нет кредитов. Купи пакет!")
            return
        
        await message.answer("🤖 Астролог думает...")
        sign = user.get('zodiac')
        ans = await ask_groq(message.text, sign)
        await message.answer(f"🔮 **Ответ астролога:**\n\n{ans}", parse_mode="Markdown")
        use_credit(message.from_user.id)
        
        # Удаляем этот обработчик, чтобы не срабатывал постоянно
        dp.message.unregister(handle_ai_question)

@dp.callback_query(F.data == "natal")
async def natal(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user.get('birth_date'):
        await callback.message.answer("📅 Сначала укажи дату рождения (ДД.ММ.ГГГГ)")
        await callback.answer()
        return
    
    await callback.message.answer("🌌 Генерирую натальную карту...")
    ans = await ask_groq(f"Рассчитай натальную карту для человека, родившегося {user['birth_date']}. Знак: {user.get('zodiac', 'неизвестен')}", user.get('zodiac'))
    await callback.message.answer(f"🌌 **Натальная карта**\n\n{ans}", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "compat")
async def compat(callback: types.CallbackQuery):
    await callback.message.answer("💕 Введи знак партнёра для расчёта совместимости:")
    await callback.answer()
    
    @dp.message()
    async def handle_compat_input(message: types.Message):
        user = get_user(message.from_user.id)
        my_sign = user.get('zodiac', 'неизвестен')
        partner_sign = message.text.strip()
        
        await message.answer("💕 Рассчитываю совместимость...")
        ans = await ask_groq(f"Совместимость {my_sign} и {partner_sign}", my_sign)
        await message.answer(f"💕 **Совместимость: {my_sign} + {partner_sign}**\n\n{ans}", parse_mode="Markdown")
        dp.message.unregister(handle_compat_input)

@dp.callback_query(F.data == "mercury")
async def mercury(callback: types.CallbackQuery):
    ans = await ask_groq("Сейчас ретроградный Меркурий? Какие советы?", None)
    await callback.message.answer(f"🪐 **Ретроградный Меркурий**\n\n{ans}", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "numerology")
async def numerology(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user.get('birth_date'):
        await callback.message.answer("📅 Сначала укажи дату рождения")
        await callback.answer()
        return
    
    await callback.message.answer("🔢 Рассчитываю число жизненного пути...")
    ans = await ask_groq(f"Рассчитай нумерологию для даты {user['birth_date']}", None)
    await callback.message.answer(f"🔢 **Нумерология**\n\n{ans}", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "week")
async def week(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    sign = user.get('zodiac', 'общий')
    await callback.message.answer("📅 Генерирую прогноз на неделю...")
    ans = await ask_groq(f"Прогноз на неделю для знака {sign}", sign)
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
    await message.answer("🎉 **Оплата прошла!** Premium активирован.", 
                        parse_mode="Markdown",
                        reply_markup=get_menu(user['name'], 999, True))

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
    await callback.message.answer(f"👥 Твоя реферальная ссылка:\n{invite_link}\n\n+1 прогноз за каждого друга!")
    await callback.answer()

@dp.callback_query(F.data == "edit")
async def edit(callback: types.CallbackQuery):
    await callback.message.answer("✏️ Введи дату рождения (ДД.ММ.ГГГГ):")
    await callback.answer()
    
    @dp.message()
    async def save_edit(message: types.Message):
        add_or_update_user(message.from_user.id, message.from_user.first_name, birth_date=message.text)
        await message.answer("✅ Данные сохранены!")
        dp.message.unregister(save_edit)

# ================= WEB SERVER ДЛЯ RENDER =================
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

# ================= ЗАПУСК =================
async def main():
    init_db()
    logging.info("🚀 Бот запускается...")
    port = int(os.getenv("PORT", 10000))
    await start_web_server(port)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())