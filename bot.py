import asyncio, logging, sys, os, sqlite3, random, hashlib
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_LINK = os.getenv("PAYMENT_LINK", "https://t.me/YOUR_ADMIN")
if not BOT_TOKEN: logging.error("❌ BOT_TOKEN not found!"); sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
DB = "astro.db"
WELCOME_IMG = "https://cdn.pixabay.com/photo/2017/08/16/22/38/universe-2650272_1280.jpg"
ASTRO_AI_IMG = "https://cdn.pixabay.com/photo/2016/02/04/22/38/star-1180004_1280.jpg"

def init_db():
    c = sqlite3.connect(DB); c.execute('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,telegram_id INTEGER UNIQUE,username TEXT,first_name TEXT,zodiac_sign TEXT,is_premium INTEGER DEFAULT 0,daily_credits INTEGER DEFAULT 1,last_credit_date TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)'); c.commit(); c.close()

def safe_name(u): return u.first_name or u.username or "✨"
def get_user(tid):
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; r = c.execute("SELECT * FROM users WHERE telegram_id=?", (tid,)).fetchone(); c.close()
    return dict(r) if r else None
def add_user(tid, un, fn):
    c = sqlite3.connect(DB); c.execute("INSERT OR IGNORE INTO users(telegram_id,username,first_name,daily_credits,last_credit_date) VALUES(?,?,?,?,?)", (tid, un, fn, 1, datetime.now().strftime("%Y-%m-%d"))); c.commit(); c.close()
def get_credits(tid):
    c = sqlite3.connect(DB); today = datetime.now().strftime("%Y-%m-%d"); r = c.execute("SELECT daily_credits,last_credit_date FROM users WHERE telegram_id=?", (tid,)).fetchone()
    if not r or r[1] != today: c.execute("UPDATE users SET daily_credits=1,last_credit_date=? WHERE telegram_id=?", (today, tid)); c.commit(); c.close(); return 1
    c.close(); return r[0] or 1
def use_credit(tid): c = sqlite3.connect(DB); c.execute("UPDATE users SET daily_credits=daily_credits-1 WHERE telegram_id=?", (tid,)); c.commit(); c.close()
def save_sign(tid, s):
    c = sqlite3.connect(DB); c.execute("UPDATE users SET zodiac_sign=? WHERE telegram_id=?", (s, tid))
    if c.total_changes == 0: c.execute("INSERT INTO users(telegram_id,zodiac_sign) VALUES(?,?)", (tid, s))
    c.commit(); c.close()

def main_kb(n, sg, cr): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔮 Гороскоп", callback_data="nav_horoscope")],[InlineKeyboardButton(text="🤖 Astro AI", callback_data="nav_astro_ai")],[InlineKeyboardButton(text="🌙 Луна", callback_data="nav_moon"), InlineKeyboardButton(text="🎱 Шар", callback_data="nav_orb")],[InlineKeyboardButton(text="💕 Совместимость", callback_data="nav_compat")],[InlineKeyboardButton(text="💎 Premium", callback_data="nav_premium"), InlineKeyboardButton(text=f"👤 {n} ({cr}🎁)", callback_data="nav_profile")]])
def back_kb(): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]])
def zodiac_kb():
    signs = ["♈ Овен","♉ Телец","♊ Близнецы","♋ Рак","♌ Лев","♍ Дева","♎ Весы","♏ Скорпион","♐ Стрелец","♑ Козерог","♒ Водолей","♓ Рыбы"]
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=s, callback_data=f"sign_{s}")] for s in signs] + [[InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]])

STOICH = {"♈ Овен":"fire","♉ Телец":"earth","♊ Близнецы":"air","♋ Рак":"water","♌ Лев":"fire","♍ Дева":"earth","♎ Весы":"air","♏ Скорпион":"water","♐ Стрелец":"fire","♑ Козерог":"earth","♒ Водолей":"air","♓ Рыбы":"water"}
COMPAT = {("fire","fire"):"🔥 Огонь+Огонь|Страсть|Конкуренция|Направляйте энергию в общие цели",("fire","air"):"🔥 Огонь+Воздух|Вдохновение|Нестабильность|Дайте свободу",("fire","water"):"🔥 Огонь+Вода|Эмоции|Непонимание|Учитесь слушать",("fire","earth"):"🔥 Огонь+Земля|Энергия+Стабильность|Разный темп|Найдите баланс",("earth","earth"):"🌍 Земля+Земля|Надёжность|Рутина|Добавляйте новизну",("earth","water"):"🌍 Земля+Вода|Забота|Замкнутость|Говорите о чувствах",("earth","air"):"🌍 Земля+Воздух|Идеи+Реализация|Разные ценности|Уважайте различия",("air","air"):"💨 Воздух+Воздух|Интеллект|Поверхностность|Переходите к делу",("air","water"):"💨 Воздух+Вода|Творчество|Непонимание|Слушайте сердцем",("water","water"):"💧 Вода+Вода|Эмпатия|Драма|Сохраняйте границы"}
ORACLE = ["🌟 ДА","✨ ТОЧНО ДА","🌕 Луна благоволит","🌙 Подожди","⏳ Терпение","🌍 Проверь","💨 Нет","🔥 ДЕЙСТВУЙ!","💧 Доверься","🌌 Спроси позже","🌀 Отпусти","🕊️ Венера дарит шанс"]

