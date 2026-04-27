import asyncio
import logging
import os
import sqlite3
import random
import aiohttp
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery, FSInputFile
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
                return f"❌ Ошибка AI: {resp.status}"
    except Exception as e:
        return f"❌ Ошибка: {e}"

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
    
    # Длинные названия для расширения кнопок
    vedana_text = f"🔮 Личный прогноз от Веданы\n({vedana_c} вед)"

    menu_kb = [
        [InlineKeyboardButton(text="🌟 Гороскоп на сегодня", callback_data="horoscope"),
         InlineKeyboardButton(text="🌌 Натальная карта", callback_data="natal")],
        [InlineKeyboardButton(text="🃏 Расклад Таро", callback_data="tarot"),
         InlineKeyboardButton(text="💕 Совместимость знаков", callback_data="compat")],
        [InlineKeyboardButton(text="🔮 Магический шар", callback_data="ball"),
         InlineKeyboardButton(text="ᚠ Гадание на рунах", callback_data="rune")],
        [InlineKeyboardButton(text="🔢 Нумерология даты", callback_data="numerology"),
         InlineKeyboardButton(text="📅 Прогноз на неделю", callback_data="week")],
        [InlineKeyboardButton(text=f"📊 Ваши прогнозы: {free_txt}", callback_data="noop")],
        [InlineKeyboardButton(text=vedana_text, callback_data=vedana_cb)],
        [InlineKeyboardButton(text="✏️ Изменить дату рождения", callback_data="edit")],
        [InlineKeyboardButton(text="👥 Пригласить друга (+5)", callback_data="invite")]
    ]

    if is_admin:
        menu_kb.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")])

    return InlineKeyboardMarkup(inline_keyboard=menu_kb)

async def send_commands_hint(message: types.Message):
    """Отправляет текстовую подсказку с командами (как у конкурентов)"""
    await message.answer("/start Запустить (если бот не отвечает)\n/menu Главное меню")

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
        asyncio.create_task(msg.answer("❌ Прогнозы на сегодня закончились. Раскрой тайны в магазине!"))
        return False
    return True

async def send_pred(msg, text):
    try:
        await msg.answer(text, parse_mode="Markdown", reply_markup=get_after_pred_kb())
    except Exception as e:
        logging.error(f"Ошибка отправки предсказания: {e}")
        await msg.answer(text, reply_markup=get_after_pred_kb())

# ================= ОНБОРДИНГ =================
@dp.message(Command("start"))
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
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

    if not get_user(message.from_user.id):
        add_or_update_user(message.from_user.id)

    user = get_user(message.from_user.id)
    is_admin = (message.from_user.username == ADMIN_USERNAME)
    caption = "🌌 Я — Ведана.\nЗвёзды готовы открыть свои тайны."

    try:
        await message.answer_photo(photo=FSInputFile("vedana.jpg"), caption=caption, reply_markup=get_menu_grid(user, is_admin), parse_mode="Markdown")
    except:
        await message.answer(caption, reply_markup=get_menu_grid(user, is_admin), parse_mode="Markdown")
    await send_commands_hint(message)

@dp.message(Command("menu"))
@dp.message(F.text == "/menu")
async def cmd_menu(message: types.Message, state: FSMContext):
    await state.clear()
    user = get_user(message.from_user.id)
    if not user:
        await cmd_start(message, state)
        return
    is_admin = (message.from_user.username == ADMIN_USERNAME)
    caption = "🌌 Я — Ведана.\nЗвёзды готовы открыть свои тайны."
    try:
        await message.answer_photo(photo=FSInputFile("vedana.jpg"), caption=caption, reply_markup=get_menu_grid(user, is_admin), parse_mode="Markdown")
    except:
        await message.answer(caption, reply_markup=get_menu_grid(user, is_admin), parse_mode="Markdown")
    await send_commands_hint(message)

async def start_onboarding(callback: types.CallbackQuery, state: FSMContext, target_action: str):
    await state.update_data(target_action=target_action)
    await callback.message.answer("🔮 Прежде чем звёзды заговорят, представься.\nКак тебя зовут?")
    await state.set_state(OnboardingState.waiting_for_name)
    await callback.answer()

@dp.message(OnboardingState.waiting_for_name)
async def onboarding_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer(f"✨ {message.text.strip()}!\n\n📅 Теперь дату рождения (ДД.ММ.ГГГГ):")
    await state.set_state(OnboardingState.waiting_for_birthdate)

