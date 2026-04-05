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

# 🖼️ КАРТИНКА ДЛЯ ПРИВЕТСТВИЯ
# Картинка будет загружаться из файла
WELCOME_IMAGE_PATH = "welcome.jpg"

# 🗄️ БАЗА ДАННЫХ (ИСПРАВЛЕННАЯ)
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

# 🔑 НОВАЯ ФУНКЦИЯ: Гарантированное сохранение знака
async def save_zodiac(tid, sign):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("UPDATE users SET zodiac_sign=? WHERE telegram_id=?", (sign, tid))
    if c.rowcount == 0:  # Если строки нет, создаём её
        c.execute("INSERT INTO users (telegram_id, zodiac_sign) VALUES (?, ?)", (tid, sign))
    conn.commit(); conn.close()

async def set_premium(tid, status: bool):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("UPDATE users SET is_premium=? WHERE telegram_id=?", (1 if status else 0, tid))
    if c.rowcount == 0:
        c.execute("INSERT INTO users (telegram_id, is_premium) VALUES (?, ?)", (tid, 1 if status else 0))
    conn.commit(); conn.close()

# 🔒 ДЕКОРАТОР PREMIUM
def premium_required(func):
    async def wrapper(message: types.Message, *args, **kwargs):
        user = await get_user(message.from_user.id)
        if not user or not user.get("is_premium"):
            await message.answer("💎 Эта функция доступна только в Premium.\nДля активации напиши админу или используй /premium",
                                 reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🏠 Главное меню")]], resize_keyboard=True))
            return
        return await func(message, *args, **kwargs)
    return wrapper

# ⌨️ КЛАВИАТУРЫ
def main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🔮 Гороскоп"), KeyboardButton(text="🌙 Луна")],
        [KeyboardButton(text="🎱 Магический шар"), KeyboardButton(text="💕 Совместимость")],
        [KeyboardButton(text="💎 Premium"), KeyboardButton(text="📊 Мой профиль")],
        [KeyboardButton(text="🏠 Главное меню")]
    ], resize_keyboard=True)

def zodiac_inline():
    signs = ["♈ Овен", "♉ Телец", "♊ Близнецы", "♋ Рак", "♌ Лев", "♍ Дева", "♎ Весы", "♏ Скорпион", "♐ Стрелец", "♑ Козерог", "♒ Водолей", "♓ Рыбы"]
    kb = [[InlineKeyboardButton(text=s, callback_data=f"sign_{s}")] for s in signs]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# 🌍 ДАННЫЕ
STOICHIOMETRY = {
    "♈ Овен": "fire", "♉ Телец": "earth", "♊ Близнецы": "air", "♋ Рак": "water",
    "♌ Лев": "fire", "♍ Дева": "earth", "♎ Весы": "air", "♏ Скорпион": "water",
    "♐ Стрелец": "fire", "♑ Козерог": "earth", "♒ Водолей": "air", "♓ Рыбы": "water"
}

