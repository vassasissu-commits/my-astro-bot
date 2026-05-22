# Telegram Bot Master Skill — Universal Knowledge Package

> Полный набор знаний, скиллов и конфигураций для создания Telegram-ботов на Python + aiogram 3.x.
> Создан на основе опыта разработки бота «МедАссистент» (@Med24AssistantBot).

## Как использовать

1. Скопируй этот файл в `.opencode/skills/` нового проекта
2. В `opencode.json` добавь ссылку на скилл
3. Начни новую сессию — скилл загрузится автоматически

Либо просто держи этот файл в корне нового проекта и `/load` его через opencode.

---

## 1. Базовый стек технологий

| Компонент | Выбор | Почему |
|-----------|-------|--------|
| **Язык** | Python 3.12+ | Стабильность, async, экосистема |
| **Фреймворк** | aiogram 3.x | Лучшая поддержка Telegram API, FSM, middleware |
| **Сервер** | FastAPI + uvicorn | Webhook, REST API, Robokassa |
| **База** | SQLAlchemy 2.x + SQLite (dev), PostgreSQL (prod) | Асинхронно, миграции, надёжно |
| **Орм** | SQLAlchemy async | `async with async_session() as session:` |
| **Платежи** | Telegram Stars + Robokassa | Параллельные шлюзы |
| **Хостинг** | Render.com Free Tier | Бесплатно, авто-deploy из GitHub |
| **Мониторинг** | UptimeRobot | Проверка health каждые 5 мин |
| **OCR** | Tesseract (pytesseract) + OpenRouter Vision | Локально + облачный fallback |
| **LLM** | OpenRouter (DeepSeek/Claude) → Gemini fallback | Цепочка с резервом |
| **PDF** | ReportLab + FPDF | Генерация отчётов |
| **Git** | GitHub → Render auto-deploy | Push → автоматический деплой |

## 2. Структура проекта

```
project/
├── bot/
│   ├── __init__.py
│   ├── main.py           # Все хендлеры, FSM, клавиатуры
│   ├── webhook.py        # FastAPI приложение, webhook, health
│   ├── keyboards.py      # Клавиатуры (Reply + Inline)
│   └── handlers/
│       └── symptoms.py   # Хендлеры для анализа симптомов
├── core/
│   ├── __init__.py
│   ├── config.py         # pydantic-settings, .env
│   ├── database.py       # SQLAlchemy модели, CRUD
│   ├── llm_client.py     # LLM + OCR клиенты
│   ├── robokassa.py      # Robokassa интеграция
│   └── result_formatter.py # Пост-процессор результатов
├── docs/
│   └── legal/
│       ├── terms_of_service.md
│       ├── privacy_policy.md
│       └── medical_disclaimer.md
├── reports/
│   ├── __init__.py
│   └── pdf_generator.py
├── .env                  # Токены, ключи, ID
├── .gitignore
├── Dockerfile
├── requirements.txt
└── README.md
```

## 3. Конфигурация (core/config.py)

Использовать **pydantic-settings** для .env:

```python
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    bot_token: str
    admin_id: int
    openrouter_api_key: str = ""
    gemini_api_key: str = ""
    proxy_url: str = ""
    proxy_url_socks: str = ""
    log_level: str = "INFO"
    robokassa_login: str = ""
    robokassa_password1: str = ""
    robokassa_password2: str = ""
    render_external_url: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Config()
```

## 4. Webhook настройка (Render + FastAPI)

Ключевые моменты:

```python
WEBHOOK_PATH = f"/webhook/{settings.bot_token}"

# В startup:
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
if RENDER_URL:
    webhook_url = f"{RENDER_URL}{WEBHOOK_PATH}"
    await bot.set_webhook(webhook_url)
else:
    logger.warning("RENDER_URL not set — webhook будет установлен позже")
```

**ВАЖНО:** Добавить `RENDER_EXTERNAL_URL` в Render Dashboard → Environment,
иначе при каждом перезапуске вебхук слетает.

**Для UptimeRobot:** И `/health`, и `/` должны отвечать на HEAD + GET.

## 5. Telegram Bot Patterns

### 5.1. Главный хендлер /start

```python
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    extras = ""  # ❗ Всегда инициализировать ДО try
    try:
        async with get_session() as session_db:
            result = await session_db.execute(
                select(User).filter(User.telegram_id == message.from_user.id)
            )
            user = result.scalar_one_or_none()
            if not user:
                user = User(telegram_id=message.from_user.id, ...)
                session_db.add(user)
                await session_db.commit()
            else:
                await session_db.execute(
                    update(User).where(...).values(username=..., first_name=...)
                )
                await session_db.commit()
    except Exception as e:
        logger.error(f"Error: {e}")
    await message.answer(
        "👋 <b>Привет!</b>",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(),
    )
```

**Критично:** `extras = ""` строка ДО `try` — иначе UnboundLocalError!