@dp.message(OnboardingState.waiting_for_birthdate)
async def onboarding_birthdate(message: types.Message, state: FSMContext):
    try:
        datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except:
        await message.answer("❌ Неверно. Формат: ДД.ММ.ГГГГ")
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
    await send_commands_hint(message)

    if target_action:
        fake_cb = types.CallbackQuery(id="fake", from_user=message.from_user, message=message, chat_instance="fake", data=target_action)
        if target_action == "horoscope":
            await horoscope(fake_cb, state)
        elif target_action == "natal":
            await natal(fake_cb, state)
        elif target_action == "ball":
            await ball_menu(fake_cb, state)
        elif target_action == "compat":
            await compat_menu(fake_cb, state)
        elif target_action == "week":
            await week_forecast(fake_cb, state)
        elif target_action == "numerology":
            await numerology(fake_cb, state)
        elif target_action == "rune":
            await rune_divination(fake_cb, state)
        elif target_action == "tarot":
            await tarot(fake_cb, state)
        elif target_action == "vedana_pred":
            await vedana_pred(fake_cb, state)

# ================= ОБРАБОТЧИКИ ПРЕДСКАЗАНИЙ =================
async def check_and_run(callback: types.CallbackQuery, state: FSMContext, action_name: str, coro):
    user = get_user(callback.from_user.id)
    if not user or not user.get('name') or not user.get('birth_date'):
        await start_onboarding(callback, state, action_name)
    else:
        await coro(callback, state)

@dp.callback_query(F.data == "horoscope")
async def horoscope(cb: types.CallbackQuery, state: FSMContext):
    async def _exec(c, s):
        user = get_user(c.from_user.id)
        if not check_free(user, c.message): return
        use_free_credit(user['telegram_id'])
        await send_loading_video(c.message)
        await delay_thinking()
        prompt = PROMPT_HOROSCOPE.format(sign=user['zodiac'], name=user['name'], date=datetime.now().strftime("%d.%m.%Y"))
        ans = await ask_groq(prompt, "Ты астролог с 20-летним опытом.")
        await send_pred(c.message, ans + get_shadow("horoscope"))
        await send_commands_hint(c.message)
        await c.answer()
    await check_and_run(cb, state, "horoscope", _exec)

@dp.callback_query(F.data == "natal")
async def natal(cb: types.CallbackQuery, state: FSMContext):
    async def _exec(c, s):
        user = get_user(c.from_user.id)
        if not check_free(user, c.message): return
        await c.message.answer("🌌 Введи время рождения (ЧЧ:ММ):")
        await s.update_data(natal_mode=True)
        await s.set_state(NatalState.waiting_for_time)
        await c.answer()
    await check_and_run(cb, state, "natal", _exec)

@dp.callback_query(F.data == "ball")
async def ball_menu(cb: types.CallbackQuery, state: FSMContext):
    async def _exec(c, s):
        user = get_user(c.from_user.id)
        if not check_free(user, c.message): return
        await c.message.answer("🔮 Напиши вопрос шару:")
        await s.set_state(BallState.waiting_for_question)
        await c.answer()
    await check_and_run(cb, state, "ball", _exec)

@dp.callback_query(F.data == "compat")
async def compat_menu(cb: types.CallbackQuery, state: FSMContext):
    async def _exec(c, s):
        user = get_user(c.from_user.id)
        if not check_free(user, c.message): return
        await c.message.answer("💕 Введи знак партнёра (Телец, Лев...):")
        await s.set_state(CompatState.waiting_for_partner_sign)
        await c.answer()
    await check_and_run(cb, state, "compat", _exec)

@dp.callback_query(F.data == "week")
async def week_forecast(cb: types.CallbackQuery, state: FSMContext):
    async def _exec(c, s):
        user = get_user(c.from_user.id)
        if not check_free(user, c.message): return
        await send_loading_video(c.message)
        await delay_thinking()
        prompt = PROMPT_WEEK.format(sign=user['zodiac'])
        ans = await ask_groq(prompt, "Ты профессиональный астролог.")
        use_free_credit(user['telegram_id'])
        await send_pred(c.message, ans + get_shadow("week"))
        await send_commands_hint(c.message)
        await c.answer()
    await check_and_run(cb, state, "week", _exec)

@dp.callback_query(F.data == "numerology")
async def numerology(cb: types.CallbackQuery, state: FSMContext):
    async def _exec(c, s):
        user = get_user(c.from_user.id)
        if not check_free(user, c.message): return
        await send_loading_video(c.message)
        await delay_thinking()
        prompt = f"Нумерология для {user['birth_date']}. Число пути и трактовка."
        ans = await ask_groq(prompt, "Ты нумеролог.")
        use_free_credit(user['telegram_id'])
        await send_pred(c.message, f"🔢 Нумерология\n\n{ans}" + get_shadow("numerology"))
        await send_commands_hint(c.message)
        await c.answer()
    await check_and_run(cb, state, "numerology", _exec)