COMPAT_VIBES = {
    ("fire", "fire"): {"vibe": "🔥🔥 Огненный союз: страсть, драйв и вечный двигатель!",
                       "plus": "Вы понимаете друг друга без слов, поддерживаете амбиции и не боитесь риска.",
                       "minus": "Вспышки ревности и конкуренции могут выжечь до тла, если не научиться уступать.",
                       "advice": "Направляйте огонь в общие цели: спорт, путешествия, бизнес. Избегайте споров на повышенных тонах."},
    ("fire", "air"): {"vibe": "💨🔥 Воздух раздувает пламя: лёгкость, идеи и взаимное вдохновение.",
                      "plus": "Интеллектуальная химия, общие мечты и умение находить выход из любых тупиков.",
                      "minus": "Огонь может сжечь хрупкие планы, а воздух — внезапно исчезнуть, оставив пепел.",
                      "advice": "Дайте друг другу свободу. Огонь пусть горит, воздух — пусть направляет. Не давите контролем."},
    ("fire", "water"): {"vibe": "💧🔥 Пар и туман: притяжение противоположностей с ноткой драмы.",
                        "plus": "Глубокая эмоциональная связь, где страсть встречает интуицию и заботу.",
                        "minus": "Вода пытается потушить огонь, огонь — испарить воду. Частые недопонимания на бытовом уровне.",
                        "advice": "Учитесь «держать температуру». Водному знаку — не гасить инициативу, огненному — не обжигать эмоциями."},
    ("fire", "earth"): {"vibe": "🌍🔥 Земля сдерживает огонь: стабильность против импульсивности.",
                        "plus": "Огонь даёт энергию, земля — фундамент. Вместе вы строите то, что выдержит испытание временем.",
                        "minus": "Темп жизни разный: один хочет бежать, другой — копать яму и ждать. Возможен конфликт ритмов.",
                        "advice": "Огненный знак: учитесь планировать. Земляной: разрешите себе спонтанность. Найдите золотую середину."},
    ("earth", "earth"): {"vibe": "🌍🌍 Двойная земля: надёжность, уют и материальный рост.",
                         "plus": "Вы строите империю вдвоём. Финансы, быт, долгосрочные планы — ваша сильная сторона.",
                         "minus": "Рутина может затянуть, как болото. Эмоциональная холодность и страх перемен.",
                         "advice": "Вносите новизну: новые маршруты, хобби, романтические сюрпризы. Не превращайте союз в бухгалтерию."},
    ("earth", "water"): {"vibe": "💧🌍 Плодородный союз: забота, глубина и тихая сила.",
                         "plus": "Вода питает землю, земля удерживает воду. Глубокая эмпатия, домашний уют, взаимная поддержка.",
                         "minus": "Оба знака могут замкнуться в себе, копить обиды и молчать, ожидая, что другой догадается.",
                         "advice": "Говорите о чувствах прямо. Не ждите телепатии. Земляному — проявлять мягкость, водному — просить словами."},
    ("earth", "fire"): {"vibe": "🔥🌍 Огонь сушит землю: энергия против инерции.",
                        "plus": "Огонь вдохновляет, земля воплощает. Отличный тандем для стартапов и реальных достижений.",
                        "minus": "Разные скорости и приоритеты. Конфликт «хочу сейчас» vs «надо подготовиться».",
                        "advice": "Огненный: уважайте темп партнёра. Земляной: не тормозите чужие мечты. Делите задачи по зонам ответственности."},
    ("earth", "air"): {"vibe": "💨🌍 Ветер и камень: лёгкость против основательности.",
                       "plus": "Воздух приносит идеи, земля даёт им форму. Интеллектуальный и практичный баланс.",
                       "minus": "Воздух кажется поверхностным, земля — скучной. Могут не находить общий язык в быту и планах.",
                       "advice": "Воздушному: заземляйте фантазии действиями. Земляному: не душите контролем. Уважайте разные способы мышления."},
    ("air", "air"): {"vibe": "💨💨 Двойной воздух: интеллект, коммуникации и свобода.",
                     "plus": "Вам никогда не скучно. Дебаты, идеи, путешествия, общие друзья и лёгкий формат отношений.",
                     "minus": "Эмоциональная дистанция, страх обязательств, «разговоры без действий».",
                     "advice": "Переходите от слов к делу. Планируйте совместные проекты. Не избегайте глубоких чувств под маской иронии."},
    ("air", "fire"): {"vibe": "🔥💨 Ветер раздувает пламя: творческий союз и взаимный драйв.",
                      "plus": "Вдохновение, харизма, общие цели. Вы заряжаете друг друга и легко преодолеваете препятствия.",
                      "minus": "Оба могут быть нетерпеливы. Конфликты из-за лидерства и «кто главный в идее».",
                      "advice": "Распределите роли: один генерирует, второй реализует. Избегайте соперничества, культивируйте команду."},
    ("air", "water"): {"vibe": "💧💨 Туман и волны: загадочность и эмоциональные качели.",
                       "plus": "Вода даёт глубину, воздух — перспективу. Творческий, интуитивный, поэтичный союз.",
                       "minus": "Непонимание языков любви: воздух рационален, вода эмоциональна. Частые недосказанности.",
                       "advice": "Водному: формулируйте потребности чётко. Воздушному: слушайте сердцем, а не только умом. Терпение — ключ."},
    ("air", "earth"): {"vibe": "🌍💨 Пыль и ветер: практичность против мечтательности.",
                       "plus": "Воздух видит возможности, земля строит мосты. Отлично для совместного бизнеса и проектов.",
                       "minus": "Разные ценности: один ценит стабильность, другой — перемены. Бытовые разногласия.",
                       "advice": "Составляйте чёткие договорённости. Уважайте границы. Не пытайтесь «переделать» партнёра под свой стандарт."},
    ("water", "water"): {"vibe": "💧💧 Океан чувств: эмпатия, интуиция и глубинная связь.",
                         "plus": "Полное эмоциональное слияние, поддержка, способность чувствовать партнёра на расстоянии.",
                         "minus": "Риск утонуть в драме, ревности, жертвенности. Границы размываются, обиды копятся.",
                         "advice": "Сохраняйте личное пространство. Не растворяйтесь в партнёре. Учитесь говорить «нет» без чувства вины."},
    ("water", "earth"): {"vibe": "🌍💧 Увлажнение и рост: забота, безопасность и тихая сила.",
                         "plus": "Вода питает, земля удерживает. Идеальный быт, финансы, взаимная опека и долгосрочные планы.",
                         "minus": "Оба могут замкнуться в проблемах, молчать и копить напряжение. Страх перемен.",
                         "advice": "Открыто обсуждайте чувства. Земляному: проявляйте нежность. Водному: не драматизируйте мелочи."},
    ("water", "fire"): {"vibe": "🔥💧 Испарение и пар: страсть, контрасты и трансформация.",
                        "plus": "Огонь даёт энергию, вода — глубину. Яркие эмоции, сильные притяжения, быстрый рост через кризисы.",
                        "minus": "Конфликт темпераментов: один хочет действия, другой — покоя. Эмоциональное выгорание.",
                        "advice": "Найдите общие ритуалы: совместный отдых, творчество, спорт. Не гасите чужой огонь, не обжигайте водой."},
    ("water", "air"): {"vibe": "💨💧 Волны и бриз: интеллектуально-эмоциональный тандем.",
                       "plus": "Вода учит глубине, воздух — лёгкости. Творческие союзы, путешествия, обмен идеями.",
                       "minus": "Непонимание приоритетов: логика vs интуиция. Чувство, что «меня не слышат».",
                       "advice": "Водному: не требуйте мгновенного понимания. Воздушному: включайте эмпатию. Компромисс через диалог."}
}

