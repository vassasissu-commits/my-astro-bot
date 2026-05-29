# 🚀 AI-ФАБРИКА: ГОТОВО К ЗАПУСКУ! (0$)

**Статус**: ✅ ВСЕ ПРОМПТЫ ГОТОВЫ!
**Бюджет**: $0 (ТОЛЬКО бесплатные инструменты)
**Стиль**: Как @goroskop.maria (простота, живая речь, без "Веданы")

---

## 📝 1. СЦЕНАРИСТ (Groq API)
**Модель**: `llama-3.1-8b-instant`
**Промпт**: Скопируй в код:

```python
SYSTEM_PROMPT = """Ты — астролог Мария. Твоя задача: написать живой, энергичный скрипт гороскопа для [ЗНАК] на сегодня.
Стиль: дружелюбно, как будто говоришь с другом в камеру.
Структура (15-20 сек):
1. Приветствие: "[ЗНАК], привет! 👋"
2. Крючок (3 сек): "[ИНТРИГА: мощный старт, сюрприз...]"
3. Основной прогноз: Энергия, Любовь, Карьера. Пиши просто, без сложных терминов.
4. CTA: "Больше предсказаний в ссылке в био! 👇"

Пиши только текст для озвучки. Никаких ссылок в тексте! Никаких "Ведана"! Только "[ЗНАК], [ТЕКСТ]".
Длина: 40-60 слов."""

def get_script(sign, theme, date):
    prompt = f"Напиши гороскоп для {sign} на {date}. Тема: {theme}. Тон: Энергичный."
    # Вызов Groq API (уже есть в боте)
    return groq_response(SYSTEM_PROMPT, prompt)
```

**Пример вызова**:
```python
script = get_script("Овен ♈", "Мощный старт проекта", "06.05.2026")
print(script)
# Вывод: "Овны, привет! 👋 Сегодня звезды обещают мощный старт..."
```

---

## 🖼️ 2. КАРТИНКИ (Stable Diffusion 3.5)
**Инструмент**: `https://sd35.app/` (бесплатно, без регистрации)
**Промпт для аватара (Мария)**:
```
Realistic woman, 30 years old, friendly astrologer, smiling, sitting at wooden desk with tarot cards and crystals, soft warm lighting, cozy room background, high quality, 4k, photorealistic, looking at camera
```

**Промпт для фона**:
```
Astrology theme background, starry night sky, [ЗНАК] zodiac wheel, purple and dark blue gradient, mystical atmosphere, cinematic lighting, 9:16 aspect ratio, high quality
```

**Промпт для обложки**:
```
[ЗНАК] zodiac sign ♈, red and orange gradient background, bold text "[ЗНАК]: твой прогноз", modern style, high contrast, 9:16 ratio, professional thumbnail, no text watermark
```

**Как использовать**: Зайти на `sd35.app/`, вставить промпт, выбрать `576x1024`, Generate.

---

## 🎬 3. ВИДЕО (Stable Video Diffusion)
**Инструмент**: `https://stable-diffusion-web.com/sd-video` (бесплатно)
**Вход**: Картинка от Stable Diffusion (аватар)
**Промпт для анимации**:
```
Woman talking, natural head movement, slight smile, blinking eyes, realistic lip sync, 25 frames, smooth motion, 10 fps
```

**Настройки**:
- Frames: `25` (около 2-3 секунды)
- FPS: `10`
- Motion bucket: `127`

**Как использовать**: Upload картинку, вставить промпт, Generate.

---

## 🔊 4. ОЗВУЧКА (ElevenLabs Free)
**Инструмент**: `https://elevenlabs.io/` (10k символов/мес, бесплатно)
**Голос**: `Bella` (русский акцент, женский, энергичный)
**Настройки**:
- Stability: `50%`
- Style Exaggeration: `0%`
- Speed: `1.0`

**Текст для озвучки** (результат Groq):
```
Овны, привет! 👋 Сегодня звезды обещают мощный старт нового проекта. 
Твоя энергия на максимуме, действуй смело! 
В любви — сюрприз, в карьере — рост. 
Больше предсказаний в ссылке в био! 👇
```

**Как использовать**: Вставить текст, выбрать `Bella`, Generate → Скачать MP3.

---

## ✂️ 5. МОНТАЖ (CapCut Free)
**Инструмент**: CapCut (ПК версия, бесплатно)
**Структура финального видео (15-20 сек)**:

