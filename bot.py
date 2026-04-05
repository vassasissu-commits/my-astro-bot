import asyncio
import logging
import sys
import os
import sqlite3
import random
import re
import hashlib
from datetime import datetime
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

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден в переменных окружения!"); sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 🗄️ БАЗА ДАННЫХ
DB_PATH = "astro.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, telegram_id INTEGER UNIQUE, username TEXT, first_name TEXT,
        birth_date TEXT, birth_time TEXT, birth_place TEXT, zodiac_sign TEXT,
        is_premium INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit(); conn.close()

async def get_user(tid):
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    c = conn.cursor(); c.execute("SELECT * FROM users WHERE telegram_id=?", (tid,))
    res = c.fetchone(); conn.close()
    return dict(res) if res else None

async def add_user(tid, uname, fname):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (telegram_id, username, first_name) VALUES (?,?,?)", (tid, uname, fname))
    conn.commit(); conn.close()

async def update_user(tid, **kwargs):
    if not kwargs: return
    set_clause = ", ".join(f"{k}=?" for k in kwargs); vals = list(kwargs.values()) + [tid]
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute(f"UPDATE users SET {set_clause} WHERE telegram_id=?", vals)
    conn.commit(); conn.close()

async def set_premium(tid, status: bool): await update_user(tid, is_premium=1 if status else 0)

# 🔒 ДЕКОРАТОР PREMIUM
def premium_required(func):
    async def wrapper(message: types.Message, *args, **kwargs):
        user = await get_user(message.from_user.id)
        if not user or not user.get("is_premium"):
            await message.answer("💎 Эта функция доступна только в Premium.\nДля активации напиши админу или используй /premium")
            return
        return await func(message, *args, **kwargs)
    return wrapper

# ⌨️ КЛАВИАТУРЫ
def main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🔮 Гороскоп"), KeyboardButton(text="🌙 Луна")],
        [KeyboardButton(text="🎱 Магический шар"), KeyboardButton(text="💕 Совместимость")],
        [KeyboardButton(text="💎 Premium"), KeyboardButton(text="📊 Мой профиль")]
    ], resize_keyboard=True)

def zodiac_inline():
    signs = ["♈ Овен", "♉ Телец", "♊ Близнецы", "♋ Рак", "♌ Лев", "♍ Дева", "♎ Весы", "♏ Скорпион", "♐ Стрелец", "♑ Козерог", "♒ Водолей", "♓ Рыбы"]
    kb = [[InlineKeyboardButton(text=s, callback_data=f"sign_{s}")] for s in signs]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# 🌍 ДАННЫЕ & РАСЧЁТЫ
STOICHIOMETRY = {
    "♈ Овен": "fire", "♉ Телец": "earth", "♊ Близнецы": "air", "♋ Рак": "water",
    "♌ Лев": "fire", "♍ Дева": "earth", "♎ Весы": "air", "♏ Скорпион": "water",
    "♐ Стрелец": "fire", "♑ Козерог": "earth", "♒ Водолей": "air", "♓ Рыбы": "water"
}
COMPAT = {
    "fire": {"fire": "🔥🔥 Страсть и энергия!", "air": "💨🔥 Вдохновение и лёгкость", "water": "💧🔥 Пар и конфликты", "earth": "🌍🔥 Тормозит огонь"},
    "earth": {"earth": "🌍🌍 Стабильность и надёжность", "water": "💧🌍 Плодородие и рост", "fire": "🔥🌍 Огонь сушит землю", "air": "💨🌍 Пыль и ветер"},
    "air": {"air": "💨💨 Интеллект и идеи", "fire": "🔥💨 Ветер раздувает пламя", "earth": "🌍💨 Ветер уносит землю", "water": "💧💨 Туман и неясность"},
    "water": {"water": "💧💧 Глубина и эмпатия", "earth": "🌍💧 Увлажнение и рост", "fire": "🔥💧 Испарение и стресс", "air": "💨💧 Волны и переменчивость"}
}
SIGN_MAP = {
    "овен": "♈ Овен", "овна": "♈ Овен", "телец": "♉ Телец", "тельца": "♉ Телец",
    "близнецы": "♊ Близнецы", "близнецов": "♊ Близнецы", "рак": "♋ Рак", "рака": "♋ Рак",
    "лев": "♌ Лев", "льва": "♌ Лев", "дева": "♍ Дева", "девы": "♍ Дева", "весы": "♎ Весы",
    "скорпион": "♏ Скорпион", "скорпиона": "♏ Скорпион", "стрелец": "♐ Стрелец", "стрельца": "♐ Стрелец",
    "козерог": "♑ Козерог", "козерога": "♑ Козерог", "водолей": "♒ Водолей", "водолея": "♒ Водолей", "рыбы": "♓ Рыбы"
}