ORACLE_ANSWERS = [
    "🌟 Звёзды говорят: ДА", "✨ Судьба решила: ТОЧНО ДА", "🌕 Полная луна благоволит",
    "🪐 Юпитер расширяет возможности", "☀️ Солнечный аспект: время действовать",
    "🌙 Луна шепчет: ПОДОЖДИ", "⏳ Сатурн требует терпения", "🌑 Новолуние: дайте идее созреть",
    "🌍 Земля советует: ПРОВЕРЬ", "📜 Меркурий ретрограден: перечитайте детали",
    "💨 Ветер дует: НЕТ", "🌪️ Уран предупреждает: резкие перемены",
    "🔥 Огонь горит: СЕЙЧАС!", "⚡ Марс даёт зелёный свет", "💧 Вода течёт: ДОВЕРЬСЯ",
    "🌊 Нептун размывает границы: слушайте интуицию", "🌌 Космос молчит: СПРОСИ ПОЗЖЕ",
    "🌀 Плутон советует: отпустите старое", "🔮 Туман рассеется через неделю",
    "🕊️ Венера дарит шанс", "🕳️ Чёрная дына поглощает сомнения: действуйте смело",
    "🌈 Радуга после дождя: всё наладится", "🍂 Осенний ветер: время завершать",
    "🌱 Весенний рост: начинайте сейчас", "❄️ Звёздная пыль: замедлитесь",
    "🧭 Компас указывает на север: следуйте принципу", "🗝️ Ключ уже в ваших руках",
    "📿 Карма требует честности", "🎲 Колесо фортуны вращается", "🕯️ Свеча горит ровно: путь ясен",
    "🌠 Падающая звезда: загадайте желание", "🌵 Кактус в пустыне: будьте стойки",
    "🦉 Сова видит в темноте: не бойтесь неизвестного", "🦋 Трансформация неизбежна",
    "🐉 Дракон охраняет сокровище: рискните", "🕊️ Голубь мира: отпустите конфликт",
    "🌋 Вулкан спит: не будите лишний раз", "🌊 Прилив близко: готовьтесь",
    "🌙 Серп луны: малыми шагами к цели", "☯️ Инь и Янь: найдите баланс",
    "🔮 Хрустальный шар мутнеет: не форсируйте", "📜 Скрижали судьбы: вы на верном пути",
    "🕰️ Время работает на вас", "🌌 Млечный путь освещает дорогу",
    "🎭 Маски сброшены: будьте собой", "🌻 Подсолнух тянется к свету: ищите позитив",
    "🌑 Затмение скоро пройдёт", "🌟 Созвездие удачи выстроилось"
]