def get_moon():
    k = datetime(2000,1,6,18,14); syn = 29.53058867; d = (datetime.now()-k).total_seconds()/86400; p = d%syn
    if p<1.84566: return "🌑 Новолуние",1,"🌱 Начинайте"
    elif p<5.53699: return "🌓 Растущая",int(p/1.84566)+1,"🌿 Действуйте"
    elif p<9.22831: return "🌗 1-я четверть",8,"⚖️ Корректируйте"
    elif p<12.91963: return "🌔 Растущая",15,"📈 Масштабируйте"
    elif p<16.61096: return "🌕 Полнолуние",16,"✨ Завершайте"
    elif p<20.30228: return "🌖 Убывающая",17,"🔄 Анализируйте"
    elif p<23.99361: return "🌘 4-я четверть",23,"🧹 Очищайте"
    else: return "🌒 Убывающая",24,"🌌 Отдыхайте"

def get_horoscope(sign):
    t = datetime.now().strftime("%Y-%m-%d"); s = int(hashlib.md5(f"{t}_{sign}".encode()).hexdigest(),16); r = random.Random(s)
    I = ["Звёзды в гармонии","Луна обостряет интуицию","Планеты благоприятствуют","Космос подсказывает: замедлись"]
    C = ["💼 Удача в системных действиях","💼 Гибкость вознаграждена","💼 День для переговоров","💼 Избегайте спонтанных трат"]
    L = ["❤️ Время для разговоров","❤️ Избегайте провокаций","❤️ Романтическая энергия","❤️ Проявите эмпатию"]
    A = ["💡 Отпустите уходящее","💡 Доверяйте интуиции","💡 Позаботьтесь о здоровье","💡 Сделайте первый шаг"]
    return f"🌟 {r.choice(I)}\n\n{r.choice(C)}\n\n{r.choice(L)}\n\n{r.choice(A)}\n\n🍀 {r.choice(['аметист','хрусталь','тигровый глаз'])} | 🎨 {r.choice(['изумрудный','голубой','золотой'])}"

def astro_ai(sign, name):
    el = STOICH.get(sign,"earth"); th = {"fire":["карьера","лидерство","творчество"],"earth":["финансы","здоровье","стабильность"],"air":["общение","обучение","идеи"],"water":["отношения","эмоции","интуиция"]}
    t = random.choice(th[el])
    return f"🔮 **Astro AI для {name}**\n\n📅 Фокус: {t}\n⚡ Энергия: {random.choice(['высокая','средняя','трансформирующая'])}\n🎯 Время: {random.choice(['09:00-11:00','14:00-16:00','19:00-21:00'])}\n⚠️ Остерегайся: {random.choice(['поспешных решений','эмоциональных всплесков','прокрастинации'])}\n\n💡 Совет: {random.choice(['Действуйте решительно','Проявите терпение','Доверьтесь интуиции','Планируйте заранее'])}"

async def send_menu(obj, is_cb=False):
    tid = obj.from_user.id; u = get_user(tid); n = safe_name(obj.from_user); sg = u.get("zodiac_sign") if u else None; cr = get_credits(tid)
    cap = f"🔮 С возвращением, {n}!\n\n⭐ Знак: {sg or 'не выбран'} | 🎁 Прогнозов: {cr}\n\nВыбери раздел ✨"
    if is_cb: await obj.message.edit_text(cap, reply_markup=main_kb(n, sg, cr)); await obj.answer()
    else:
        try: await obj.answer_photo(photo=WELCOME_IMG, caption=cap, reply_markup=main_kb(n, sg, cr))
        except: await obj.answer(cap, reply_markup=main_kb(n, sg, cr))

@dp.message(Command("start"))
async def start(msg): add_user(msg.from_user.id, msg.from_user.username, msg.from_user.first_name); await send_menu(msg)
@dp.message(F.text == "🏠 Главное меню")
async def home(msg): await send_menu(msg)
@dp.callback_query(F.data == "back_main")
async def back(cb): await send_menu(cb, True)
@dp.callback_query(F.data == "nav_horoscope")
async def horo_menu(cb): await cb.message.edit_text("🔮 **Выбери знак**", reply_markup=zodiac_kb()); await cb.answer()
@dp.callback_query(F.data.startswith("sign_"))
async def show_horoscope(cb):
    sign = cb.data.replace("sign_",""); cr = get_credits(cb.from_user.id)
    if cr <= 0: await cb.answer("⚠️ Бесплатный прогноз закончился! Premium = безлимит.", show_alert=True); return
    use_credit(cb.from_user.id); save_sign(cb.from_user.id, sign)
    await cb.message.edit_text(f"{sign}\n\n{get_horoscope(sign)}\n\n🎁 Осталось: {cr-1}", reply_markup=back_kb()); await cb.answer()