@dp.callback_query(F.data == "rune")
async def rune_divination(cb: types.CallbackQuery, state: FSMContext):
    async def _exec(c, s):
        user = get_user(c.from_user.id)
        if not check_free(user, c.message): return
        await send_loading_video(c.message)
        await delay_thinking()
        rune = random.choice(RUNES)
        prompt = PROMPT_RUNE.format(rune_name=rune['name'], sign=user.get('zodiac', ''))
        ans = await ask_groq(prompt, "Ты эксперт по рунам.")
        use_free_credit(user['telegram_id'])
        await send_pred(c.message, f"ᚠ Руны говорят:\n\n{rune['desc']}\n\n{ans}" + get_shadow("rune"))
        await send_commands_hint(c.message)
        await c.answer()
    await check_and_run(cb, state, "rune", _exec)

@dp.callback_query(F.data == "tarot")
async def tarot(cb: types.CallbackQuery, state: FSMContext):
    async def _exec(c, s):
        user = get_user(c.from_user.id)
        if not check_free(user, c.message): return
        use_free_credit(user['telegram_id'])
        await send_loading_video(c.message)
        await delay_thinking()
        card = random.choice(TAROT_CARDS)
        text = f"🔮 Карты говорят...\n\n{card['desc']}\n\n{get_shadow('tarot')}"
        await send_pred(c.message, text)
        await send_commands_hint(c.message)
        await c.answer()
    await check_and_run(cb, state, "tarot", _exec)

@dp.callback_query(F.data == "vedana_pred")
async def vedana_pred(cb: types.CallbackQuery, state: FSMContext):
    async def _exec(c, s):
        user = get_user(c.from_user.id)
        if user['vedana_credits'] <= 0 and not user['is_premium']:
            await c.message.answer("✨ У тебя нет свободных предсказаний Веданы.\n\nРаскрой тайны в магазине:", reply_markup=get_shop_kb())
            await c.answer()
            return
        await send_loading_video(c.message)
        await delay_thinking()
        prompt = PROMPT_VEDANA.format(name=user['name'], sign=user['zodiac'], birth_date=user['birth_date'])
        ans = await ask_groq(prompt, "Ты Ведана, опытный астролог.")
        if not user['is_premium']:
            use_vedana_credit(user['telegram_id'])
        await send_pred(c.message, ans)
        await send_commands_hint(c.message)
        await c.answer()
    await check_and_run(cb, state, "vedana_pred", _exec)

# ================= FSM ДЛЯ NATAL, BALL, COMPAT =================
@dp.message(NatalState.waiting_for_time)
async def natal_time(msg: types.Message, state: FSMContext):
    await state.update_data(time=msg.text.strip())
    await msg.answer("📍 Место рождения (Город):")
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
    await send_commands_hint(msg)
    await state.clear()

@dp.message(BallState.waiting_for_question)
async def ball_question(msg: types.Message, state: FSMContext):
    user = get_user(msg.from_user.id)
    if not user or not check_free(user, msg):
        await state.clear()
        return
    await send_loading_video(msg)
    await delay_thinking()
    prompt = PROMPT_BALL.format(q=msg.text, sign=user.get('zodiac',''))
    ans = await ask_groq(prompt,"Ты магический шар.")
    use_free_credit(msg.from_user.id)
    await send_pred(msg, ans + get_shadow("ball"))
    await send_commands_hint(msg)
    await state.clear()

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
    await send_commands_hint(msg)
    await state.clear()

# ================= ОБРАБОТЧИКИ ДЛЯ КНОПОК БЕЗ ОНБОРДИНГА =================
@dp.callback_query(F.data == "noop")
async def noop(cb: types.CallbackQuery): await cb.answer()

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
        await send_commands_hint(cb.message)
    await cb.answer()

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
    await cb.message.answer("✏️ Новая дата (ДД.ММ.ГГГГ):")
    await cb.answer()

@dp.message(F.text)
async def save_edit(msg: types.Message, st: FSMContext):
    try:
        datetime.strptime(msg.text.strip(), "%d.%m.%Y")
        zodiac = calculate_zodiac(msg.text.strip())
        add_or_update_user(msg.from_user.id, birth_date=msg.text.strip(), zodiac=zodiac)
        await msg.answer("✅ Дата обновлена!", reply_markup=get_menu_grid(get_user(msg.from_user.id)))
        await send_commands_hint(msg)
    except:
        await msg.answer("❌ Неверно")
    await st.clear()

@dp.callback_query(F.data == "invite")
async def invite_friend(cb: types.CallbackQuery):
    bot_username = (await bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=ref_{cb.from_user.id}"
    await cb.message.answer(
        f"👥 Твоя реферальная ссылка:\n{link}\n\n"
        f"🎁 За каждого друга, который перейдёт по ссылке и начнёт пользоваться ботом, "
        f"ты получишь +5 бесплатных прогнозов.\n\n"
        f"📢 Поделись ссылкой в TikTok, соцсетях или с друзьями!"
    )
    await cb.answer()

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

# ================= ПЛАТЕЖИ =================
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
        await send_commands_hint(msg)

# ================= ЗАПУСК =================
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