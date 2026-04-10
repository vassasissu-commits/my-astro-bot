import asyncio
import logging
import os
import sqlite3
import random
import aiohttp
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, 
    KeyboardButton, LabeledPrice, PreCheckoutQuery, FSInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiohttp import web

# ================= НАСТРОЙКИ =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not BOT_TOKEN or not GROQ_API_KEY:
    logging.error("❌ Ошибка: Проверь переменные окружения BOT_TOKEN и GROQ_API_KEY")
    exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

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

# ================= GROQ AI =================
async def ask_groq(prompt, system_prompt):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
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

PROMPT_RUNE = """Ты — эксперт по рунам. Выпала руна {rune_name}.
Дай толкование для человека со знаком {sign}.
СТРУКТУРА:
🔮 Руна: {rune_name}
📖 Значение: [основное значение]
💫 Что означает для тебя: [персональное толкование]
💡 Совет рун: [практический совет]
Длина: 100-150 слов."""

# ================= ТЕНЕВЫЕ ФРАЗЫ =================
SHADOWS = {
    "horoscope": ["🕯️ Но есть аспект, который требует более глубокого изучения...", "✨ Этот знак — лишь верхушка. Глубинный смысл раскроется в личной консультации.", "🔮 Звёзды шепчут о важном. Хочешь узнать точную дату?"],
    "natal": ["🌑 Карта открыта, но судьба хранит ещё один секрет...", "✨ Натальная карта показывает потенциал. Личная консультация Веданы активирует его."],
    "tarot": ["🔮 Карта выпала не случайно. За ней скрывается послание именно для тебя...", "🕯️ Расклад завершён, но вопрос остаётся открытым. Ведана знает ответ."],
    "compat": ["💕 Совместимость рассчитана. Но как пройти через зоны риска? Ведана подскажет путь.", "✨ Звёзды видят союз иначе. Личная консультация раскроет скрытые аспекты."],
    "ball": ["🔮 Шар ответил, но эхо остаётся. Хочешь услышать его от самой Веданы?", "🌑 Ответ получен. Следующий шаг требует мудрости опытного астролога."],
    "week": ["📅 Неделя обещает перемены. Будь готов(а) к знакам...", "✨ Прогноз составлен. Детали скрыты в личной консультации."],
    "numerology": ["🔢 Число пути найдено. Но как его пройти без потерь?", "🕯️ Нумерология открыла дверь. Ведана поможет войти."],
    "rune": ["✨ Руны открыли путь. Но куда он ведёт — покажет время.", "✨ Руническое послание получено. Следуй совету."]
}

def get_shadow(pred_type):
    return "\n\n" + random.choice(SHADOWS.get(pred_type, ["🔮 Звёзды видят больше..."]))

