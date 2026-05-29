# 🤖 ГОТОВАЯ AI-ФАБРИКА (ПОЛНЫЙ КОМПЛЕКТ)

Все промпты готовы к использованию. ТОЛЬКО бесплатные инструменты.

---

## 📝 1. AI-СЦЕНАРИСТ (Groq API)
**Модель**: `llama-3.1-8b-instant`
**Системный промпт** (сохранить в переменную `SYSTEM_PROMPT`):
```
Ты — астролог Мария. Твоя задача: написать живой, энергичный скрипт гороскопа для [ЗНАК] на сегодня.
Стиль: дружелюбно, как будто говоришь с другом в камеру.
Структура:
1. Приветствие: "[ЗНАК], привет! 👋"
2. Крючок (3 сек): "[ИНТРИГА: событие дня]..."
3. Основной прогноз (15-20 сек): Энергия, Любовь, Карьера. Пиши просто, без сложных терминов.
4. CTA: "Больше предсказаний в ссылке в био! 👇"

Пиши только текст для озвучки. Никаких ссылок в тексте! Никаких "Ведана"! Только "[ЗНАК], [СОБЫТИЕ]".
Длина: 40-60 слов.
```

**Пользовательский промпт** (меняем [ЗНАК] и [ДАТА]):
```
Напиши гороскоп для [ЗНАК] на [ДАТА].
Тема дня: [ТЕМА: например, "Мощный старт", "Тайное свидание", "Финансовый успех"].
Тон: Энергичный, мотивирующий.
```

**Пример вызова (Python)**:
```python
import groq

client = groq.Groq(api_key="YOUR_GROQ_KEY")

def generate_script(sign, date, theme):
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.replace("[ЗНАК]", sign)},
            {"role": "user", "content": f"Напиши гороскоп для {sign} на {date}. Тема: {theme}. Тон: Энергичный."}
        ],
        max_tokens=150,
        temperature=0.7
    )
    return response.choices[0].message.content

# Тест для Овна
script = generate_script("Овен ♈", "06.05.2026", "Мощный старт проекта")
print(script)
```

---

## 🖼️ 2. AI-КАРТИНКИ (Stable Diffusion 3.5)
**Инструмент**: `https://sd35.app/` (бесплатно, без регистрации)

### А. Аватар (подставляем знак):
```
Realistic woman, 30 years old, friendly astrologer, smiling, sitting at wooden desk with tarot cards and crystals, soft warm lighting, cozy room background, high quality, 4k, photorealistic, looking at camera
```

### Б. Фон (подставляем знак):
```
Astrology theme background, starry night sky, [ЗНАК] zodiac wheel, purple and dark blue gradient, mystical atmosphere, cinematic lighting, 9:16 aspect ratio, high quality
```

### В. Обложка (подставляем знак):
```
[ЗНАК] zodiac sign ♈, red and orange gradient background, bold text "[ЗНАК]: твой прогноз", modern style, high contrast, 9:16 ratio, professional thumbnail, no text watermark
```

**Как использовать**:
1. Зайти на `https://sd35.app/`
2. Вставить промпт
3. Выбрать размер: `576x1024` (для 9:16)
4. Generate → Скачать JPG/PNG

---

## 🎬 3. AI-ВИДЕО (Stable Video Diffusion)
**Инструмент**: `https://stable-diffusion-web.com/sd-video` (бесплатно)

**Промпт для анимации аватара** (берем картинку от Stable Diffusion):
```
Woman talking, natural head movement, slight smile, blinking eyes, realistic lip sync, 25 frames, smooth motion, 576x1024, 10 fps
```

**Настройки**:
- Frames: `25` (около 2-3 секунд)
- FPS: `10`
- Motion bucket: `127`

**Как использовать**:
1. Upload картинку (аватар от Stable Diffusion)
2. Вставить промпт анимации
3. Generate → Скачать MP4

---

## 🔊 4. AI-ОЗВУЧКА (ElevenLabs Free)
**Инструмент**: `https://elevenlabs.io/` (10k символов/мес, бесплатно)
**Голос**: `Bella` (русский акцент, женский, энергичный)

**Настройки**:
- Stability: `50%`
- Style Exaggeration: `0%`
- Speed: `1.0`

**Текст для озвучки** (результат от Groq):
```
Овны, привет! 👋 Сегодня звезды обещают мощный старт нового проекта. 
Твоя энергия на максимуме, действуй смело! 
В любви — сюрприз, в карьере — рост. 
Больше предсказаний в ссылке в био! 👇
```

