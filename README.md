# @SuperAstro2027_bot — Астрология + Таро

**Бот**: @SuperAstro2027_bot  
**GitHub**: https://github.com/vassasissu-commits/my-astro-bot  
**Render**: https://my-astro-bot-wqwl.onrender.com  
**Webhook**: https://my-astro-bot-wqwl.onrender.com/webhook

---

## Как запустить локально

1. Создай виртуальное окружение:
```
python -m venv venv
venv\Scripts\activate
```
2. Установи зависимости:
```
pip install -r requirements.txt
```
3. Убедись, что в `.env` есть токен (смотри CREDENTIALS.md):
```
BOT_TOKEN = "твой_токен"
```
4. Запусти:
```
python bot.py
```

## Как деплоить на Render

При пуше в GitHub Render автоматически пересобирается.
Если надо добавить переменные окружения вручную:
- Зайди в https://dashboard.render.com → сервис `my-astro-bot`
- Settings → Environment → добавить:
  - `BOT_TOKEN` = смотри CREDENTIALS.md
  - `GROQ_API_KEY` = смотри CREDENTIALS.md
  - `PORT` = `8080` (автоматически)

## Webhook

Если бот перестал отвечать — проверь webhook:
```
curl "https://api.telegram.org/bot$(grep BOT_TOKEN CREDENTIALS.md | head -1 | cut -d':' -f2-)/getWebhookInfo"
```
Если url пустой — переустанови (токен из CREDENTIALS.md):
```
curl "https://api.telegram.org/botТОКЕН/setWebhook?url=https://my-astro-bot-wqwl.onrender.com/webhook"
```

## Структура проекта

- `bot.py` — главный файл бота (aiogram 3.x + aiohttp webhook)
- `config.py` — API-ключи и настройки
- `astro.db` — SQLite база пользователей
- `scripts/` — скрипты-помощники
- `images/`, `audio/`, `videos/` — медиа для контента

## Важно

- Бот работает через **webhook** на Render (не polling)
- При локальном запуске через `python bot.py` — запускается polling
- Все токены и ключи — в CREDENTIALS.md (не пушить на GitHub)