### 5.2. FSM (Finite State Machine)

```python
from aiogram.fsm.state import State, StatesGroup

class MyFlow(StatesGroup):
    step1 = State()
    step2 = State()

@dp.message(MyFlow.step1)
async def step1_handler(message: types.Message, state: FSMContext):
    await state.update_data(key=message.text)
    await state.set_state(MyFlow.step2)
    await message.answer("Шаг 2")

@dp.callback_query(MyFlow.step2, F.data.startswith("option_"))
async def step2_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    # ...
    await state.clear()
```

**Внимание:** FSM в памяти теряется при ребуте Render free tier.
Для продакшена — Redis FSMStorage.

### 5.3. Middleware

```python
class StatsMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if hasattr(event, 'from_user') and event.from_user:
            rate_stats.record(event.from_user.id)
        return await handler(event, data)

dp.message.middleware.register(StatsMiddleware())
```

### 5.4. Callback Query Безопасность

```python
async def safe_callback_answer(callback: types.CallbackQuery):
    try:
        await callback.answer()
    except Exception:
        pass  # Telegram выкидывает ошибку при просроченном callback
```

### 5.5. Разделение на файлы

Хендлеры можно выносить, используя Router:

```python
# bot/handlers/symptoms.py
from aiogram import Router, F
router = Router()

@router.message(F.text == "🔍 Анализ симптомов")
async def handler(message: types.Message, state: FSMContext):
    ...

# В main.py:
from bot.handlers.symptoms import router as symptoms_router
dp.include_router(symptoms_router)
```

## 6. База данных (SQLAlchemy async)

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///bot.db")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    daily_requests = Column(Integer, default=0)
    last_request_date = Column(DateTime, nullable=True)
    is_premium = Column(Boolean, default=False)
    free_analyses = Column(Integer, default=0)
    lab_balance = Column(Integer, default=0)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
```

## 7. LLM + OCR

Цепочка: Tesseract (фото) → OpenRouter → Gemini fallback.

```python
import pytesseract
from PIL import Image

def ocr_tesseract(image: Image.Image) -> str:
    return pytesseract.image_to_string(image, lang='rus+eng')

async def llm_call(prompt: str, system_prompt: str) -> str:
    # 1. OpenRouter
    try:
        return await call_openrouter(prompt, system_prompt)
    except Exception:
        logger.warning("OpenRouter failed, trying Gemini")
    # 2. Gemini fallback
    try:
        return await call_gemini(prompt, system_prompt)
    except Exception:
        raise
```

**SYSTEM_PROMPT** — обязателен для каждого LLM вызова.
Пост-процессор `format_llm_result()` чистит Markdown и добавляет дисклеймер.

## 8. Платежи

### Telegram Stars

```python
# Отправка счёта
await bot.send_invoice(
    chat_id=user_id,
    title="Анализ симптомов",
    description="Информационный разбор ваших симптомов",
    payload=f"package_1",       # уникальный ID платежа
    provider_token="",          # пусто для XTR
    currency="XTR",             # Telegram Stars
    prices=[LabeledPrice(label="Анализ симптомов", amount=30)],  # цена в Stars
)

# Обязательный pre_checkout_query
@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_q: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

# Обработка successful_payment
@dp.message(F.successful_payment)
async def payment_success(message: types.Message, state: FSMContext):
    amount = message.successful_payment.total_amount  # в Stars
    # ...
```

### Robokassa

```python
# Генерация URL оплаты
def generate_payment_url(self, inv_id: str, summ: float, description: str) -> str:
    signature = hashlib.md5(
        f"{self.login}:{summ:.2f}:{inv_id}:{self.password1}".encode()
    ).hexdigest()
    return (f"https://auth.robokassa.ru/Merchant/Index.aspx?"
            f"MerchantLogin={self.login}&OutSum={summ:.2f}&InvId={inv_id}"
            f"&Description={description}&SignatureValue={signature}")

# Проверка Result URL
def verify_result(self, inv_id: str, summ: str, signature: str) -> bool:
    expected = hashlib.md5(
        f"{summ}:{inv_id}:{self.password2}".encode()
    ).hexdigest()
    return signature.lower() == expected.lower()
```

**Robokassa требует:** Публичная оферта с ценами, описанием услуг, пошаговым алгоритмом возврата, ФИО и ИНН, контактами. Возврат без вычета комиссий.

## 9. Юридические документы (Robokassa checklist)

Обязательные разделы в Публичной оферте:

1. **Общие положения** — кто, где, когда
2. **Термины** — Исполнитель, Заказчик, Услуга
3. **Предмет Договора** — что делаем
4. **Описание услуг и характеристики** — подробно
5. **Порядок заказа** — /start → выбор → данные → оплата
6. **Цены** — конкретные цифры (50₽/99₽/199₽)
7. **Оказание услуг (доставка)** — результат в чате
8. **Возврат и отказ** — пошаговый алгоритм: email → 5дней ответ → 10дней возврат → полная сумма без комиссий
9. **ФИО, ИНН, телефон, email**
10. Фраза: «возврат без удержания комиссий»

Политика конфиденциальности: ФЗ-152, категории данных, цели, сроки, контакты.

## 10. Хостинг (Render.com Free Tier)

### Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-rus && rm -rf /var/lib/apt/lists/*
COPY . .
CMD ["uvicorn", "bot.webhook:app", "--host", "0.0.0.0", "--port", "8080"]
```