@dp.callback_query(F.data == "nav_astro_ai")
async def ai(cb):
    u = get_user(cb.from_user.id); n = safe_name(cb.from_user); sg = u.get("zodiac_sign") if u else None
    if not sg: await cb.message.edit_text("🤖 **Astro AI**\n\nСначала выбери знак в 🔮 Гороскоп!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔮 Выбрать знак", callback_data="nav_horoscope")]])); await cb.answer(); return
    pred = astro_ai(sg, n)
    try: await cb.message.answer_photo(photo=ASTRO_AI_IMG, caption=pred, reply_markup=back_kb(), parse_mode="Markdown"); await cb.message.delete()
    except: await cb.message.edit_text(pred, reply_markup=back_kb(), parse_mode="Markdown")
    await cb.answer()
@dp.callback_query(F.data == "nav_moon")
async def moon(cb): ph, dy, rc = get_moon(); await cb.message.edit_text(f"🌙 **Фаза**: {ph}\n📅 **День**: {dy}\n💡 **Совет**: {rc}", reply_markup=back_kb(), parse_mode="Markdown"); await cb.answer()
@dp.callback_query(F.data == "nav_orb")
async def orb(cb): await cb.message.edit_text(f"🎱 {random.choice(ORACLE)}", reply_markup=back_kb()); await cb.answer()
@dp.callback_query(F.data == "nav_compat")
async def compat_menu(cb): await cb.message.edit_text("💕 **Совместимость**\n\nНапиши: `Имя Знак`\nПример: `Света Близнецы`", reply_markup=back_kb(), parse_mode="Markdown"); await cb.answer()
@dp.callback_query(F.data == "nav_premium")
async def prem(cb):
    txt = "💎 **Premium**\n\n📊 Натальная карта\n💕 Детальная совместимость\n🌌 Прогноз транзитов\n🔮 Персональные советы\n⚡ Безлимитные прогнозы\n\n💰 299₽/мес"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💳 Оплатить", url=PAYMENT_LINK)],[InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]])
    await cb.message.edit_text(txt, reply_markup=kb); await cb.answer()
@dp.callback_query(F.data == "nav_profile")
async def prof(cb):
    u = get_user(cb.from_user.id)
    if not u: return
    txt = f"👤 **Профиль**\n\nИмя: {u.get('first_name') or 'Не указано'}\n♐ Знак: {u.get('zodiac_sign') or 'Не выбран'}\n💎 Premium: {'Да' if u.get('is_premium') else 'Нет'}\n🎁 Прогнозов: {get_credits(cb.from_user.id)}"
    await cb.message.edit_text(txt, reply_markup=back_kb(), parse_mode="Markdown"); await cb.answer()

@dp.message()
async def handle_compat(msg):
    txt = msg.text.strip().lower(); smap = {"овен":"♈ Овен","телец":"♉ Телец","близнецы":"♊ Близнецы","рак":"♋ Рак","лев":"♌ Лев","дева":"♍ Дева","весы":"♎ Весы","скорпион":"♏ Скорпион","стрелец":"♐ Стрелец","козерог":"♑ Козерог","водолей":"♒ Водолей","рыбы":"♓ Рыбы"}
    found = next((v for k,v in smap.items() if k in txt), None)
    if not found: return
    u = get_user(msg.from_user.id); us = u.get("zodiac_sign") if u else None
    if not us: await msg.answer("❓ Сначала выбери свой знак в меню 🔮", reply_markup=main_kb("User", None, 1)); return
    el1, el2 = STOICH[us], STOICH[found]
    data = COMPAT.get((el1,el2)) or COMPAT.get((el2,el1)) or "💫 Уникальный союз|Гармония|Нет|Доверяйте"
    v,p,m,a = data.split("|")
    nm = msg.text.replace(found,"").replace(next((k for k,v in smap.items() if v==found),""),"").strip().capitalize() or "Партнёр"
    await msg.answer(f"💕 {u.get('first_name','Вы')} ({us}) + {nm} ({found})\n\n**{v}**\n✅ {p}\n⚠️ {m}\n💡 {a}", reply_markup=main_kb(u.get('first_name','User'), us, get_credits(msg.from_user.id)), parse_mode="Markdown")

# 🌐 WEB SERVER (запускается ПЕРЕД polling для Render)
async def health(req): return web.Response(text="OK 🤖")
async def start_web(port):
    app = web.Application(); app.add_routes([web.get('/', health), web.get('/health', health)])
    runner = web.AppRunner(app); await runner.setup(); site = web.TCPSite(runner, '0.0.0.0', port); await site.start()
    logging.info(f"🌐 Server on port {port}")

async def run_polling():
    while True:
        try: logging.info("🔄 Polling..."); await dp.start_polling(bot); break
        except Exception as e: logging.error(f"💥 {e}"); await asyncio.sleep(10)

async def main():
    logging.info("🚀 Starting..."); init_db()
    try: m = await bot.me(); logging.info(f"✅ @{m.username}")
    except Exception as e: logging.error(f"❌ {e}"); return
    # Сначала веб-сервер (чтобы Render увидел порт), потом polling
    await start_web(int(os.getenv("PORT", 10000)))
    await run_polling()

if __name__ == "__main__": asyncio.run(main())
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site
