# 🤖 ПРОМПТЫ ДЛЯ AI-ФАБРИКИ (Готово к использованию)

Все промпты заточены под стиль @goroskop.maria: живая речь, простота, энергия, без "Веданы".

---

## 1. 📝 AI-СЦЕНАРИСТ (Groq API)
**Модель**: `llama-3.1-8b-instant`
**Системный промпт**:
```
Ты — астролог Мария. Твоя задача: написать живой, энергичный скрипт гороскопа для [ЗНАК] на сегодня.
Стиль: дружелюбно, как будто говоришь с другом в камеру.
Структура:
1. Приветствие: "[ЗНАК], привет! 👋"
2. Крючок (3 сек): "Сегодня звезды обещают [ИНТРИГА]..."
3. Основной прогноз (15-20 сек): Энергия дня, любовь, карьера. Пиши просто, без сложных терминов.
4. CTA: "Больше предсказаний в ссылке в био! 👇"

Пиши только текст для озвучки. Никаких ссылок в тексте!
Длина: 40-60 слов.
```

**Пользовательский промпт (пример для Овна)**:
```
Напиши гороскоп для Овна на 06.05.2026.
Тема дня: "Мощный старт нового проекта".
Тон: Энергичный, мотивирующий.
```

**Groq API вызов (Python)**:
```python
import groq

client = groq.Groq(api_key="YOUR_GROQ_KEY")

response = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[
        {"role": "system", "content": "Ты астролог Мария. [СИСТЕМНЫЙ ПРОМПТ]"},
        {"role": "user", "content": "Напиши гороскоп для Овна на сегодня. Тема: Мощный старт."}
    ],
    max_tokens=150,
    temperature=0.7
)
script = response.choices[0].message.content
print(script)
```

---

## 2. 🖼 AI-КАРТИНКИ (Stable Diffusion 3.5)
**Инструмент**: `sd35.app` или `stablediffusion.com`
**Промпт для аватара (человек как Мария)**:
```
Realistic woman, 30 years old, friendly astrologer, smiling, sitting at wooden desk with tarot cards and crystals, soft warm lighting, cozy room background, high quality, 4k, photorealistic, looking at camera
```

**Промпт для фона (гороскоп)**:
```
Astrology theme background, starry night sky, zodiac wheel, purple and dark blue gradient, mystical atmosphere, cinematic lighting, 9:16 aspect ratio, high quality
```

**Промпт для обложки (Овен)**:
```
Aries zodiac sign ♈, red and orange gradient background, bold text "ОВЕН: Твой прогноз", modern style, high contrast, 9:16 ratio, professional thumbnail
```

**Как использовать**:
1. Зайти на `https://sd35.app/`
2. Вставить промпт
3. Выбрать размер: `576x1024` (для вертикального видео)
4. Скачать картинку

---

## 3. 🎬 AI-ВИДЕО (Stable Video Diffusion)
**Инструмент**: `https://stable-diffusion-web.com/sd-video`
**Вход**: Картинка от Stable Diffusion (аватар Марии)
**Промпт для анимации**:
```
Woman talking, natural head movement, slight smile, blinking eyes, realistic lip sync, 25 frames, smooth motion
```

**Настройки**:
- Frames: `25` (около 2-3 секунд)
- FPS: `10-12`
- Motion bucket: `127`

**Как использовать**:
1. Зайти на `stable-diffusion-web.com/sd-video`
2. Upload картинку (аватар)
3. Вставить промпт анимации
4. Generate → Скачать MP4

---

## 4. 🔊 AI-ОЗВУЧКА (ElevenLabs)
**Инструмент**: `elevenlabs.io` (Free: 10k символов/мес)
**Голос**: `Bella` (русский акцент, женский, энергичный)
**Текст для озвучки (результат Groq)**:
```
Овны, привет! 👋 Сегодня звезды обещают мощный старт нового проекта. 
Твоя энергия на максимуме, действуй смело! 
В любви — сюрприз, в карьере — рост. 
Больше предсказаний в ссылке в био! 👇
```

**Настройки голоса**:
- Stability: `50%`
- Style Exaggeration: `0%`
- Speed: `1.0`

**Как использовать**:
1. Зайти на `elevenlabs.io`
2. Выбрать голос `Bella`
3. Вставить текст
4. Generate → Скачать MP3

---

## 5. ✂️ AI-МОНТАЖ (CapCut — Автоматизация)
**Инструмент**: CapCut (ПК версия)
**Структура готового видео (15-20 сек)**:
```
[00:00-00:03] Картинка (Аватар) + Текст: "Овны, сегодня..."
[00:03-00:15] Видео (Анимированный аватар) + Озвучка (Groq + ElevenLabs)
[00:15-00:18] Текст: "✨ Твой прогноз ждет в ссылке"
[00:18-00:20] Стрелка вниз 👇 + Музыка YouTube Audio
```

**Бесплатная музыка (YouTube Audio Library)**:
- Название: "Upbeat Inspiration" или "Mystical Morning"
- Автор: Для коммерческого использования

**Автоматизация в CapCut**:
1. Загрузить видео (Stable Video Diffusion)
2. Загрузить звук (ElevenLabs MP3)
3. Добавить субтитры (авто-распознавание)
4. Добавить обложку (Stable Diffusion)
5. Экспорт: 1080x1920, 30fps

---

## 🔄 ОБЩИЙ WORKFLOW (Автоматизация)

### Python скрипт (пример):
```python
# 1. Groq генерирует скрипт
script = groq_generate("Овен", "Мощный старт")

# 2. Stable Diffusion генерирует картинку
image = sd_generate("Realistic woman, smiling, 4k")

# 3. Stable Video Diffusion делает видео из картинки
video = svd_generate(image, script)

# 4. ElevenLabs озвучивает скрипт
audio = elevenlabs_tts(script, voice="Bella")

# 5. CapCut собирает всё вместе (ручной монтаж или FFmpeg)
final_video = merge_audio_video(video, audio)
```

---

## 📋 ЧЕК-ЛИСТ ДЛЯ МЕНЕДЖЕРА (Trello)
| Задача | Статус | Инструмент |
|---------|--------|-----------|
| Скрипт для Овна (Groq) | ⏳️ В процессе | `llama-3.1-8b` |
| Картинка аватара (SD) | ⏳️ В процессе | `sd35.app` |
| Видео анимация (SVD) | ⏳️ В процессе | `stable-diffusion-web.com` |
| Озвучка (ElevenLabs) | ⏳️ В процессе | `elevenlabs.io` |
| Монтаж (CapCut) | ⏳️ В процессе | `capcut.com` |
| Проверка безопасности (TikTok) | ⏳️ В процессе | `TikTok Specialist` |
| Upload на TikTok | ⏳️ В процессе | `@aries_horoscope` |

---

## ⚠️ КРИТИЧЕСКИЕ ПРАВИЛА
1. **НЕТ "Веданы"** в промптах! Только "астролог Мария" или "твой гороскоп".
2. **НЕТ ссылок** в скриптах для озвучки!
3. **Уникальные `start_param`** для каждого знака:
   - Овен: `?start=tiktok_aries1`
   - Телец: `?start=tiktok_taurus1`
4. **Безопасность**: TikTok Specialist проверяет каждое видео перед публикацией.

---

**СТАТУС**: Промпты готовы! Можно запускать фабрику.
**СЛЕДУЮЩИЙ ШАГ**: Заполняем `AI_VIDEO_FACTORY.md` с детальным планом реализации.
