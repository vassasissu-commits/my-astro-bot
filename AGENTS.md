# AGENTS.md — Vedana Astro Bot (@SuperAstro2027_bot)

## Tech Stack
- Python 3.11.9, aiogram 3.x, aiohttp webhook
- SQLite (astro_users.db) — WAL mode
- Render.com Free Tier (webhook), UptimeRobot
- LLM: Groq (llama-3.1-8b-instant)
- Payments: Telegram Stars (XTR)
- TTS: Edge TTS (Svetlana/Dmitry)
- Images: Pexels + Pixabay API
- Git: GitHub → Render auto-deploy (настройка 22.05)

## Project Type
Telegram-бот-астролог «Ведана» — гороскопы, таро, руны, натальная карта, нумерология, совместимость, магический шар

## Structure (single-file)
- `bot.py` — весь бот (хендлеры, FSM, БД, платежи, webhook) в 1062 строки
- `config.py` — API ключи, настройки TTS, тесты (HARDCODED keys — надо в .env)
- `.env` — переменные окружения
- `requirements.txt` — зависимости
- `runtime.txt` — python-3.11.9
- `astro.db` / `astro_users.db` — SQLite базы

## Critical Rules
- parse_mode: always use "HTML" (NOT Markdown — crashes on underscores/bold)
- Variables must be initialized BEFORE try blocks to avoid UnboundLocalError
- API keys must NEVER be hardcoded — only from .env / os.getenv()
- WEBHOOK_URL is hardcoded in bot.py — заменить на RENDER_EXTERNAL_URL
- SQLite не подходит для Render (сбрасывается при рестарте) — нужен PostgreSQL

## Key Files
- `bot.py` — главный и единственный файл бота (1062 строки)
- `config.py` — API ключи (требует рефакторинга)
- `.env` — секреты

## Common Issues Found
- API keys hardcoded в config.py (утечка в git)
- WEBHOOK_URL хардкодом в bot.py (не гибко)
- parse_mode="Markdown" используется — риск ошибок
- SQLite на Render — данные теряются при перезапуске
- Нет .gitignore
- Нет разделения на модули (всё в одном файле)