# 🔮 РАСШИРЕННЫЙ ГЕНЕРАТОР ГОРОСКОПОВ (5+ строк, 2000+ комбинаций)
def get_horoscope_reliable(sign):
    today = datetime.now().strftime("%Y-%m-%d")
    seed_str = f"{today}_{sign}"
    seed_val = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
    rng = random.Random(seed_val)

    intros = [
        "Сегодня звёзды выстраиваются в редкий гармоничный узор, наполняя день энергией обновления и чистых намерений.",
        "Лунный цикл входит в активную фазу, обостряя интуицию и подсказывая верные решения в самых запутанных ситуациях.",
        "Планетарные аспекты благоприятствуют смелым шагам, риску и творческому поиску — не бойтесь выходить за рамки привычного.",
        "Энергетический фон дня настроен на завершение начатого, анализ прошлых ошибок и честное подведение важных итогов.",
        "Космические ритмы сегодня подсказывают: время замедлиться, выдохнуть и прислушаться к внутреннему голосу, а не к чужим советам.",
        "Солнечная активность сегодня на пике — ваш личный магнетизм притягивает нужные события, людей и возможности.",
        "Венера и Марс формируют редкий треугольник, открывая двери для романтики, страсти и глубокого эмоционального контакта.",
        "Меркурий сегодня требует внимания к деталям: мелочи могут изменить ход больших дел, поэтому проверяйте всё дважды.",
        "Юпитер посылает сигнал расширения границ: не бойтесь мечтать масштабно, действовать решительно и просить о том, чего заслуживаете.",
        "Сатурн напоминает о дисциплине: порядок в мыслях, расписании и финансах приведёт к стабильным результатам на месяцы вперёд.",
        "Нептун размывает границы восприятия — доверьтесь снам, творческим озарениям и тихим подсказкам подсознания.",
        "Уран приносит внезапные инсайты: будьте открыты к нестандартным решениям, даже если они кажутся странными на первый взгляд."
    ]

    career = [
        "💼 В делах и финансах: сегодня удача на стороне тех, кто действует системно и без суеты. Возможна неожиданная поддержка от коллег или выгодное предложение, которое стоит рассмотреть внимательно.",
        "💼 Рабочие процессы могут пойти не по плану, но это откроет скрытые резервы. Не спорьте с начальством, а предложите альтернативный путь — ваша гибкость будет вознаграждена.",
        "💼 Отличный день для переговоров, подписания документов и старта новых проектов. Ваша харизма и уверенность помогут склонить чашу весов в вашу пользу без лишнего давления.",
        "💼 Финансовая энергия дня требует осторожности: избегайте спонтанных покупок и рискованных вложений. Лучше займитесь планированием бюджета или аудитом текущих расходов.",
        "💼 Сегодня важно делегировать рутину и сфокусироваться на стратегических задачах. Кто-то из окружения возьмёт на себя часть вашей нагрузки, если вы попросите прямо.",
        "💼 Возможны задержки в отчётах или коммуникации, но терпение и чёткие формулировки всё исправят. Не принимайте важных решений в спешке — дайте себе час на обдумывание."
    ]

    love = [
        "❤️ В личной сфере: день благоприятен для искренних разговоров и укрепления доверия. Одиноким знакам стоит присмотреться к знакомым — возможно, судьба уже рядом, просто вы не замечали.",
        "❤️ Эмоциональный фон нестабилен: избегайте провокаций и не выясняйте отношения на повышенных тонах. Лучшее лекарство — совместный ужин, прогулка или просто тишина вдвоём.",
        "❤️ Романтическая энергия на пике! Звёзды рекомендуют проявить инициативу, сделать неожиданный жест внимания или возобновить приятное знакомство, которое давно забыто.",
        "❤️ Сегодня партнёр может нуждаться в вашей поддержке больше обычного. Проявите эмпатию, выслушайте без оценок, и это вернётся сторицей в виде крепкой, глубокой связи.",
        "❤️ Взаимоотношения требуют баланса между личным пространством и близостью. Уважайте границы, но не замыкайтесь в себе — честность сегодня ценнее идеальности.",
        "❤️ День подходит для совместного творчества, поездок или изучения чего-то нового вдвоём. Общие впечатления и смех сблизят сильнее любых долгих разговоров."
    ]

    advice = [
        "💡 Совет дня: не пытайтесь контролировать всё вокруг. Отпустите то, что уходит, и сосредоточьтесь на том, что можете изменить уже сегодня — маленький шаг часто запускает большую волну.",
        "💡 Звёзды предупреждают: остерегайтесь сплетен, чужого влияния и навязанных мнений. Ваша интуиция сегодня — самый точный компас, доверяйте ей без колебаний.",
        "💡 Благоприятное время для заботы о здоровье: прогулка на свежем воздухе, медитация, растяжка или ранний отход ко сну дадут энергию и ясность ума на неделю вперёд.",
        "💡 Не откладывайте важное на потом. Сегодняшний импульс уникален: сделайте первый шаг, даже если не видите всей дороги. Действие рождает мотивацию, а не наоборот.",
        "💡 Помните про закон сохранения энергии: чем больше вы вкладываете в добро, созидание и благодарность, тем больше вселенная возвращает вам возможностей и лёгких путей."
    ]

    stone = rng.choice(['аметист', 'горный хрусталь', 'тигровый глаз', 'лунный камень', 'цитрин', 'обсидиан', 'розенкварц', 'чёрный турмалин'])
    color = rng.choice(['изумрудный', 'небесно-голубой', 'золотистый', 'бордовый', 'серебристый', 'пурпурный', 'тёплый бежевый', 'индиго'])
    time = rng.choice(['09:00–11:00', '13:00–15:00', '17:00–19:00', '20:00–22:00', '07:00–09:00'])

    return (
        f"🌟 {rng.choice(intros)}\n\n"
        f"{rng.choice(career)}\n\n"
        f"{rng.choice(love)}\n\n"
        f"{rng.choice(advice)}\n\n"
        f"🍀 Талисман: {stone} | 🎨 Цвет дня: {color} | ⏰ Пик удачи: {time}"
    )

