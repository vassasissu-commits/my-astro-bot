import asyncio
import logging
import sys
import os
import sqlite3
import random
import hashlib
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# Настройки
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_LINK = os.getenv("PAYMENT_LINK", "https://t.me/YOUR_ADMIN")

if not BOT_TOKEN:
    logging.error("BOT_TOKEN not found")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
DB = "astro.db"
WELCOME_IMG = "https://cdn.pixabay.com/photo/2017/08/16/22/38/universe-2650272_1280.jpg"
ASTRO_AI_IMG = "https://cdn.pixabay.com/photo/2016/02/04/22/38/star-1180004_1280.jpg"

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        "id INTEGER PRIMARY KEY, "
        "telegram_id INTEGER UNIQUE, "
        "username TEXT, "
        "first_name TEXT, "
        "zodiac_sign TEXT, "
        "is_premium INTEGER DEFAULT 0, "
        "daily_credits INTEGER DEFAULT 1, "
        "last_credit_date TEXT, "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ")"
    )
    conn.commit()
    conn.close()

def safe_name(user):
    if user.first_name:
        return user.first_name
    if user.username:
        return user.username
    return "✨"

def get_user(tid):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id=?", (tid,))
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def add_user(tid, username, firstname):
    conn = sqlite3.connect(DB)
    today = datetime.now().strftime("%Y-%m-%d")
    conn.execute(
        "INSERT OR IGNORE INTO users (telegram_id, username, first_name, daily_credits, last_credit_date) VALUES (?, ?, ?, ?, ?)",
        (tid, username, firstname, 1, today)
    )
    conn.commit()
    conn.close()

def get_credits(tid):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cur.execute("SELECT daily_credits, last_credit_date FROM users WHERE telegram_id=?", (tid,))
    row = cur.fetchone()
    if not row or row[1] != today:
        conn.execute(
            "UPDATE users SET daily_credits=1, last_credit_date=? WHERE telegram_id=?",
            (today, tid)
        )
        conn.commit()
        conn.close()
        return 1
    conn.close()
    return row[0] if row[0] else 1

def use_credit(tid):
    conn = sqlite3.connect(DB)
    conn.execute("UPDATE users SET daily_credits=daily_credits-1 WHERE telegram_id=?", (tid,))
    conn.commit()
    conn.close()

def save_sign(tid, sign):
    conn = sqlite3.connect(DB)
    conn.execute("UPDATE users SET zodiac_sign=? WHERE telegram_id=?", (sign, tid))
    if conn.total_changes == 0:
        conn.execute("INSERT INTO users (telegram_id, zodiac_sign) VALUES (?, ?)", (tid, sign))
    conn.commit()
    conn.close()

def main_kb(name, sign, credits):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔮 Гороскоп", callback_data="nav_horoscope")],
        [InlineKeyboardButton(text="🤖 Astro AI", callback_data="nav_astro_ai")],
        [InlineKeyboardButton(text="🌙 Луна", callback_data="nav_moon"),
         InlineKeyboardButton(text="🎱 Шар", callback_data="nav_orb")],
        [InlineKeyboardButton(text="💕 Совместимость", callback_data="nav_compat")],
        [InlineKeyboardButton(text="💎 Premium", callback_data="nav_premium"),
         InlineKeyboardButton(text=f"👤 {name} ({credits})", callback_data="nav_profile")],
    ])

def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ])

def zodiac_kb():
    signs = ["♈ Овен", "♉ Телец", "♊ Близнецы", "♋ Рак", "♌ Лев", "♍ Дева",
             "♎ Весы", "♏ Скорпион", "♐ Стрелец", "♑ Козерог", "♒ Водолей", "♓ Рыбы"]
    kb = [[InlineKeyboardButton(text=s, callback_data=f"sign_{s}")] for s in signs]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

STOICH = {
    "♈ Овен": "fire", "♉ Телец": "earth", "♊ Близнецы": "air", "♋ Рак": "water",
    "♌ Лев": "fire", "♍ Дева": "earth", "♎ Весы": "air", "♏ Скорпион": "water",
    "♐ Стрелец": "fire", "♑ Козерог": "earth", "♒ Водолей": "air", "♓ Рыбы": "water"
}

