# ИНСТРУКЦИЯ: Как создать видео для Овна (30 сек)

## 1. СЦЕНАРИЙ (в файле aris_30s.json)
- ХУК (0:00-0:03): "Овны, остановитесь! Плутон заблокировал вашу удачу..."
- ОСНОВНАЯ ЧАСТЬ: Марс, оппозиция, угроза потери шанса
- ТРИГГЕР: 97% уже узнали, время ограничено
- CTA: Ссылка на бота с параметром `?start=tiktok_aries1`

## 2. ГЕНЕРАЦИЯ ВИДЕО-КЛИПОВ (5-10 сек каждый)

### Бесплатные API (выбери 1-2):
1. **Luma Dream Machine** (30 видео/мес, 5 сек) → https://lumalabs.ai
   - Промпт: "Dramatic fire explosion, ram symbol burning, dark cosmic background"
   - Скачай видео → `videos/aries/clip1.mp4`

2. **Pika Labs** (ежедневно, 4 сек) → https://pika.art
   - Промпт: "Mars planet animation, zodiac wheel spinning"
   - Скачай → `videos/aries/clip2.mp4`

3. **Haiper** (щедрый лимит) → https://haiper.ai
   - Промпт: "Clock ticking fast, stars aligning, mysterious fog"

4. **Kling AI** (66 кредитов) → https://klingai.com
   - Промпт: "Bot logo appearing, arrow pointing to link"

## 3. ОЗВУЧКА
### Вариант А: ElevenLabs (платный, топ качество)
- Залей текст из сценария
- Выбери русский голос (Dmitry/Anna)
- Скачай аудио → `audio/aries/aries_30s.mp3`

### Вариант Б: Светлана (бесплатно, пока)
```powershell
python tts_batch.py aries "Овны, остановитесь! Плутон заблокировал вашу удачу..."
```

## 4. МОНТАЖ (CapCut / DaVinci Resolve)
1. Загрузи клипы в порядке сценария
2. Добавь озвучку
3. Добавь текст (субтитры)
4. Экспорт: 1080x1920 (вертикальное видео), 30 сек

## 5. ЗАГРУЗКА
- TikTok: @aries_horoscope
- YouTube Shorts: загрузи с описанием и ссылкой
- Ссылка в описании: `https://t.me/SuperAstro2027_bot?start=tiktok_aries1`

## СТРУКТУРА ПАПОК
```
videos/aries/
  ├── clip1.mp4 (огонь, Овен)
  ├── clip2.mp4 (Марс, планеты)
  ├── clip3.mp4 (часы, звезды)
  └── clip4.mp4 (бот, ссылка)
audio/aries/
  └── aries_30s.mp3
scripts/
  └── aries_30s.json
```

## СЛЕДУЮЩИЕ ШАГИ
1. Зарегайся на Luma/Pika/Kling (бесплатно)
2. Сгенерируй 4 клипа по описанию из сценария
3. Озвучь через Elevenlabs или Светлану
4. Смонтируй в CapCut (бесплатно)
5. Загрузи первое тестовое видео