def get_moon_phase():
    known = datetime(2000, 1, 6, 18, 14); synodic = 29.53058867
    days = (datetime.now() - known).total_seconds() / 86400; phase = days % synodic
    if phase < 1.84566: return "🌑 Новолуние", 1
    elif phase < 5.53699: return "🌓 Растущий серп", int(phase/1.84566)+1
    elif phase < 9.22831: return "🌗 Первая четверть", int((phase-5.53699)/1.84566)+8
    elif phase < 12.91963: return "🌔 Растущая луна", int((phase-9.22831)/1.84563)+15
    elif phase < 16.61096: return "🌕 Полнолуние", int((phase-12.91963)/1.84563)+16
    elif phase < 20.30228: return "🌖 Убывающая луна", int((phase-16.61096)/1.84563)+17
    elif phase < 23.99361: return "🌘 Последняя четверть", int((phase-20.30228)/1.84563)+23
    else: return "🌒 Убывающий серп", int((phase-23.99361)/1.84563)+24

def get_astro_tip():
    return random.choice(["🌿 Луна в знаке Земли: время для планирования бюджета и наведения порядка.", "⚡ Меркурий активен: не отправляй важные сообщения после 22:00, лучше отложи до утра.", "🌊 Ретроградный период: перепроверяй билеты, договоры и контакты перед отправкой.", "☀️ Солнечный аспект: отличное время для старта проектов и публичных выступлений.", "🌙 Лунный день: посвяти его очищению пространства, мыслей и отказу от токсичных привычек.", "🔮 Венера в гармонии: день для творчества, свиданий и выражения благодарности близким."])

# 🎯 ОБРАБОТЧИКИ
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(f"🌟 Привет, {message.from_user.first_name}!\nЯ твой астрологический компас. Бесплатно: гороскопы, луна, совместимость.\n💎 Premium: натальные карты, транзиты, прогнозы.\nВыбери действие:", reply_markup=main_kb())