COMPAT = {
    ("fire", "fire"): "🔥 Огонь+Огонь|Страсть|Конкуренция|Направляйте энергию в общие цели",
    ("fire", "air"): "🔥 Огонь+Воздух|Вдохновение|Нестабильность|Дайте свободу",
    ("fire", "water"): "🔥 Огонь+Вода|Эмоции|Непонимание|Учитесь слушать",
    ("fire", "earth"): "🔥 Огонь+Земля|Энергия+Стабильность|Разный темп|Найдите баланс",
    ("earth", "earth"): "🌍 Земля+Земля|Надёжность|Рутина|Добавляйте новизну",
    ("earth", "water"): "🌍 Земля+Вода|Забота|Замкнутость|Говорите о чувствах",
    ("earth", "air"): "🌍 Земля+Воздух|Идеи+Реализация|Разные ценности|Уважайте различия",
    ("air", "air"): "💨 Воздух+Воздух|Интеллект|Поверхностность|Переходите к делу",
    ("air", "water"): "💨 Воздух+Вода|Творчество|Непонимание|Слушайте сердцем",
    ("water", "water"): "💧 Вода+Вода|Эмпатия|Драма|Сохраняйте границы"
}

ORACLE = [
    "🌟 ДА", "✨ ТОЧНО ДА", "🌕 Луна благоволит", "🌙 Подожди",
    "⏳ Терпение", "🌍 Проверь", "💨 Нет", "🔥 ДЕЙСТВУЙ!",
    "💧 Доверься", "🌌 Спроси позже", "🌀 Отпусти", "🕊️ Венера дарит шанс"
]

def get_moon():
    known = datetime(2000, 1, 6, 18, 14)
    synodic = 29.53058867
    days = (datetime.now() - known).total_seconds() / 86400
    phase = days % synodic
    if phase < 1.84566:
        return "🌑 Новолуние", 1, "🌱 Начинайте"
    elif phase < 5.53699:
        return "🌓 Растущая", int(phase / 1.84566) + 1, "🌿 Действуйте"
    elif phase < 9.22831:
        return "🌗 1-я четверть", 8, "⚖️ Корректируйте"
    elif phase < 12.91963:
        return "🌔 Растущая", 15, "📈 Масштабируйте"
    elif phase < 16.61096:
        return "🌕 Полнолуние", 16, "✨ Завершайте"
    elif phase < 20.30228:
        return "🌖 Убывающая", 17, "🔄 Анализируйте"
    elif phase < 23.99361:
        return "🌘 4-я четверть", 23, "🧹 Очищайте"
    else:
        return "🌒 Убывающая", 24, "🌌 Отдыхайте"

def get_horoscope(sign):
    today = datetime.now().strftime("%Y-%m-%d")
    seed = int(hashlib.md5(f"{today}_{sign}".encode()).hexdigest(), 16)
    rng = random.Random(seed)
    intros = ["Звёзды в гармонии", "Луна обостряет интуицию", "Планеты благоприятствуют", "Космос подсказывает: замедлись"]
    career = ["💼 Удача в системных действиях", "💼 Гибкость вознаграждена", "💼 День для переговоров", "💼 Избегайте спонтанных трат"]
    love = ["❤️ Время для разговоров", "❤️ Избегайте провокаций", "❤️ Романтическая энергия", "❤️ Проявите эмпатию"]
    advice = ["💡 Отпустите уходящее", "💡 Доверяйте интуиции", "💡 Позаботьтесь о здоровье", "💡 Сделайте первый шаг"]
    stones = ["аметист", "хрусталь", "тигровый глаз"]
    colors = ["изумрудный", "голубой", "золотой"]
    return (
        f"🌟 {rng.choice(intros)}\n\n"
        f"{rng.choice(career)}\n\n"
        f"{rng.choice(love)}\n\n"
        f"{rng.choice(advice)}\n\n"
        f"🍀 {rng.choice(stones)} | 🎨 {rng.choice(colors)}"
    )