Учти `fonts-dejavu-core` для PDF.

### Особенности Free Tier

- 🥶 **Cold start:** 30-50 сек при первом запросе после 15 мин бездействия
- ⏱ **UptimeRobot timeout:** ставь **60 секунд** (не 30!)
- 🧠 **FSM в памяти:** сбрасывается при spin-down
- 🗄️ **SQLite:** файлы удаляются при рестарте → нужен PostgreSQL
- 🌐 **Webhook:** `RENDER_EXTERNAL_URL` обязателен в Environment

### UptimeRobot

- Monitor Type: HTTP(s)
- URL: `https://твой-бот.onrender.com/health`
- Interval: 5 minutes
- Advanced → Request Timeout: **60 seconds**

## 11. GitHub Workflow

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/username/repo.git
git push -u origin main
```

Render: New + Web Service → Connect GitHub repo → Auto-deploy on push.

**Когда Render не деплоит после push:** проверь Build Filter в настройках Render.

## 12. Ценообразование (паттерны)

```python
# Два словаря — Stars и Рубли
STARS_PRICES = {1: 30, 2: 60, 10: 120}
RUBLE_PRICES = {1: 50, 2: 99, 10: 199}

# Выбор пакета
for count in [1, 2, 10]:
    stars = STARS_PRICES[count]
    rub = RUBLE_PRICES[count]
    text = f"{count} {pluralize(count, 'анализ', 'анализа', 'анализов')} — {rub}₽ (⭐{stars})"
```

## 13. Частые баги и их решения

| Баг | Причина | Решение |
|-----|---------|---------|
| `Can't parse entities` | Markdown + `_` `*` в тексте | Перейти на `parse_mode="HTML"` |
| `UnboundLocalError` | Переменная не инициализирована до `try` | Всегда `var = ""` до блока try |
| `405 Method Not Allowed` | HEAD без GET | `@app.get / @app.head` для одного эндпоинта |
| Webhook не работает | RENDER_EXTERNAL_URL не задан | Добавить в Environment на Render |
| SQLite сброшен | Render удаляет файлы при рестарте | Перейти на PostgreSQL |
| 404 на webhook | Неправильный токен в пути | Проверить encoded `:` в URL |
| Bot не отвечает | Container спит + UptimeRobot 30s timeout | Поставить 60s timeout |
| FSM потерян | Render spin-down | Использовать Redis FSMStorage |
| Stars не работают | Нет pre_checkout_query хендлера | Обязательно `@dp.pre_checkout_query()` |
| `executing functools.partial` | DEBUG логи aiosqlite | `echo=False` в engine |

## 14. Маркетинг Telegram-ботов

- **Deep Link:** `https://t.me/bot?start=ref_CODE` — реферальная система
- **Share text:** Результаты с хештегами и ссылкой на бота
- **Кнопка "Поделиться":** `switch_inline_query` для шаринга в другие чаты
- **Цены:** Показывать экономию на пакетах (50₽ × 10 = 500₽, пакет 199₽)
- **Акции:** Бесплатные запросы за шаринг, за реферала
- **Юридические документы:** Кнопка внизу главного меню (не навязчиво, но доступно)

## 15. Переменные окружения (.env)

```env
BOT_TOKEN=123456:ABC...
ADMIN_ID=123456789
OPENROUTER_API_KEY=sk-or-...
GEMINI_API_KEY=AIza...
ROBOKASSA_LOGIN=shop_login
ROBOKASSA_PASSWORD1=password1
ROBOKASSA_PASSWORD2=password2
RENDER_EXTERNAL_URL=https://myapp.onrender.com
LOG_LEVEL=INFO
```

---

## Быстрый старт в новом проекте

1. Создать папку проекта
2. `pip install aiogram fastapi uvicorn sqlalchemy aiosqlite pydantic-settings python-dotenv aiohttp`
3. Скопировать структуру из раздела 2
4. Создать `.env` с BOT_TOKEN и ADMIN_ID
5. Написать `bot/main.py` с `/start` хендлером
6. Написать `bot/webhook.py` с FastAPI + `/health`
7. Создать Dockerfile
8. Push в GitHub
9. Настроить Render: Web Service + Environment
10. Настроить UptimeRobot с таймаутом 60 сек

> Этот файл — твой клон меня. Открой новую сессию opencode в любом проекте,
> дай мне путь к этому файлу, и я восстановлю все свои знания и скиллы.
