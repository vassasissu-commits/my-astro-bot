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

# 🔧 НАСТРОЙКИ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_LINK = os.getenv("PAYMENT_LINK", "https://t.me/YOUR_ADMIN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

if not BOT_TOKEN:
    logging.error("❌ BOT_TOKEN не найден!")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
DB_PATH = "astro.db"

# 🖼️ КАРТИНКИ
WELCOME_IMG = "https://cdn.pixabay.com/photo/2017/08/16/22/38/universe-2650272_1280.jpg"
ASTRO_AI_IMG = "https://cdn.pixabay.com/photo/2016/02/04/22/38/star-1180004_1280.jpg"

# 🗄️ БАЗА ДАННЫХ
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        telegram_id INTEGER UNIQUE,
        username TEXT,
        first_name TEXT,
        zodiac_sign TEXT,
        is_premium INTEGER DEFAULT 0,
        daily_credits INTEGER DEFAULT 1,
        last_credit_date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def get_safe_name(user_obj):
    if user_obj.first_name:
        return user_obj.first_name
    if user_obj.username:
        return user_obj.username
    return "✨"

def get_user_dict(tid):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id=?", (tid,))
    res = c.fetchone()
    conn.close()
    if res:
        return dict(res)
    return None

def add_user(tid, uname, fname):
    conn = sqlite3.connect(DB_PATH)
    today = datetime.now().strftime("%Y-%m-%d")
    conn.execute(
        "INSERT OR IGNORE INTO users (telegram_id, username, first_name, daily_credits, last_credit_date) VALUES (?,?,?,?,?)",
        (tid, uname, fname, 1, today)
    )
    conn.commit()
    conn.close()

def get_credits(tid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT daily_credits, last_credit_date FROM users WHERE telegram_id=?", (tid,))
    res = c.fetchone()
    if not res or res[1] != today:
        conn.execute("UPDATE users SET daily_credits=1, last_credit_date=? WHERE telegram_id=?", (today, tid))
        conn.commit()
        conn.close()
        return 1
    conn.close()
    return res[0] if res[0] else 1

def use_credit(tid):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET daily_credits=daily_credits-1 WHERE telegram_id=?", (tid,))
    conn.commit()
    conn.close()

def save_sign(tid, sign):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET zodiac_sign=? WHERE telegram_id=?", (sign, tid))
    if conn.total_changes == 0:
        conn.execute("INSERT INTO users (telegram_id, zodiac_sign) VALUES (?,?)", (tid, sign))
    conn.commit()
    conn.close()

# ⌨️ КЛАВИАТУРЫ
def main_kb(name, sign, credits):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔮 Гороскоп на день", callback_data="nav_horoscope")],
        [InlineKeyboardButton(text="🤖 Astro AI — умный прогноз", callback_data="nav_astro_ai")],
        [InlineKeyboardButton(text="🌙 Луна", callback_data="nav_moon"),
         InlineKeyboardButton(text="🎱 Магический шар", callback_data="nav_orb")],
        [InlineKeyboardButton(text="💕 Совместимость", callback_data="nav_compat")],
        [InlineKeyboardButton(text="💎 Premium", callback_data="nav_premium"),
         InlineKeyboardButton(text=f"👤 {name} ({credits}🎁)", callback_data="nav_profile")],
    ])

def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_main")]
    ])

def zodiac_kb():
    signs = ["♈ Овен", "♉ Телец", "♊ Близнецы", "♋ Рак", "♌ Лев", "♍ Дева",
             "♎ Весы", "♏ Скорпион", "♐ Стрелец", "♑ Козерог", "♒ Водолей", "♓ Рыбы"]
    kb = [[InlineKeyboardButton(text=s, callback_data=f"sign_{s}")] for s in signs]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# 🌍 ДАННЫЕ
STOICH = {
    "♈ Овен": "fire", "♉ Телец": "earth", "♊ Близнецы": "air", "♋ Рак": "water",
    "♌ Лев": "fire", "♍ Дева": "earth", "♎ Весы": "air", "♏ Скорпион": "water",
    "♐ Стрелец": "fire", "♑ Козерог": "earth", "♒ Водолей": "air", "♓ Рыбы": "water"
}