# ================= ТАРО =================
TAROT_CARDS = [
    {"name": "🃏 Шут (0)", "desc": "🌬️ Начало пути, чистый лист.\n\n✨ Ты стоишь на пороге нового цикла. Вселенная приглашает отпустить контроль и довериться потоку.\n💫 Сейчас не время для долгих раздумий. Спонтанность станет проводником.\n🕊️ Рискни там, где раньше боялся. Удача любит смелых."},
    {"name": "🎩 Маг (I)", "desc": "🔮 Сила воли и мастерство.\n\n✨ У тебя в руках все инструменты для успеха. Нужно лишь сфокусировать намерение.\n💫 Твои слова и мысли материализуются быстрее обычного.\n⚡ Действуй осознанно: ты создаёшь свою реальность прямо сейчас."},
    {"name": "📜 Жрица (II)", "desc": "🌙 Интуиция и тайны.\n\n✨ Ответы уже внутри тебя. Прислушайся к тихому голосу подсознания.\n💫 Сны и знаки будут особенно яркими в ближайшие дни.\n🤫 Не торопи события. Мудрость приходит в тишине."},
    {"name": "👑 Императрица (III)", "desc": "🌿 Плодородие и изобилие.\n\n✨ Время творить и принимать дары мира.\n💫 Отношения и проекты получат мощный импульс роста.\n🌸 Позволь себе наслаждаться процессом."},
    {"name": "🏛️ Император (IV)", "desc": "⚖️ Власть и структура.\n\n✨ Нужна дисциплина и чёткий план. Хаос отступает перед порядком.\n💫 Возьми ответственность за свою жизнь в свои руки.\n🛡️ Установи границы: они защитят твою энергию."},
    {"name": "🔑 Иерофант (V)", "desc": "📖 Традиции и обучение.\n\n✨ Ищи наставника или обратись к проверенным знаниям.\n💫 Духовные практики и ритуалы принесут ясность.\n🤝 Объединение с единомышленниками усилит твой путь."},
    {"name": "💞 Влюбленные (VI)", "desc": "❤️ Выбор и любовь.\n\n✨ Перед тобой стоит важный выбор. Слушай сердце, но не игнорируй разум.\n💫 Гармония в отношениях возможна через честность.\n🦋 Принятие решения откроет новую дверь."},
    {"name": "🏇 Колесница (VII)", "desc": "🔥 Победа и движение.\n\n✨ Ты на верном пути. Не сворачивай, даже если ветер встречный.\n💫 Контролируй эмоции: они могут увести в сторону.\n🏆 Успех ближе, чем кажется. Действуй решительно."},
    {"name": "🦁 Сила (VIII)", "desc": "🌸 Терпение и мужество.\n\n✨ Настоящая сила — в мягкости и самообладании.\n💫 Укроти внутренние страхи любовью, а не борьбой.\n🕊️ Ты справишься с любым испытанием, сохраняя достоинство."},
    {"name": "🕯️ Отшельник (IX)", "desc": "🌌 Поиск истины.\n\n✨ Время для уединения и глубокого самоанализа.\n💫 Внешний шум мешает слышать внутренний компас.\n🔦 Твой собственный свет укажет путь. Не бойся одиночества."},
    {"name": "🎡 Колесо Фортуны (X)", "desc": "🔄 Перемены и судьба.\n\n✨ Цикл завершается, начинается новый. Всё идёт по плану высших сил.\n💫 Удача поворачивается к тебе лицом. Используй момент.\n🌊 Плыви по течению, но держи руль."},
    {"name": "⚖️ Справедливость (XI)", "desc": "📜 Карма и правда.\n\n✨ Ты получишь ровно то, что заслужил. Честность вознаграждается.\n💫 Юридические или важные договорные вопросы решатся в твою пользу.\n🕊️ Принимай решения с холодной головой и чистым сердцем."},
    {"name": "🙃 Повешенный (XII)", "desc": "🔄 Жертва и новый взгляд.\n\n✨ Иногда нужно остановиться, чтобы увидеть картину целиком.\n💫 Отпусти старое, чтобы освободить место для нового.\n🌿 Пауза — это не поражение, а стратегическая мудрость."},
    {"name": "💀 Смерть (XIII)", "desc": "🦋 Трансформация.\n\n✨ Что-то должно уйти, чтобы родилось нечто большее.\n💫 Не цепляйся за прошлое. Трансформация неизбежна и благодатна.\n🌅 Закат всегда предшествует рассвету. Доверься процессу."},
    {"name": "⏳ Умеренность (XIV)", "desc": "💧 Баланс и терпение.\n\n✨ Ищи золотую середину во всём. Крайности сейчас опасны.\n💫 Исцеление приходит через гармонию и спокойствие.\n🕊️ Смешивай противоположности: так рождается алхимия успеха."},
    {"name": "⛓️ Дьявол (XV)", "desc": "🔥 Искушения и зависимости.\n\n✨ Осознай, что держит тебя в плену: страх, привычка или чужое мнение.\n💫 Цепи существуют только в твоей голове. Ты свободен освободиться.\n🌑 Тень требует внимания, а не подавления."},
    {"name": "🏰 Башня (XVI)", "desc": "⚡ Внезапные перемены.\n\n✨ Старые структуры рушатся, чтобы освободить место для истины.\n💫 Шок временный. За разрушением следует очищение.\n🌩️ Не сопротивляйся. Позволь молнии сжечь иллюзии."},
    {"name": "⭐ Звезда (XVII)", "desc": "🌠 Надежда и вдохновение.\n\n✨ После бури наступает ясность. Верь в свою мечту.\n💫 Вселенная посылает тебе знаки поддержки. Замечай их.\n💧 Исцеление уже в пути. Сохраняй веру."},
    {"name": "🌑 Луна (XVIII)", "desc": "🌊 Иллюзии и страхи.\n\n✨ Не всё то, чем кажется. Доверяй фактам, а не догадкам.\n💫 Подсознание активно. Сны могут нести важные послания.\n🌫️ Пройди через туман сомнений: за ним ждёт берег."},
    {"name": "☀️ Солнце (XIX)", "desc": "🌻 Радость и успех.\n\n✨ Ясность, тепло и витальность наполняют твою жизнь.\n💫 Проекты завершаются успешно. Дети и творчество приносят счастье.\n🔆 Наслаждайся моментом: ты в потоке изобилия."},
    {"name": "📯 Суд (XX)", "desc": "🔔 Возрождение и призыв.\n\n✨ Пришло время подвести итоги и ответить на зов судьбы.\n💫 Прошлые ошибки прощены. Начинай с чистого листа.\n🕊️ Пробуждение сознания меняет всё. Действуй по высшему импульсу."},
    {"name": "🌍 Мир (XXI)", "desc": "🕊️ Завершение и гармония.\n\n✨ Цикл успешно завершён. Ты целостен и в ладу с миром.\n💫 Путешествия, обучение и расширение горизонтов благоприятны.\n🌐 Ты на своём месте. Наслаждайся плодами труда."}
]