ASTRO_TIPS = [
    "🌿 Луна в знаке Земли: время для планирования бюджета, уборки и наведения порядка в документах.",
    "⚡ Меркурий активен: не отправляй важные сообщения после 22:00, лучше отложи до утра.",
    "🌊 Ретроградный период: перепроверяй билеты, договоры и контакты перед отправкой.",
    "☀️ Солнечный аспект: отличное время для старта проектов, публичных выступлений и личных начинаний.",
    "🌙 Лунный день: посвяти его очищению пространства, мыслей и отказу от токсичных привычек.",
    "🔮 Венера в гармонии: день для творчества, свиданий и выражения благодарности близким.",
    "🪐 Сатурн в аспекте: время взять на себя ответственность и выстроить долгосрочные рамки.",
    "🌪️ Уран активен: будь готов к внезапным озарениям, не цепляйся за устаревшие планы.",
    "🌑 Новолуние в воде: интуиция на пике. Слушай сны, записывай идеи, медитируй.",
    "🌕 Полнолуние в огне: энергия бьёт через край. Направь её в спорт или активный отдых.",
    "🌸 Венера входит в знак воздуха: лёгкие разговоры, флирт, новые знакомства благоприятны.",
    "🌾 Марс в знаке земли: действуй методично, не распыляйся, фокус на результате.",
    "🌌 Юпитер расширяет горизонты: учи новое, путешествуй, не бойся мечтать масштабно.",
    "🕯️ Нептун размывает границы: избегай иллюзий, проверяй факты, не давай в долг на словах.",
    "🌋 Плутон трансформирует: отпусти то, что изжило себя. Перемены ведут к росту.",
    "🌧️ Луна в скорпионе: глубинные чувства выходят наружу. Не копите обиды, говорите прямо.",
    "🌞 Солнце в деве: внимание к деталям, забота о здоровье, системный подход к задачам.",
    "🌪️ Воздушные тригоны: отличные дни для переговоров, обучения, обмена опытом.",
    "🌊 Водные квадратуры: эмоциональные качели. Заземляйся, дыши, не принимай решений на пике.",
    "🔥 Огненные оппозиции: конфликт интересов. Ищи компромисс, не вступай в спор ради спора.",
    "🌙 Лунный день благоприятен для покупок, если Луна в тельце или раке.",
    "🌑 Луна в козероге: время ставить цели, строить графики, работать на результат.",
    "🌕 Луна в весах: гармония в отношениях, совместные ужины, искусство, эстетика.",
    "🌪️ Меркурий в стрельце: расширяй кругозор, читай, путешествуй, философствуй.",
    "🌿 Венера в тельце: цени комфорт, вкусную еду, тактильность, простые радости.",
    "⚡ Марс в овне: действуй решительно, но не грубо. Энергия требует выхода.",
    "🌌 Сатурн в водолее: время реформ, работы в команде, цифровизации и социальных проектов.",
    "🕊️ Уран в тельце: неожиданные финансовые возможности, пересмотр ценностей.",
    "🌊 Нептун в рыбах: творческий подъём, сострадание, работа с подсознанием.",
    "🌞 Солнце в скорпионе: глубинный анализ, трансформация, работа с теневыми сторонами."
]