COMPAT = {
    ("fire", "fire"): {"v": "🔥 Огонь + Огонь", "p": "Страсть и драйв", "m": "Конкуренция", "a": "Направляйте энергию в общие цели"},
    ("fire", "air"): {"v": "🔥 Огонь + Воздух", "p": "Вдохновение", "m": "Нестабильность", "a": "Дайте друг другу свободу"},
    ("fire", "water"): {"v": "🔥 Огонь + Вода", "p": "Глубина эмоций", "m": "Непонимание", "a": "Учитесь слушать"},
    ("fire", "earth"): {"v": "🔥 Огонь + Земля", "p": "Энергия + Стабильность", "m": "Разный темп", "a": "Найдите баланс"},
    ("earth", "earth"): {"v": "🌍 Земля + Земля", "p": "Надёжность", "m": "Рутина", "a": "Добавляйте новизну"},
    ("earth", "water"): {"v": "🌍 Земля + Вода", "p": "Забота и уют", "m": "Замкнутость", "a": "Говорите о чувствах"},
    ("earth", "air"): {"v": "🌍 Земля + Воздух", "p": "Идеи + Реализация", "m": "Разные ценности", "a": "Уважайте различия"},
    ("air", "air"): {"v": "💨 Воздух + Воздух", "p": "Интеллект", "m": "Поверхностность", "a": "Переходите к делу"},
    ("air", "water"): {"v": "💨 Воздух + Вода", "p": "Творчество", "m": "Непонимание", "a": "Слушайте сердцем"},
    ("water", "water"): {"v": "💧 Вода + Вода", "p": "Эмпатия", "m": "Драма", "a": "Сохраняйте границы"}
}

ORACLE = [
    "🌟 Звёзды говорят: ДА", "✨ Судьба: ТОЧНО ДА", "🌕 Луна благоволит",
    "🌙 Подожди", "⏳ Терпение", "🌍 Проверь детали", "💨 Нет",
    "🔥 ДЕЙСТВУЙ!", "💧 Доверься интуиции", "🌌 Спроси позже",
    "🌀 Отпусти старое", "🕊️ Венера дарит шанс"
]

def get_moon():
    known = datetime(2000, 1, 6, 18, 14)
    syn = 29.53058867
    days = (datetime.now() - known).total_seconds() / 86400
    ph = days % syn
    if ph < 1.84566:
        return "🌑 Новолуние", 1, "🌱 Начинайте новое"
    elif ph < 5.53699:
        return "🌓 Растущая", int(ph / 1.84566) + 1, "🌿 Действуйте"
    elif ph < 9.22831:
        return "🌗 1-я четверть", 8, "⚖️ Корректируйте"
    elif ph < 12.91963:
        return "🌔 Растущая", 15, "📈 Масштабируйте"
    elif ph < 16.61096:
        return "🌕 Полнолуние", 16, "✨ Завершайте"
    elif ph < 20.30228:
        return "🌖 Убывающая", 17, "🔄 Анализируйте"
    elif ph < 23.99361:
        return "🌘 4-я четверть", 23, "🧹 Очищайте"
    else:
        return "🌒 Убывающая", 24, "🌌 Отдыхайте"

def get_horoscope(sign):
    today = datetime.now().strftime("%Y-%m-%d")
    seed = int(hashlib.md5(f"{today}_{sign}".encode()).hexdigest(), 16)
    rng = random.Random(seed)
    I = ["Звёзды выстраиваются в гармонию", "Луна обостряет интуицию",
         "Планеты благоприятствуют смелым шагам", "Космос подсказывает: замедлись"]
    C = ["💼 Удача в системных действиях", "💼 Гибкость будет вознаграждена",
         "💼 Отличный день для переговоров", "💼 Избегайте спонтанных трат"]
    L = ["❤️ Время для искренних разговоров", "❤️ Избегайте провокаций",
         "❤️ Романтическая энергия на пике", "❤️ Проявите эмпатию"]
    A = ["💡 Отпустите уходящее", "💡 Доверяйте интуиции",
         "💡 Позаботьтесь о здоровье", "💡 Сделайте первый шаг"]
    stones = ["аметист", "хрусталь", "тигровый глаз"]
    colors = ["изумрудный", "голубой", "золотой"]
    return (f"🌟 {rng.choice(I)}\n\n"
            f"{rng.choice(C)}\n\n"
            f"{rng.choice(L)}\n\n"
            f"{rng.choice(A)}\n\n"
            f"🍀 Талисман: {rng.choice(stones)} | 🎨 Цвет: {rng.choice(colors)}")