**Как использовать**:
1. Зайти на `elevenlabs.io`
2. Выбрать голос `Bella`
3. Вставить текст
4. Generate → Скачать MP3

---

## ✂️ 5. AI-МОНТАЖ (CapCut Free)
**Инструмент**: CapCut (ПК версия, бесплатно)

### Структура готового видео (15-20 сек):
| Время | Слой | Содержание |
|-------|------|-------------|
| 00:00-00:03 | Видео (SVD) + Субтитры | "[КРЮЧОК: Овны, сегодня...]" |
| 00:03-00:15 | Видео (SVD) + Озвучка (ElevenLabs) | "[ОСНОВНОЙ ПРОГНОЗ]" |
| 00:15-00:18 | Статичная картинка (SD) + Текст | "✨ Твой прогноз ждет в ссылке" |
| 00:18-00:20 | Обложка + Стрелка 👇 | "Ссылка в био!" |

### Бесплатная музыка:
- YouTube Audio Library → "Upbeat Inspiration" или "Mystical Morning"
- Скачать MP3 → Импорт в CapCut

**Автоматизация**:
- CapCut поддерживает пакетную обработку (batch processing) — можно за один раз смонтировать 12 видео по шаблону.

---

## 📋 6. TikTok Specialist (ЧЕК-ЛИСТ)
**Перед публикацией проверяй каждое видео**:

| Пункт | Что проверяем | Статус |
|-------|-------------|--------|
| 1 | В тексте видео НЕТ `@SuperAstro2027_bot` | [ ] |
| 2 | В тексте видео НЕТ `t.me`, `http` | [ ] |
| 3 | В тексте видео НЕТ "Ведана", "Vedana" | [ ] |
| 4 | В описании (Bio) есть "Ссылка в био 👇" | [ ] |
| 5 | Website URL заполнен: `https://t.me/SuperAstro2027_bot?start=tiktok_[ЗНАК]1` | [ ] |
| 6 | Аватарка: БЕЗ текста, только эмодзи знака | [ ] |

---

## 🔗 7. ССЫЛКИ ДЛЯ ТРАФИКА (Уникальные `start_param`)

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

## 🚀 8. ОПИСАНИЕ ПРОФИЛЯ (Bio — 1 строка)

| Вариант | Текст для вставки |
|---------|--------------------------|
| **А (Рекомендуемый)** | `✨ Твой прогноз на каждый день 👇` |
| **Б** | `🔮 Гороскоп для [ЗНАК]. Подпишись 👇` |
| **В** | `✨ Энергия, страсть, драйв. Ссылка в профиле!` |

⚠️ **ГЛАВНОЕ**: В тексте НЕТ `@SuperAstro2027_bot`! НЕТ `t.me`! НЕТ "Ведана"!

---

## 🏭 9. УПРАВЛЕНИЕ (Trello Free)

**Создать доску**: "AI Factory - [ДАТА]"
**Колонки**:
1. 📝 Скрипты (Groq) — 24 задачи
2. 🖼️ Картинки (Stable Diffusion) — 24 задачи
3. 🎬 Видео (Stable Video Diffusion) — 24 задачи
4. 🔊 Озвучка (ElevenLabs) — 24 задачи
5. ✂️ Монтаж (CapCut) — 24 задачи
6. ✅ Готово к публикации

**Бесплатно**: 10 досок, неограниченные карточки.

---

## 📊 ИТОГОВЫЙ СТАТУС

✅ **ФАБРИКА ГОТОВА К ЗАПУСКУ!**
- Промпты для Groq (системный + пользовательский) ✅
- Промпты для Stable Diffusion (аватар, фон, обложка) ✅
- Промпты для Stable Video Diffusion (анимация) ✅
- Настройки ElevenLabs (голос, настройки) ✅
- Шаблон монтажа CapCut ✅
- Чек-лист TikTok Specialist ✅
- 12 уникальных ссылок `start_param` ✅

**ЧТО ДЕЛАТЬ СЕЙЧАС**:
1. Скопировать промпты из раздела 1 и протестировать на Groq.
2. Скопировать промпты из раздела 2 и сгенерировать первую картинку на sd35.app.
3. Скопировать промпты из раздела 3 и создать первое видео.
4. Скопировать текст из раздела 4 и озвучить в ElevenLabs.
5. Собрать всё в CapCut.

**ВСЕ НА РУССКОМ! НИКАКОЙ "ВЕДАНЫ"! ТОЛЬКО ЗНАКИ ЗОДИАКА!**