def get_moon_phase():
    known = datetime(2000, 1, 6, 18, 14); synodic = 29.53058867
    days = (datetime.now() - known).total_seconds() / 86400; phase = days % synodic
    if phase < 1.84566: return "🌑 Новолуние", 1, "🌱 Идеально для закладки основ, постановки целей и чистого листа."
    elif phase < 5.53699: return "🌓 Растущий серп", int(phase/1.84566)+1, "🌿 Время активных действий, поиска ресурсов и первых шагов."
    elif phase < 9.22831: return "🌗 Первая четверть", int((phase-5.53699)/1.84566)+8, "⚖️ Преодоление препятствий, корректировка курса, борьба с сомнениями."
    elif phase < 12.91963: return "🌔 Растущая луна", int((phase-9.22831)/1.84563)+15, "📈 Активный рост, масштабирование идей, притяжение возможностей."
    elif phase < 16.61096: return "🌕 Полнолуние", int((phase-12.91963)/1.84563)+16, "✨ Пик энергии, завершение циклов, публичность, эмоциональная ясность."
    elif phase < 20.30228: return "🌖 Убывающая луна", int((phase-16.61096)/1.84563)+17, "🔄 Пересмотр, анализ ошибок, передача опыта, постепенное снижение темпа."
    elif phase < 23.99361: return "🌘 Последняя четверть", int((phase-20.30228)/1.84563)+23, "🧹 Очистка, завершение дел, прощение, подготовка к новому циклу."
    else: return "🌒 Убывающий серп", int((phase-23.99361)/1.84563)+24, "🌌 Тишина, отдых, подведение итогов, сбор энергии перед новолунием."

def get_astro_tip(): return random.choice(ASTRO_TIPS)