def astro_ai(sign, name):
    el = STOICH.get(sign, "earth")
    themes = {
        "fire": ["карьера", "лидерство", "творчество"],
        "earth": ["финансы", "здоровье", "стабильность"],
        "air": ["общение", "обучение", "идеи"],
        "water": ["отношения", "эмоции", "интуиция"]
    }
    t = random.choice(themes[el])
    p1 = (f"🔮 **Astro AI для {name}**\n\n"
          f"📅 Фокус: {t}\n"
          f"⚡ Энергия: {random.choice(['высокая', 'средняя', 'трансформирующая'])}\n"
          f"🎯 Время: {random.choice(['09:00-11:00', '14:00-16:00', '19:00-21:00'])}\n"
          f"⚠️ Остерегайся: {random.choice(['поспешных решений', 'эмоциональных всплесков', 'прокрастинации'])}\n\n"
          f"💡 Совет: {random.choice(['Действуйте решительно', 'Проявите терпение', 'Доверьтесь интуиции', 'Планируйте заранее'])}")
    p2 = (f"🌌 **Космический анализ {name}**\n\n"
          f"🪐 Планета: {random.choice(['Меркурий', 'Венера', 'Марс', 'Юпитер'])}\n"
          f"💫 Аспект: {random.choice(['гармоничный', 'напряжённый', 'трансформирующий'])}\n\n"
          f"📊 Сферы:\n"
          f"• {t.title()}: {random.randint(65, 95)}%\n"
          f"• Здоровье: {random.randint(65, 95)}%\n"
          f"• Отношения: {random.randint(65, 95)}%\n\n"
          f"🎁 Подарок дня: {random.choice(['неожиданная встреча', 'финансовая удача', 'важный инсайт'])}")
    return random.choice([p1, p2])

# 🎯 ОБРАБОТЧИКИ
async def send_menu(cb_or_msg, is_cb=False):
    tid = cb_or_msg.from_user.id
    user = get_user_dict(tid)
    name = get_safe_name(cb_or_msg.from_user)
    sign = user.get("zodiac_sign") if user else None
    credits = get_credits(tid)
    caption = f"🔮 С возвращением, {name}!\n\n⭐ Знак: {sign or 'не выбран'} | 🎁 Прогнозов: {credits}\n\nВыбери раздел ✨"
    kb = main_kb(name, sign, credits)
    if is_cb:
        await cb_or_msg.message.edit_text(caption, reply_markup=kb)
        await cb_or_msg.answer()
    else:
        try:
            await cb_or_msg.answer_photo(photo=WELCOME_IMG, caption=caption, reply_markup=kb)
        except Exception:
            await cb_or_msg.answer(caption, reply_markup=kb)

@dp.message(Command("start"))
async def cmd_start(msg):
    add_user(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    await send_menu(msg)

@dp.message(F.text == "🏠 Главное меню")
async def cmd_home(msg):
    await send_menu(msg)

@dp.callback_query(F.data == "back_main")
async def back_main(cb):
    await send_menu(cb, is_cb=True)

@dp.callback_query(F.data == "nav_horoscope")
async def nav_horoscope(cb):
    await cb.message.edit_text("🔮 **Выбери свой знак**\n\nЯ рассчитаю персональный прогноз:", reply_markup=zodiac_kb())
    await cb.answer()

@dp.callback_query(F.data.startswith("sign_"))
async def show_horoscope(cb):
    sign = cb.data.replace("sign_", "")
    cr = get_credits(cb.from_user.id)
    if cr <= 0:
        await cb.answer("⚠️ Бесплатный прогноз на сегодня закончился! Premium даёт безлимит.", show_alert=True)
        return
    use_credit(cb.from_user.id)
    save_sign(cb.from_user.id, sign)
    await cb.message.edit_text(f"{sign}\n\n{get_horoscope(sign)}\n\n🎁 Осталось: {cr - 1}", reply_markup=back_kb())
    await cb.answer()

@dp.callback_query(F.data == "nav_astro_ai")
async def nav_ai(cb):
    user = get_user_dict(cb.from_user.id)
    name = get_safe_name(cb.from_user)
    sign = user.get("zodiac_sign") if user else None
    if not sign:
        await cb.message.edit_text(
            "🤖 **Astro AI**\n\nСначала выбери знак в 🔮 Гороскоп, чтобы я составил прогноз!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔮 Выбрать знак", callback_data="nav_horoscope")]
            ])
        )
        await cb.answer()
        return
    pred = astro_ai(sign, name)
    try:
        await cb.message.answer_photo(photo=ASTRO_AI_IMG, caption=pred, reply_markup=back_kb(), parse_mode="Markdown")
        await cb.message.delete()
    except Exception:
        await cb.message.edit_text(pred, reply_markup=back_kb(), parse_mode="Markdown")
    await cb.answer()