def astro_ai(sign, name):
    element = STOICH.get(sign, "earth")
    themes = {
        "fire": ["карьера", "лидерство", "творчество"],
        "earth": ["финансы", "здоровье", "стабильность"],
        "air": ["общение", "обучение", "идеи"],
        "water": ["отношения", "эмоции", "интуиция"]
    }
    theme = random.choice(themes[element])
    return (
        f"🔮 **Astro AI для {name}**\n\n"
        f"📅 Фокус: {theme}\n"
        f"⚡ Энергия: {random.choice(['высокая', 'средняя', 'трансформирующая'])}\n"
        f"🎯 Время: {random.choice(['09:00-11:00', '14:00-16:00', '19:00-21:00'])}\n"
        f"⚠️ Остерегайся: {random.choice(['поспешных решений', 'эмоциональных всплесков', 'прокрастинации'])}\n\n"
        f"💡 Совет: {random.choice(['Действуйте решительно', 'Проявите терпение', 'Доверьтесь интуиции', 'Планируйте заранее'])}"
    )

async def send_menu(obj, is_callback=False):
    tid = obj.from_user.id
    user = get_user(tid)
    name = safe_name(obj.from_user)
    sign = user.get("zodiac_sign") if user else None
    credits = get_credits(tid)
    caption = f"🔮 С возвращением, {name}!\n\n⭐ Знак: {sign or 'не выбран'} | 🎁 Прогнозов: {credits}\n\nВыбери раздел ✨"
    keyboard = main_kb(name, sign, credits)
    if is_callback:
        await obj.message.edit_text(caption, reply_markup=keyboard)
        await obj.answer()
    else:
        try:
            await obj.answer_photo(photo=WELCOME_IMG, caption=caption, reply_markup=keyboard)
        except Exception:
            await obj.answer(caption, reply_markup=keyboard)

@dp.message(Command("start"))
async def cmd_start(message):
    add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await send_menu(message)

@dp.message(F.text == "🏠 Главное меню")
async def cmd_home(message):
    await send_menu(message)

@dp.callback_query(F.data == "back_main")
async def callback_back(callback):
    await send_menu(callback, is_callback=True)

@dp.callback_query(F.data == "nav_horoscope")
async def callback_horoscope_menu(callback):
    await callback.message.edit_text("🔮 **Выбери знак**", reply_markup=zodiac_kb())
    await callback.answer()

@dp.callback_query(F.data.startswith("sign_"))
async def callback_show_horoscope(callback):
    sign = callback.data.replace("sign_", "")
    credits = get_credits(callback.from_user.id)
    if credits <= 0:
        await callback.answer("⚠️ Бесплатный прогноз закончился! Premium = безлимит.", show_alert=True)
        return
    use_credit(callback.from_user.id)
    save_sign(callback.from_user.id, sign)
    text = f"{sign}\n\n{get_horoscope(sign)}\n\n🎁 Осталось: {credits - 1}"
    await callback.message.edit_text(text, reply_markup=back_kb())
    await callback.answer()