def get_horoscope_reliable(sign):
    today = datetime.now().strftime("%Y-%m-%d")
    seed_val = int(hashlib.md5(f"{today}_{sign}".encode()).hexdigest(), 16)
    rng = random.Random(seed_val)
    intros = ["Сегодня звёзды выстраиваются в редкий гармоничный узор, наполняя день энергией обновления.",
        "Лунный цикл входит в активную фазу, обостряя интуицию и подсказывая верные решения.",
        "Планетарные аспекты благоприятствуют смелым шагам и творческому поиску.",
        "Энергетический фон дня настроен на завершение начатого и честное подведение итогов.",
        "Космические ритмы подсказывают: время замедлиться и прислушаться к внутреннему голосу.",
        "Солнечная активность на пике — ваш личный магнетизм притягивает нужные события.",
        "Венера и Марс формируют редкий треугольник, открывая двери для глубокого контакта.",
        "Меркурий требует внимания к деталям: мелочи могут изменить ход больших дел.",
        "Юпитер посылает сигнал расширения границ: мечтайте масштабно и действуйте решительно.",
        "Сатурн напоминает о дисциплине: порядок в мыслях приведёт к стабильным результатам.",
        "Нептун размывает границы восприятия — доверьтесь снам и тихим подсказкам.",
        "Уран приносит внезапные инсайты: будьте открыты к нестандартным решениям."]
    career = ["💼 В делах: сегодня удача на стороне системных действий. Возможна поддержка коллег или выгодное предложение.",
        "💼 Рабочие процессы могут пойти не по плану, но это откроет скрытые резервы. Ваша гибкость будет вознаграждена.",
        "💼 Отличный день для переговоров и старта проектов. Харизма поможет склонить чашу весов в вашу пользу.",
        "💼 Финансовая энергия требует осторожности: избегайте спонтанных трат, займитесь аудитом расходов.",
        "💼 Важно делегировать рутину и сфокусироваться на стратегии. Кто-то возьмёт нагрузку, если попросите прямо.",
        "💼 Возможны задержки в коммуникации, но терпение и чёткие формулировки всё исправят. Не решайте в спешке."]
    love = ["❤️ В личной сфере: день благоприятен для искренних разговоров. Одиноким стоит присмотреться к знакомым.",
        "❤️ Эмоциональный фон нестабилен: избегайте провокаций. Лучшее лекарство — совместный ужин или прогулка.",
        "❤️ Романтическая энергия на пике! Проявите инициативу или возобновите приятное знакомство.",
        "❤️ Партнёр может нуждаться в поддержке. Проявите эмпатию, выслушайте без оценок.",
        "❤️ Взаимоотношения требуют баланса между личным пространством и близостью. Честность сегодня ценнее идеальности.",
        "❤️ День подходит для совместного творчества или поездок. Общие впечатления сблизят сильнее слов."]
    advice = ["💡 Совет: не пытайтесь контролировать всё. Отпустите уходящее, сосредоточьтесь на том, что можете изменить сегодня.",
        "💡 Звёзды предупреждают: остерегайтесь сплетен и навязанных мнений. Ваша интуиция — самый точный компас.",
        "💡 Благоприятное время для заботы о здоровье: прогулка, медитация или ранний сон дадут энергию на неделю.",
        "💡 Не откладывайте важное. Сегодняшний импульс уникален: сделайте первый шаг, даже если не видите всей дороги.",
        "💡 Помните про закон сохранения энергии: чем больше вкладываете в добро, тем больше возможностей возвращается."]
    stone = rng.choice(['аметист', 'горный хрусталь', 'тигровый глаз', 'лунный камень', 'цитрин', 'обсидиан', 'розенкварц', 'чёрный турмалин'])
    color = rng.choice(['изумрудный', 'небесно-голубой', 'золотистый', 'бордовый', 'серебристый', 'пурпурный', 'тёплый бежевый', 'индиго'])
    time = rng.choice(['09:00–11:00', '13:00–15:00', '17:00–19:00', '20:00–22:00', '07:00–09:00'])
    return f"🌟 {rng.choice(intros)}\n\n{rng.choice(career)}\n\n{rng.choice(love)}\n\n{rng.choice(advice)}\n\n🍀 Талисман: {stone} | 🎨 Цвет дня: {color} | ⏰ Пик удачи: {time}"

SIGN_MAP = {
    "овен": "♈ Овен", "овна": "♈ Овен", "телец": "♉ Телец", "тельца": "♉ Телец",
    "близнецы": "♊ Близнецы", "близнецов": "♊ Близнецы", "рак": "♋ Рак", "рака": "♋ Рак",
    "лев": "♌ Лев", "льва": "♌ Лев", "дева": "♍ Дева", "девы": "♍ Дева", "весы": "♎ Весы",
    "скорпион": "♏ Скорпион", "скорпиона": "♏ Скорпион", "стрелец": "♐ Стрелец", "стрельца": "♐ Стрелец",
    "козерог": "♑ Козерог", "козерога": "♑ Козерог", "водолей": "♒ Водолей", "водолея": "♒ Водолей", "рыбы": "♓ Рыбы"
}

# 🎯 ОБРАБОТЧИКИ

def get_welcome_caption(name=None):
    prefix = f"Привет, {name}! ✨\n\n" if name else ""
    return (
        f"{prefix}Я — проводник между мирами видимого и скрытого.\n"
        "Здесь ты узнаешь, что готовят планеты,\n"
        "услышишь совет Луны и раскроешь карты судьбы.\n\n"
        "🔮 **Бесплатно:**\n"
        "• Гороскоп на день\n"
        "• Фаза Луны и советы\n"
        "• Совместимость по стихиям\n"
        "• Магический шар ответов\n\n"
        "💎 **Открой больше в Premium:**\n"
        "• Натальная карта рождения\n"
        "• Прогноз транзитов планет\n"
        "• Персональные рекомендации\n\n"
        "✨ Выбери путь:"
    )