@dp.callback_query(F.data == "nav_moon")
async def nav_moon(cb):
    ph, day, rec = get_moon()
    await cb.message.edit_text(f"🌙 **Фаза**: {ph}\n📅 **Лунный день**: {day}\n💡 **Рекомендация**: {rec}",
                               reply_markup=back_kb(), parse_mode="Markdown")
    await cb.answer()

@dp.callback_query(F.data == "nav_orb")
async def nav_orb(cb):
    await cb.message.edit_text(f"🎱 {random.choice(ORACLE)}", reply_markup=back_kb())
    await cb.answer()

@dp.callback_query(F.data == "nav_compat")
async def nav_compat(cb):
    await cb.message.edit_text(
        "💕 **Совместимость по стихиям**\n\nНапиши имя и знак партнёра.\nПример: `Света Близнецы` или `Макс ♏`",
        reply_markup=back_kb(), parse_mode="Markdown"
    )
    await cb.answer()

@dp.callback_query(F.data == "nav_premium")
async def nav_prem(cb):
    txt = ("💎 **Premium-доступ**\n\n"
           "📊 Полная натальная карта\n"
           "💕 Детальная совместимость\n"
           "🌌 Прогноз транзитов\n"
           "🔮 Персональные рекомендации\n"
           "⚡ Безлимитные прогнозы\n\n"
           "💰 299₽/мес\n\n"
           "Нажми для оплаты:")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=PAYMENT_LINK)],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ])
    await cb.message.edit_text(txt, reply_markup=kb)
    await cb.answer()

@dp.callback_query(F.data == "nav_profile")
async def nav_prof(cb):
    u = get_user_dict(cb.from_user.id)
    if not u:
        return
    txt = (f"👤 **Профиль**\n\n"
           f"Имя: {u.get('first_name') or 'Не указано'}\n"
           f"♐ Знак: {u.get('zodiac_sign') or 'Не выбран'}\n"
           f"💎 Premium: {'Да' if u.get('is_premium') else 'Нет'}\n"
           f"🎁 Прогнозов сегодня: {get_credits(cb.from_user.id)}")
    await cb.message.edit_text(txt, reply_markup=back_kb(), parse_mode="Markdown")
    await cb.answer()

@dp.message()
async def handle_compat(msg):
    txt = msg.text.strip().lower()
    smap = {
        "овен": "♈ Овен", "телец": "♉ Телец", "близнецы": "♊ Близнецы", "рак": "♋ Рак",
        "лев": "♌ Лев", "дева": "♍ Дева", "весы": "♎ Весы", "скорпион": "♏ Скорпион",
        "стрелец": "♐ Стрелец", "козерог": "♑ Козерог", "водолей": "♒ Водолей", "рыбы": "♓ Рыбы"
    }
    found = None
    for k, v in smap.items():
        if k in txt:
            found = v
            break
    if not found:
        return
    u = get_user_dict(msg.from_user.id)
    us = u.get("zodiac_sign") if u else None
    if not us:
        await msg.answer("❓ Сначала выбери свой знак в меню 🔮", reply_markup=main_kb("User", None, 1))
        return
    el1 = STOICH[us]
    el2 = STOICH[found]
    data = COMPAT.get((el1, el2)) or COMPAT.get((el2, el1)) or {"v": "💫 Уникальный союз", "p": "Гармония", "m": "Нет", "a": "Доверяйте"}
    name_part = msg.text.replace(found, "").replace(next((k for k, v in smap.items() if v == found), ""), "").strip().capitalize()
    name = name_part or "Партнёр"
    result_txt = (f"💕 {u.get('first_name', 'Вы')} ({us}) + {name} ({found})\n\n"
                  f"**{data['v']}**\n"
                  f"✅ {data['p']}\n"
                  f"⚠️ {data['m']}\n"
                  f"💡 {data['a']}")
    await msg.answer(result_txt, reply_markup=main_kb(u.get('first_name', 'User'), us, get_credits(msg.from_user.id)), parse_mode="Markdown")

# 🌐 RENDER WEB & LOOP
async def health(req):
    return web.Response(text="OK 🤖")

async def start_web(port):
    app = web.Application()
    app.add_routes([web.get('/', health), web.get('/health', health)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site