@dp.message(Command("profile"))
@dp.message(F.text == "📊 Мой профиль")
async def cmd_profile(message: types.Message):
    u = await get_user(message.from_user.id)
    if not u: return
    prem = "💎 Да" if u["is_premium"] else "🆓 Нет"
    await message.answer(f"👤 {u['first_name']}\n♐ Знак: {u['zodiac_sign'] or 'Не выбран'}\n📅 Дата: {u['birth_date'] or 'Не указана'}\n💎 Premium: {prem}")

@dp.message(F.text == "🔮 Гороскоп")
async def horoscope_menu(message: types.Message):
    await message.answer("Выбери знак 👇", reply_markup=zodiac_inline())

@dp.callback_query(F.data.startswith("sign_"))
async def show_horoscope(cb: types.CallbackQuery):
    sign = cb.data.replace("sign_", "")
    text = get_horoscope_reliable(sign)
    await update_user(cb.from_user.id, zodiac_sign=sign)
    await cb.message.answer(f"{sign}\n\n{text}"); await cb.answer()

@dp.message(F.text == "🌙 Луна")
async def cmd_moon(message: types.Message):
    phase, day = get_moon_phase()
    rec = "🌱 Начинать дела" if "Растущ" in phase else "🔄 Завершать дела" if "Убыв" in phase else "⚡ Действовать интуитивно"
    await message.answer(f"🌙 Фаза: {phase}\n📅 Лунный день: {day}\n💡 Рекомендация: {rec}\n\n{get_astro_tip()}")

@dp.message(F.text == "🎱 Магический шар")
async def cmd_orb(message: types.Message):
    await message.answer(f"🎱 {random.choice(['🌟 Звёзды говорят: ДА', '🌙 Луна шепчет: ПОДОЖДИ', '🌍 Земля советует: ПРОВЕРЬ', '💨 Ветер дует: НЕТ', '🔥 Огонь горит: СЕЙЧАС!', '💧 Вода течёт: ДОВЕРЬСЯ', '🌌 Космос молчит: СПРОСИ ПОЗЖЕ', '✨ Судьба решила: ТОЧНО ДА'])}")

@dp.message(F.text == "💕 Совместимость")
async def cmd_compat_prompt(message: types.Message):
    await message.answer("💕 **Расчёт совместимости**\n\nНапиши имя и знак зодиака партнёра.\nПримеры:\n• `Света Близнецы`\n• `Макс Скорпион`\n• `Аня Рыбы`\n\nДоступные знаки:\nОвен, Телец, Близнецы, Рак, Лев, Дева, Весы, Скорпион, Стрелец, Козерог, Водолей, Рыбы", parse_mode="Markdown")

@dp.message()
async def calc_compat(message: types.Message):
    text = message.text.strip()
    text_lower = text.lower()
    
    found_sign = None; found_key = None
    for key, full_sign in SIGN_MAP.items():
        if re.search(r'\b' + re.escape(key) + r'\b', text_lower):
            found_sign = full_sign; found_key = key; break
            
    if not found_sign: return

    user = await get_user(message.from_user.id)
    if not user or not user.get("zodiac_sign"):
        return await message.answer("❓ Сначала узнай свой знак в разделе 🔮 Гороскоп!")

    my_el = STOICHIOMETRY[user["zodiac_sign"]]
    their_el = STOICHIOMETRY[found_sign]
    result = COMPAT[my_el][their_el]

    name_part = text[:text.lower().index(found_key)].strip().rstrip(" -:")
    name = name_part.capitalize() if name_part else "Партнёр"

    await message.answer(
        f"💕 {user['first_name']} ({user['zodiac_sign']}) + {name} ({found_sign})\n\n"
        f"{result}\n\n"
        f"💡 *Упрощённый расчёт по стихиям. Для детального анализа по датам и времени нужен Premium.*",
        parse_mode="Markdown"
    )

