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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_LINK = os.getenv("PAYMENT_LINK", "https://t.me/YOUR_ADMIN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

if not BOT_TOKEN:
    logging.error("❌ BOT_TOKEN не найден в переменных окружения!"); sys.exit(1)

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
        id INTEGER PRIMARY KEY, telegram_id INTEGER UNIQUE, username TEXT, first_name TEXT,
        zodiac_sign TEXT, is_premium INTEGER DEFAULT 0, daily_credits INTEGER DEFAULT 1,
        last_credit_date TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit(); conn.close()

def get_safe_name(user_obj):
    return user_obj.first_name or user_obj.username or "✨"

def get_user_dict(tid):
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    c = conn.cursor(); c.execute("SELECT * FROM users WHERE telegram_id=?", (tid,))
    res = c.fetchone(); conn.close()
    return dict(res) if res else None

def add_user(tid, uname, fname):
    conn = sqlite3.connect(DB_PATH)
    today = datetime.now().strftime("%Y-%m-%d")
    conn.execute("INSERT OR IGNORE INTO users (telegram_id, username, first_name, daily_credits, last_credit_date) VALUES (?,?,?,?,?)",
                 (tid, uname, fname, 1, today))
    conn.commit(); conn.close()

def get_credits(tid):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT daily_credits, last_credit_date FROM users WHERE telegram_id=?", (tid,))
    res = c.fetchone()
    if not res or res[1] != today:
        conn.execute("UPDATE users SET daily_credits=1, last_credit_date=? WHERE telegram_id=?", (today, tid))
        conn.commit(); conn.close(); return 1
    conn.close(); return res[0] if res[0] else 1

def use_credit(tid):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET daily_credits=daily_credits-1 WHERE telegram_id=?", (tid,))
    conn.commit(); conn.close()

def save_sign(tid, sign):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET zodiac_sign=? WHERE telegram_id=?", (sign, tid))
    if conn.total_changes == 0:
        conn.execute("INSERT INTO users (telegram_id, zodiac_sign) VALUES (?,?)", (tid, sign))
    conn.commit(); conn.close()

# ⌨️ КЛАВИАТУРЫ
def main_kb(name, sign, credits):
    sign_emoji = sign.split()[0] if sign else "❓"
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
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_main")]])

def zodiac_kb():
    signs = ["♈ Овен", "♉ Телец", "♊ Близнецы", "♋ Рак", "♌ Лев", "♍ Дева", "♎ Весы", "♏ Скорпион", "♐ Стрелец", "♑ Козерог", "♒ Водолей", "♓ Рыбы"]
    kb = [[InlineKeyboardButton(text=s, callback_data=f"sign_{s}")] for s in signs]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# 🌍 ДАННЫЕ
STOICH = {"♈ Овен":"fire","♉ Телец":"earth","♊ Близнецы":"air","♋ Рак":"water","♌ Лев":"fire","♍ Дева":"earth","♎ Весы":"air","♏ Скорпион":"water","♐ Стрелец":"fire","♑ Козерог":"earth","♒ Водолей":"air","♓ Рыбы":"water"}
COMPAT = {
    ("fire","fire"):{"v":"🔥 Огонь + Огонь","p":"Страсть и драйв","m":"Конкуренция","a":"Направляйте энергию в общие цели"},
    ("fire","air"):{"v":"🔥 Огонь + Воздух","p":"Вдохновение","m":"Нестабильность","a":"Дайте друг другу свободу"},
    ("fire","water"):{"v":"🔥 Огонь + Вода","p":"Глубина эмоций","m":"Непонимание","a":"Учитесь слушать"},
    ("fire","earth"):{"v":"🔥 Огонь + Земля","p":"Энергия + Стабильность","m":"Разный темп","a":"Найдите баланс"},
    ("earth","earth"):{"v":"🌍 Земля + Земля","p":"Надёжность","m":"Рутина","a":"Добавляйте новизну"},
    ("earth","water"):{"v":"🌍 Земля + Вода","p":"Забота и уют","m":"Замкнутость","a":"Говорите о чувствах"},
    ("earth","air"):{"v":"🌍 Земля + Воздух","p":"Идеи + Реализация","m":"Разные ценности","a":"Уважайте различия"},
    ("air","air"):{"v":"💨 Воздух + Воздух","p":"Интеллект","m":"Поверхностность","a":"Переходите к делу"},
    ("air","water"):{"v":"💨 Воздух + Вода","p":"Творчество","m":"Непонимание","a":"Слушайте сердцем"},
    ("water","water"):{"v":"💧 Вода + Вода","p":"Эмпатия","m":"Драма","a":"Сохраняйте границы"}
}
ORACLE = ["🌟 Звёзды говорят: ДА", "✨ Судьба: ТОЧНО ДА", "🌕 Луна благоволит", "🌙 Подожди", "⏳ Терпение", "🌍 Проверь детали", "💨 Нет", "🔥 ДЕЙСТВУЙ!", "💧 Доверься интуиции", "🌌 Спроси позже", "🌀 Отпусти старое", "🕊️ Венера дарит шанс"]

def get_moon():
   