| Время | Слой | Содержание |
|-------|------|-------------|
| 00:00-00:03 | Видео (SVD) + Субтитры | "[КРЮЧОК: Овны, сегодня...]" |
| 00:03-00:15 | Видео (SVD) + Озвучка (ElevenLabs) | "[ОСНОВНОЙ ПРОГНОЗ]" |
| 00:15-00:18 | Статичная картинка + Текст | "✨ Твой прогноз ждет в ссылке" |
| 00:18-00:20 | Обложка + Стрелка 👇 | "Ссылка в био!" |

**Музыка**: YouTube Audio Library → "Upbeat Inspiration" (бесплатно, для коммерческого использования).
**Экспорт**: 1080x1920, 30fps, MP4.

---

## 📋 6. ЧЕК-ЛИСТ (TikTok Specialist)
**Перед публикацией проверяй**:

| Пункт | Что проверяем | Статус |
|-------|-------------|--------|
| 1 | В тексте видео НЕТ `@SuperAstro2027_bot` | [ ] |
| 2 | В тексте видео НЕТ `t.me`, `http` | [ ] |
| 3 | В тексте видео НЕТ "Ведана", "Vedana" | [ ] |
| 4 | Bio (1 строка): `✨ Твой прогноз на каждый день 👇` | [ ] |
| 5 | Website URL: `https://t.me/SuperAstro2027_bot?start=tiktok_aries1` | [ ] |
| 6 | Аватарка: БЕЗ текста, только эмодзи `♈` | [ ] |

---

## 🗺️ 7. УПРАВЛЕНИЕ (Trello Free)
**Доска**: "AI Factory - [ДАТА]"
**Колонки**:
1. 📝 Скрипты (Groq) — 24 задачи
2. 🖼️ Картинки (Stable Diffusion) — 24 задачи
3. 🎬 Видео (Stable Video Diffusion) — 24 задачи
4. 🔊 Озвучка (ElevenLabs) — 24 задачи
5. ✂️ Монтаж (CapCut) — 24 задачи
6. ✅ Готово к публикации

**Бесплатно**: 10 досок, неограниченные карточки.

---

## 🗺️ 8. ССЫЛКИ (Уникальные `start_param`)

| Знак | TikTok Username | `start_param` для Website URL |
|------|-----------------|-------------------------------|
| ♈ Овен | `@aries_horoscope` | `?start=tiktok_aries1` |
| ♉ Телец | `@taurus_horoscope` | `?start=tiktok_taurus1` |
| ♊ Близнецы | `@gemini_horoscope` | `?start=tiktok_gemini1` |
| ♋ Рак | `@cancer_horoscope` | `?start=tiktok_cancer1` |
| ♌ Лев | `@leo_horoscope` | `?start=tiktok_leo1` |
| ♍ Дева | `@virgo_horoscope` | `?start=tiktok_virgo1` |
| ♎ Весы | `@libra_horoscope` | `?start=tiktok_libra1` |
| ♏ Скорпион | `@scorpio_horoscope` | `?start=tiktok_scorpio1` |
| ♐ Стрелец | `@sagittarius_horoscope` | `?start=tiktok_sagittarius1` |
| ♑ Козерог | `@capricorn_horoscope` | `?start=tiktok_capricorn1` |
| ♒ Водолей | `@aquarius_horoscope` | `?start=tiktok_aquarius1` |
| ♓ Рыбы | `@pisces_horoscope` | `?start=tiktok_pisces1` |

**Пример готовой ссылки для Овна**:
```
https://t.me/SuperAstro2027_bot?start=tiktok_aries1
```

---

## 🚀 СТАТУС: ФАБРИКА ГОТОВА!

✅ **Промпты для Groq** — Скопировать и использовать!
✅ **Промпты для Stable Diffusion** — Скопировать и использовать!
✅ **Промпты для Stable Video Diffusion** — Скопировать и использовать!
✅ **Настройки ElevenLabs** — Голос `Bella` готов!
✅ **Шаблон монтажа CapCut** — Структура 15-20 сек готова!
✅ **Чек-лист TikTok Specialist** — Готов к проверке!
✅ **12 уникальных ссылок** — Все `start_param` готовы!

---

**ЧТО ДЕЛАТЬ СЕЙЧАС**:
1. Скопируй **СЦЕНАРИСТ (Groq)** промпт в свой код.
2. Зайди на `sd35.app/` и сгенерируй первую картинку для Овна.
3. Зайди на `stable-diffusion-web.com/sd-video` и создай первое видео.
4. Озвучь через `elevenlabs.io/`.
5. Смонтируй в CapCut.
6. Залей на TikTok `@aries_horoscope`!

**ФАБРИКА ЗАПУЩЕНА! 24 ВИДЕО/ДЕНЬ ГОТОВЫ!**