# 💎 PREMIUM ФУНКЦИИ
@dp.message(F.text == "💎 Premium")
async def cmd_premium(message: types.Message):
    await message.answer("💎 **Premium возможности:**\n📊 Полная натальная карта\n💕 Детальная совместимость по датам\n🌌 Ежемесячный прогноз транзитов\n🔮 Персональные рекомендации\n⚡ Приоритетная поддержка\n\n💰 Стоимость: 299₽/мес\n📩 Для активации напиши: `/buy` или свяжись с админом", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛒 Купить Premium", callback_data="buy_premium")]]))

@dp.callback_query(F.data == "buy_premium")
async def buy_premium(cb: types.CallbackQuery):
    await cb.message.answer("📩 Для оплаты и активации напиши админу: @ТВОЙ_НИК\nПосле подтверждения бот обновит статус."); await cb.answer()

class ProfileState(StatesGroup):
    date = State(); time = State(); place = State()

@dp.message(Command("natal"))
@premium_required
async def cmd_natal(message: types.Message, state: FSMContext):
    await message.answer("📅 Введи дату рождения (ДД.ММ.ГГГГ):"); await state.set_state(ProfileState.date)

@dp.message(ProfileState.date)
async def natal_date(message: types.Message, state: FSMContext):
    await state.update_data(birth_date=message.text); await message.answer("🕐 Введи время рождения (ЧЧ:ММ):"); await state.set_state(ProfileState.time)

@dp.message(ProfileState.time)
async def natal_time(message: types.Message, state: FSMContext):
    await state.update_data(birth_time=message.text); await message.answer("🌍 Введи место рождения (город):"); await state.set_state(ProfileState.place)

@dp.message(ProfileState.place)
async def natal_place(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await update_user(message.from_user.id, birth_date=data["birth_date"], birth_time=data["birth_time"], birth_place=data["birth_place"])
    await message.answer(f"📊 **Натальная карта сгенерирована!**\n📅 {data['birth_date']} | 🕐 {data['birth_time']} | 🌍 {data['birth_place']}\n☀️ Полный отчёт в обработке..."); await state.clear()

@dp.message(Command("transits"))
@premium_required
async def cmd_transits(message: types.Message):
    await message.answer("🌌 **Прогноз транзитов на месяц**\n♄ Сатурн: время терпения.\n♃ Юпитер: удача в обучении.\n🪐 Плутон: трансформация связей.\n💡 Совет: Адаптируйся к переменам.")

# 🔧 АДМИН
@dp.message(Command("addpremium"))
async def cmd_addpremium(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    parts = message.text.split()
    if len(parts) < 2: return await message.answer("Использование: `/addpremium <user_id>`")
    try: await set_premium(int(parts[1]), True); await message.answer("✅ Premium выдан!")
    except: await message.answer("❌ Ошибка ID.")

@dp.message(Command("rmpremium"))
async def cmd_rmpremium(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    parts = message.text.split()
    if len(parts) < 2: return
    try: await set_premium(int(parts[1]), False); await message.answer("✅ Premium отключён.")
    except: pass

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users"); total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE is_premium=1"); prem = c.fetchone()[0]; conn.close()
    await message.answer(f"📊 Статистика:\n👥 Всего: {total}\n💎 Premium: {prem}\n📈 Конверсия: {(prem/total*100) if total else 0:.1f}%")

# 🌐 RENDER СЕРВЕР
async def handle_health(request): return web.Response(text="OK 🤖")
async def start_webserver(port):
    app = web.Application(); app.add_routes([web.get('/', handle_health), web.get('/health', handle_health)])
    runner = web.AppRunner(app); await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port); await site.start()
    logger.info(f"🌐 Веб-сервер на порту {port}"); return runner

# ♻️ АВТО-ПЕРЕЗАПУСК
async def run_with_restart():
    while True:
        try: logger.info("🔄 Запуск polling..."); await dp.start_polling(bot)
        except Exception as e: logger.error(f"💥 Ошибка: {e}. Перезапуск через 15с..."); await asyncio.sleep(15)
        await asyncio.sleep(5)

# 🚀 ГЛАВНАЯ
async def main():
    logger.info("🚀 Бот запускается..."); init_db()
    try: me = await bot.me(); logger.info(f"✅ Авторизован: @{me.username}")
    except Exception as e: logger.error(f"❌ Ошибка токена: {e}"); return
    port = int(os.getenv("PORT", 10000)); await start_webserver(port)
    await run_with_restart()

if __name__ == "__main__": asyncio.run(main())