async def send_welcome(message, caption=None):
    if caption is None:
        caption = get_welcome_caption(message.from_user.first_name)
    try:
        await message.answer_photo(
            photo=WELCOME_IMAGE_URL,
            caption=caption,
            reply_markup=main_kb(),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"❌ Ошибка отправки фото: {e}")
        await message.answer(caption, reply_markup=main_kb(), parse_mode="Markdown")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await send_welcome(message)
    logger.info(f"✅ /start от {message.from_user.id}")

@dp.message(F.text == "🏠 Главное меню")
async def cmd_home(message: types.Message):
    logger.info(f"🏠 Кнопка 'Главное меню' от {message.from_user.id}")
    await send_welcome(message, get_welcome_caption("✨"))

@dp.message(Command("profile"))
@dp.message(F.text == "📊 Мой профиль")
async def cmd_profile(message: types.Message):
    u = await get_user(message.from_user.id)
    if not u: return
    prem = "💎 Да" if u.get("is_premium") else "🆓 Нет"
    sign = u.get("zodiac_sign") or "Не выбран"
    await message.answer(f"👤 {u['first_name']}\n♐ Знак: {sign}\n📅 Дата: {u['birth_date'] or 'Не указана'}\n💎 Premium: {prem}",
                         reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🏠 Главное меню")]], resize_keyboard=True))

@dp.message(F.text == "🔮 Гороскоп")
async def horoscope_menu(message: types.Message):
    await message.answer("Выбери знак 👇", reply_markup=zodiac_inline())

@dp.callback_query(F.data.startswith("sign_"))
async def show_horoscope(cb: types.CallbackQuery):
    sign = cb.data.replace("sign_", "")
    text = get_horoscope_reliable(sign)
    await save_zodiac(cb.from_user.id, sign)  # 🔑 ТЕПЕРЬ ГАРАНТИРОВАННО СОХРАНЯЕТ
    await cb.message.answer(f"{sign}\n\n{text}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]]))
    await cb.answer()

@dp.callback_query(F.data == "back_main")
async def back_to_main(cb: types.CallbackQuery):
    logger.info(f"🔙 Inline-кнопка 'Главное меню' от {cb.from_user.id}")
    await cb.message.answer(get_welcome_caption("✨"), reply_markup=main_kb(), parse_mode="Markdown")
    await cb.answer()

@dp.message(F.text == "🌙 Луна")
async def cmd_moon(message: types.Message):
    phase, day, rec = get_moon_phase()
    await message.answer(f"🌙 **Фаза**: {phase}\n📅 **Лунный день**: {day}\n💡 **Рекомендация**: {rec}\n\n{get_astro_tip()}",
                         reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🏠 Главное меню")]], resize_keyboard=True), parse_mode="Markdown")

@dp.message(F.text == "🎱 Магический шар")
async def cmd_orb(message: types.Message):
    await message.answer(f"🎱 {random.choice(ORACLE_ANSWERS)}",
                         reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🏠 Главное меню")]], resize_keyboard=True))

@dp.message(F.text == "💕 Совместимость")
async def cmd_compat_prompt(message: types.Message):
    await message.answer("💕 **Расчёт совместимости**\n\nНапиши имя и знак зодиака партнёра.\nПримеры:\n• `Света Близнецы`\n• `Макс Скорпион`\n• `Аня Рыбы`\n\nДоступные знаки:\nОвен, Телец, Близнецы, Рак, Лев, Дева, Весы, Скорпион, Стрелец, Козерог, Водолей, Рыбы",
                         reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🏠 Главное меню")]], resize_keyboard=True), parse_mode="Markdown")

@dp.message()
async def calc_compat(message: types.Message):
    text = message.text.strip(); text_lower = text.lower()
    found_sign = found_key = None
    for key, full_sign in SIGN_MAP.items():
        if re.search(r'\b' + re.escape(key) + r'\b', text_lower):
            found_sign, found_key = full_sign, key; break
    if not found_sign: return  # Пропускаем, если это не команда совместимости
    
    user = await get_user(message.from_user.id)
    saved_sign = user.get("zodiac_sign", "").strip() if user else ""
    if not saved_sign:
        return await message.answer("❓ Сначала узнай свой знак в разделе 🔮 Гороскоп!",
                                    reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🏠 Главное меню")]], resize_keyboard=True))
    
    my_el, their_el = STOICHIOMETRY[saved_sign], STOICHIOMETRY[found_sign]
    data = COMPAT_VIBES.get((my_el, their_el)) or COMPAT_VIBES.get((their_el, my_el)) or COMPAT_VIBES[("earth", "air")]
    name_part = text[:text.lower().index(found_key)].strip().rstrip(" -:")
    name = name_part.capitalize() if name_part else "Партнёр"
    
    await message.answer(
        f"💕 {user.get('first_name', 'Пользователь')} ({saved_sign}) + {name} ({found_sign})\n\n"
        f"**Общая вибрация:** {data['vibe']}\n**Сильная сторона:** {data['plus']}\n"
        f"**Зона риска:** {data['minus']}\n**Совет звёзд:** {data['advice']}\n\n"
        f"💡 *Упрощённый расчёт по стихиям. Для детального анализа по датам и времени нужен Premium.*",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🏠 Главное меню")]], resize_keyboard=True), parse_mode="Markdown")

@dp.message(F.text == "💎 Premium")
async def cmd_premium(message: types.Message):
    await message.answer("💎 **Premium возможности:**\n📊 Полная натальная карта\n💕 Детальная совместимость по датам\n🌌 Ежемесячный прогноз транзитов\n🔮 Персональные рекомендации\n⚡ Приоритетная поддержка\n\n💰 Стоимость: 299₽/мес\n📩 Для активации напиши: `/buy` или свяжись с админом",
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                             [InlineKeyboardButton(text="🛒 Купить Premium", callback_data="buy_premium")],
                             [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]]))

@dp.callback_query(F.data == "buy_premium")
async def buy_premium(cb: types.CallbackQuery):
    await cb.message.edit_text("📩 Для оплаты и активации напиши админу: @ТВОЙ_НИК\nПосле подтверждения бот обновит статус.",
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]]))
    await cb.answer()

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
    await message.answer(f"📊 **Натальная карта сгенерирована!**\n📅 {data['birth_date']} | 🕐 {data['birth_time']} | 🌍 {data['birth_place']}\n☀️ Полный отчёт в обработке...",
                         reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🏠 Главное меню")]], resize_keyboard=True))
    await state.clear()

@dp.message(Command("transits"))
@premium_required
async def cmd_transits(message: types.Message):
    await message.answer("🌌 **Прогноз транзитов на месяц**\n♄ Сатурн: время терпения.\n♃ Юпитер: удача в обучении.\n🪐 Плутон: трансформация связей.\n💡 Совет: Адаптируйся к переменам.",
                         reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🏠 Главное меню")]], resize_keyboard=True))

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

# 🌐 RENDER
async def handle_health(request): return web.Response(text="OK 🤖")
async def start_webserver(port):
    app = web.Application(); app.add_routes([web.get('/', handle_health), web.get('/health', handle_health)])
    runner = web.AppRunner(app); await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port); await site.start()
    logger.info(f"🌐 Веб-сервер на порту {port}"); return runner

async def run_with_restart():
    while True:
        try: logger.info("🔄 Запуск polling..."); await dp.start_polling(bot)
        except Exception as e: logger.error(f"💥 Ошибка: {e}. Перезапуск через 15с..."); await asyncio.sleep(15)
        await asyncio.sleep(5)

async def main():
    logger.info("🚀 Бот запускается..."); init_db()
    try: me = await bot.me(); logger.info(f"✅ Авторизован: @{me.username}")
    except Exception as e: logger.error(f"❌ Ошибка токена: {e}"); return
    port = int(os.getenv("PORT", 10000)); await start_webserver(port)
    await run_with_restart()

if __name__ == "__main__": asyncio.run(main())