# ================= РУНЫ =================
RUNES = [
    {"name": "ᚠ Феху", "desc": "Богатство, изобилие, новая энергия"},
    {"name": "ᚢ Уруз", "desc": "Сила, здоровье, жизненная мощь"},
    {"name": "ᚦ Турисаз", "desc": "Врата, защита, активное действие"},
    {"name": "ᚬ Ансуз", "desc": "Знание, общение, божественное вдохновение"},
    {"name": "ᚱ Райдо", "desc": "Путь, путешествие, правильный выбор"},
    {"name": "ᚲ Кеназ", "desc": "Огонь, творчество, озарение"},
    {"name": "ᚷ Гебо", "desc": "Дар, партнёрство, равновесие"},
    {"name": "ᚹ Вуньо", "desc": "Радость, успех, гармония"},
    {"name": "ᚺ Хагалаз", "desc": "Разрушение, кризис, трансформация"},
    {"name": "ᚾ Наутиз", "desc": "Нужда, ограничение, терпение"},
    {"name": "ᛁ Иса", "desc": "Лёд, остановка, застой"},
    {"name": "ᛊ Йера", "desc": "Урожай, цикл, вознаграждение"},
    {"name": "ᛇ Эйваз", "desc": "Защита, выносливость, связь миров"},
    {"name": "ᛈ Перт", "desc": "Тайна, интуиция, скрытое знание"},
    {"name": "ᛉ Альгиз", "desc": "Защита, покровительство, инстинкт"},
    {"name": "ᛋ Соулу", "desc": "Солнце, успех, целостность"},
    {"name": "ᛏ Тейваз", "desc": "Воин, победа, справедливость"},
    {"name": "ᛒ Беркана", "desc": "Рост, плодородие, исцеление"},
    {"name": "ᛖ Эваз", "desc": "Движение, прогресс, доверие"},
    {"name": "ᛗ Манназ", "desc": "Человек, самосознание, общество"},
    {"name": "ᛚ Лагуз", "desc": "Вода, интуиция, поток"},
    {"name": "ᛟ Ингуз", "desc": "Плодородие, завершение, потенциал"},
    {"name": "ᛞ Дагаз", "desc": "День, прорыв, трансформация"},
    {"name": "ᛟ Одал", "desc": "Наследие, дом, корни"}
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
        [InlineKeyboardButton(text="👥 Пригласить друга (+5 прогнозов)", callback_data="invite")],
        [InlineKeyboardButton(text="🏠 Назад в меню", callback_data="main_menu")]
    ])

def get_menu_grid(user):
    name = user['name']
    free_txt = "∞/" if user['is_premium'] else f"{user['free_credits']}/3"
    vedana_c = user['vedana_credits']
    vedana_cb = "vedana_pred" if (vedana_c > 0 or user['is_premium']) else "shop"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌟 Гороскоп", callback_data="horoscope"),
         InlineKeyboardButton(text="🌌 Натальная карта", callback_data="natal")],
        [InlineKeyboardButton(text="🃏 Таро", callback_data="tarot"),
         InlineKeyboardButton(text="💕 Совместимость", callback_data="compat")],
        [InlineKeyboardButton(text="🔮 Магический шар", callback_data="ball"),
         InlineKeyboardButton(text="ᚠ Гадание на рунах", callback_data="rune")],
        [InlineKeyboardButton(text="🔢 Нумерология", callback_data="numerology"),
         InlineKeyboardButton(text="📅 На неделю", callback_data="week")],
        [InlineKeyboardButton(text=f"📅 Прогнозы: {free_txt}", callback_data="noop")],
        [InlineKeyboardButton(text=f"🔮 Индивидуальное предсказание от Веданы ({vedana_c})", callback_data=vedana_cb)],
        [InlineKeyboardButton(text="✏️ Изменить данные", callback_data="edit")]
    ])

# ================= ВСПОМОГАТЕЛЬНЫЕ =================
async def send_loading_video(message):
    try:
        video = FSInputFile("loading.mp4")
        await message.answer_video(video, caption="🌌 Звёзды складываются...")
    except Exception as e:
        logging.warning(f"Не удалось отправить видео: {e}")
        await message.answer("🌌 Ведана концентрируется...")

async def delay_thinking():
    await asyncio.sleep(random.uniform(3, 5))

def calculate_zodiac(birth_date):
    try:
        date = datetime.strptime(birth_date, "%d.%m.%Y")
        day, month = date.day, date.month
        signs = [
            ((3,21),(4,19), "♈ Овен"), ((4,20),(5,20), "♉ Телец"), ((5,21),(6,20), "♊ Близнецы"),
            ((6,21),(7,22), "♋ Рак"), ((7,23),(8,22), "♌ Лев"), ((8,23),(9,22), "♍ Дева"),
            ((9,23),(10,22), "♎ Весы"), ((10,23),(11,21), "♏ Скорпион"), ((11,22),(12,21), "♐ Стрелец"),
            ((12,22),(12,31), "♑ Козерог"), ((1,1),(1,19), "♑ Козерог"), ((1,20),(2,18), "♒ Водолей"),
            ((2,19),(3,20