@dp.callback_query(F.data == "nav_astro_ai")
async def callback_astro_ai(callback):
    user = get_user(callback.from_user.id)
    name = safe_name(callback.from_user)
    sign = user.get("zodiac_sign") if user else None
    if not sign:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔮 Выбрать знак", callback_data="nav_horoscope")]
        ])
        await callback.message.edit_text("🤖 **Astro AI**\n\nСначала выбери знак в 🔮 Гороскоп!", reply_markup=kb)
        await callback.answer()
        return
    prediction = astro_ai(sign, name)
    try:
        await callback.message.answer_photo(
            photo=ASTRO_AI_IMG,
            caption=prediction,
            reply_markup=back_kb(),
            parse_mode="Markdown"
        )
        await callback.message.delete()
    except Exception:
        await callback.message.edit_text(prediction, reply_markup=back_kb(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "nav_moon")
async def callback_moon(callback):
    phase, day, rec = get_moon()
    text = f"🌙 **Фаза**: {phase}\n📅 **День**: {day}\n💡 **Совет**: {rec}"
    await callback.message.edit_text(text, reply_markup=back_kb(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "nav_orb")
async def callback_orb(callback):
    await callback.message.edit_text(f"🎱 {random.choice(ORACLE)}", reply_markup=back_kb())
    await callback.answer()

@dp.callback_query(F.data == "nav_compat")
async def callback_compat_menu(callback):
    text = "💕 **Совместимость**\n\nНапиши: `Имя Знак`\nПример: `Света Близнецы`"
    await callback.message.edit_text(text, reply_markup=back_kb(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "nav_premium")
async def callback_premium(callback):
    text = (
        "💎 **Premium**\n\n"
        "📊 Натальная карта\n"
        "💕 Детальная совместимость\n"
        "🌌 Прогноз транзитов\n"
        "🔮 Персональные советы\n"
        "⚡ Безлимитные прогнозы\n\n"
        "💰 299₽/мес"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=PAYMENT_LINK)],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data == "nav_profile")
async def callback_profile(callback):
    user = get_user(callback.from_user.id)
    if not user:
        return
    text = (
        f"👤 **Профиль**\n\n"
        f"Имя: {user.get('first_name') or 'Не указано'}\n"
        f"♐ Знак: {user.get('zodiac_sign') or 'Не выбран'}\n"
        f"💎 Premium: {'Да' if user.get('is_premium') else 'Нет'}\n"
        f"🎁 Прогнозов: {get_credits(callback.from_user.id)}"
    )
    await callback.message.edit_text(text, reply_markup=back_kb(), parse_mode="Markdown")
    await callback.answer()

@dp.message()
async def handle_compat_message(message):
    text = message.text.strip().lower()
    sign_map = {
        "овен": "♈ Овен", "телец": "♉ Телец", "близнецы": "♊ Близнецы", "рак": "♋ Рак",
        "лев": "♌ Лев", "дева": "♍ Дева", "весы": "♎ Весы", "скорпион": "♏ Скорпион",
        "стрелец": "♐ Стрелец", "козерог": "♑ Козерог", "водолей": "♒ Водолей", "рыбы": "♓ Рыбы"
    }
    found_sign = None
    for key, full_sign in sign_map.items():
        if key in text:
            found_sign = full_sign
            break
    if not found_sign:
        return
    user = get_user(message.from_user.id)
    user_sign = user.get("zodiac_sign") if user else None
    if not user_sign:
        await message.answer("❓ Сначала выбери свой знак в меню 🔮", reply_markup=main_kb("User", None, 1))
        return
    el1 = STOICH[user_sign]
    el2 = STOICH[found_sign]
    data = COMPAT.get((el1, el2)) or COMPAT.get((el2, el1)) or "💫 Уникальный союз|Гармония|Нет|Доверяйте"
    parts = data.split("|")
    vibe, plus, minus, advice = parts[0], parts[1], parts[2], parts[3]
    name_part = text.replace(found_sign, "").replace(
        next((k for k, v in sign_map.items() if v == found_sign), ""), ""
    ).strip().capitalize()
    partner_name = name_part if name_part else "Партнёр"
    result = (
        f"💕 {user.get('first_name', 'Вы')} ({user_sign}) + {partner_name} ({found_sign})\n\n"
        f"**{vibe}**\n"
        f"✅ {plus}\n"
        f"⚠️ {minus}\n"
        f"💡 {advice}"
    )
    await message.answer(
        result,
        reply_markup=main_kb(user.get('first_name', 'User'), user_sign, get_credits(message.from_user.id)),
        parse_mode="Markdown"
    )

async def health_check(request):
    return web.Response(text="OK")

async def start_web_server(port):
    app = web.Application()
    app.add_routes([web.get('/', health_check), web.get('/health', health_check)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Web server started on port {port}")

async def run_polling():
    while True:
        try:
            logging.info("Starting polling...")
            await dp.start_polling(bot)
            break
        except Exception as e:
            logging.error(f"Polling error: {e}")
            await asyncio.sleep(10)

async def main():
    logging.info("Bot starting...")
    init_db()
    try:
        me = await bot.me()
        logging.info(f"Authorized as @{me.username}")
    except Exception as e:
        logging.error(f"Authorization error: {e}")
        return
    port = int(os.getenv("PORT", 10000))
    await start_web_server(port)
    await run_polling()

if __name__ == "__main__":
    asyncio.run(main())