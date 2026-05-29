import json
import os

# === UNIQUE TEMPLATES FOR EACH ZODIAC SIGN ===
# Each sign has its own unique selling style, triggers, and personality

SIGN_SCRIPTS = {
    "aries": {
        "name_ru": "Овен",
        "style": "дерзкий, энергичный, прямой",
        "color": "красный",
        "clips": [
            {
                "text": "Овны, стойте! Марс блокирует вашу главную цель на сегодня...",
                "video": "fire explosion, ram symbol burning, intense red flames"
            },
            {
                "text": "Эта энергия может разрушить ваши планы, если не узнаете подробности...",
                "video": "Mars planet close up, fast movement, dramatic shadows"
            },
            {
                "text": "Только 24 часа, чтобы изменить ход событий. 89% Овнов уже знают...",
                "video": "clock ticking fast, red lightning, urgent atmosphere"
            },
            {
                "text": "Ваша агрессия сегодня — это ваш враг номер один...",
                "video": "ram head statue, cracks appearing, dramatic light"
            },
            {
                "text": "Секретный прогноз Марса для Овнов: t.me/SuperAstro2027_bot?start=tiktok_aries1",
                "video": "bot logo glowing red, arrow pointing, fire particles"
            }
        ]
    },
    
    "taurus": {
        "name_ru": "Телец",
        "style": "чувственный, материальный, спокойный",
        "color": "зеленый",
        "clips": [
            {
                "text": "Тельцы, ваша финансовая удача под угрозой прямо сейчас...",
                "video": "green meadow, bull statue, golden coins falling"
            },
            {
                "text": "Венера шепчет: ваше богатство зависит от одного решения сегодня...",
                "video": "scales with money, Venus symbol, soft green glow"
            },
            {
                "text": "Пропустите этот знак — и потеряете шанс на прибыль в этом месяце...",
                "video": "bank notes flying, Taurus constellation, luxury items"
            },
            {
                "text": "97% Тельцов уже забрали свой финансовый прогноз. Вы следующий?",
                "video": "closed safe opening slowly, golden light spilling out"
            },
            {
                "text": "Узнайте, где спрятаны ваши деньги: t.me/SuperAstro2027_bot?start=tiktok_taurus1",
                "video": "bot logo with dollar sign, green sparks, arrow down"
            }
        ]
    },
    
    "gemini": {
        "name_ru": "Близнецы",
        "style": "общительный, любопытный, двойственный",
        "color": "синий",
        "clips": [
            {
                "text": "Близнецы, вам лгут! Узнайте, кто скрывает правду от вас...",
                "video": "twin shadows, blue mist, mysterious figures talking"
            },
            {
                "text": "Меркурий раскрывает тайну вашего окружения. Это шокирует...",
                "video": "Mercury planet spinning, chat messages appearing, blue digital rain"
            },
            {
                "text": "Ваша интуиция кричит, но разум не слышит. Послушайте знаки...",
                "video": "two faces mirror, whispering mouths, blue neon signs"
            },
            {
                "text": "Двойственность разрушает ваши связи. Узнайте, как спасти их...",
                "video": "broken mirror reflection, Gemini symbol, blue electricity"
            },
            {
                "text": "Тайна, которую скрывают от Близнецов: t.me/SuperAstro2027_bot?start=tiktok_gemini1",
                "video": "bot logo with question mark, blue chat bubbles, arrow"
            }
        ]
    },
    
    "cancer": {
        "name_ru": "Рак",
        "style": "эмоциональный, защищающий, семейный",
        "color": "серебряный",
        "clips": [
            {
                "text": "Раки, ваша семья под защитой, но надолго ли? Луна предупреждает...",
                "video": "moon over ocean, crab shell glowing, silver waves"
            },
            {
                "text": "Эмоциональный шторм сегодня разрушит ваш внутренний покой...",
                "video": "stormy sea, crying eyes reflection, silver rain drops"
            },
            {
                "text": "Ваша интуиция видит то, что скрыто от других. Не игнорируйте знаки...",
                "video": "crystal ball glowing, Cancer constellation, silver mist"
            },
            {
                "text": "Близкие скрывают правду. Узнайте, что происходит за вашей спиной...",
                "video": "family photo burning at edges, shadow figures, silver light"
            },
            {
                "text": "Лунный прогноз для Раков, который изменит всё: t.me/SuperAstro2027_bot?start=tiktok_cancer1",
                "video": "bot logo with moon crescent, silver sparkles, arrow up"
            }
        ]
    },
    
    "leo": {
        "name_ru": "Лев",
        "style": "гордый, лидерский, драматичный",
        "color": "золотой",
        "clips": [
            {
                "text": "Львы, ваша корона под угрозой! Кто посмеет бросить вам вызов?",
                "video": "golden crown glowing, lion roaring, golden flames"
            },
            {
                "text": "Солнце предупреждает: ваша слава может померкнуть уже сегодня...",
                "video": "solar eclipse, Leo constellation, golden dust falling"
            },
            {
                "text": "Лидерство требует жертв. Готовы ли вы заплатить эту цену?",
                "video": "lion on throne, golden scales tipping, dramatic lighting"
            },
            {
                "text": "Только истинные Львы смогут пройти это испытание. Вы один из них?",
                "video": "golden mane flowing, Leo symbol glowing, golden sparks"
            },
            {
                "text": "Ваше королевское пророчество здесь: t.me/SuperAstro2027_bot?start=tiktok_leo1",
                "video": "bot logo with crown, golden rays, arrow pointing"
            }
        ]
    },
    
    "virgo": {
        "name_ru": "Дева",
        "style": "точный, аналитичный, заботливый",
        "color": "изумрудный",
        "clips": [
            {
                "text": "Девы, вы упустили важную деталь в своем здоровье. Ошибка может стоить дорого...",
                "video": "emerald green code scrolling, Virgo symbol, medical cross"
            },
            {
                "text": "Меркурий показывает: ваша придирчивость сегодня — ваш враг...",
                "video": "magnifying glass over documents, green digital grid"
            },
            {
                "text": "Идеальный порядок требует жертв. Узнайте, что нужно исправить...",
                "video": "organized desk, Virgo constellation, emerald light"
            },
            {
                "text": "Ваш перфекционизм ломает ваше окружение. Остановите это...",
                "video": "cracked mirror, green smoke, Virgo maiden statue"
            },
            {
                "text": "Точный медицинский и жизненный прогноз: t.me/SuperAstro2027_bot?start=tiktok_virgo1",
                "video": "bot logo with medical symbol, emerald sparks, arrow"
            }
        ]
    },
    
    "libra": {
        "name_ru": "Весы",
        "style": "гармоничный, дипломатичный, отношения",
        "color": "розовый",
        "clips": [
            {
                "text": "Весы, ваши отношения на грани. Венера требует выбора сегодня...",
                "video": "pink scales tipping, couple silhouettes, rose petals falling"
            },
            {
                "text": "Партнер скрывает правду о ваших чувствах. Узнайте, что происходит...",
                "video": "two faces back to back, Libra symbol, pink mist"
            },
            {
                "text": "Гармония разрушается, если проигнорировать этот знак. У вас есть 24 часа...",
                "video": "broken mirror, balancing act, pink and gold light"
            },
            {
                "text": "Любовь или долг? Выбор, который изменит вашу судьбу...",
                "video": "heart and duty scales, Libra constellation, pink sparkles"
            },
            {
                "text": "Тайна ваших отношений раскрыта: t.me/SuperAstro2027_bot?start=tiktok_libra1",
                "video": "bot logo with heart, pink arrows, romantic glow"
            }
        ]
    },
    
    "scorpio": {
        "name_ru": "Скорпион",
        "style": "интенсивный, мистический, трансформирующий",
        "color": "черный",
        "clips": [
            {
                "text": "Скорпионы, вашу тайну раскрыли! Плутон требует немедленных действий...",
                "video": "black scorpion glowing, dark mist, intense red eyes"
            },
            {
                "text": "Трансформация будет болезненной, но необходимой. Кто стоит за этим?",
                "video": "Scorpio constellation, dark clouds moving, black smoke"
            },
            {
                "text": "Ваша интуиция не лжет: опасность ближе, чем кажется. 97% уже знают...",
                "video": "shadow figure, Scorpio symbol burning, dark flames"
            },
            {
                "text": "Смерть старого — рождение нового. Готовы ли вы к трансформации?",
                "video": "phoenix rising from black ashes, Scorpio stinger glowing"
            },
            {
                "text": "Темное пророчество для Скорпионов: t.me/SuperAstro2027_bot?start=tiktok_scorpio1",
                "video": "bot logo with skull, black and red sparks, arrow"
            }
        ]
    },
    
    "sagittarius": {
        "name_ru": "Стрелец",
        "style": "философский, путешественник, свободолюбивый",
        "color": "фиолетовый",
        "clips": [
            {
                "text": "Стрельцы, ваше путешествие начинается сегодня! Юпитер открывает врата...",
                "video": "purple galaxy, archer shooting arrow, cosmic dust"
            },
            {
                "text": "Вы стоите на пороге великого открытия. Стрела уже выпущена...",
                "video": "Sagittarius constellation, purple nebula, flying arrow"
            },
            {
                "text": "Философская истина, которая изменит ваш взгляд на мир. Не упустите момент...",
                "video": "open book with maps, purple aurora, archer silhouette"
            },
            {
                "text": "Свобода или судьба? Выбор, который определит ваш путь...",
                "video": "broken chains, Sagittarius symbol, purple lightning"
            },
            {
                "text": "Ваше космическое пророчество здесь: t.me/SuperAstro2027_bot?start=tiktok_sagittarius1",
                "video": "bot logo with compass, purple stars, arrow pointing"
            }
        ]
    },
    
    "capricorn": {
        "name_ru": "Козерог",
        "style": "амбициозный, дисциплинированный, успешный",
        "color": "серый",
        "clips": [
            {
                "text": "Козероги, ваш карьерный рост под угрозой! Сатурн требует отчета...",
                "video": "grey mountain peak, goat climbing, corporate building"
            },
            {
                "text": "Амбиции могут разрушить ваш успех, если не узнаете правду сегодня...",
                "video": "Capricorn constellation, grey gears turning, time clock"
            },
            {
                "text": "Ваше терпение будет вознаграждено, но цена может быть высока. Узнайте...",
                "video": "broken chains, mountain climber, grey storm clouds"
            },
            {
                "text": "Только 24 часа, чтобы исправить ошибку в карьере. 89% уже знают...",
                "video": "Capricorn symbol glowing, grey scales, success trophies"
            },
            {
                "text": "Ваш карьерный прогноз от Сатурна: t.me/SuperAstro2027_bot?start=tiktok_capricorn1",
                "video": "bot logo with briefcase, grey city lights, arrow"
            }
        ]
    },
    
    "aquarius": {
        "name_ru": "Водолей",
        "style": "инновационный, независимый, футуристичный",
        "color": "электрик",
        "clips": [
            {
                "text": "Водолеи, будущее уже здесь! Уран активирует ваш гений сегодня...",
                "video": "electric blue circuit board, Aquarius symbol, futuristic city"
            },
            {
                "text": "Инновация требует жертв. Готовы ли вы изменить мир? Время истекает...",
                "video": "Aquarius constellation, electric sparks, digital rain"
            },
            {
                "text": "Ваша независимость под угрозой. Узнайте, кто стоит за этим заговором...",
                "video": "broken chain, electric blue lightning, futuristic mask"
            },
            {
                "text": "Только истинные Водолеи смогут пройти этот тест. Вы один из них?",
                "video": "Aquarius water bearer, electric blue potion, glowing"
            },
            {
                "text": "Ваше футуристическое пророчество: t.me/SuperAstro2027_bot?start=tiktok_aquarius1",
                "video": "bot logo with satellite, electric blue beams, arrow"
            }
        ]
    },
    
    "pisces": {
        "name_ru": "Рыбы",
        "style": "интуитивный, мечтательный, психический",
        "color": "бирюзовый",
        "clips": [
            {
                "text": "Рыбы, ваши сны предсказывают беду! Нептун шепчет правду...",
                "video": "teal ocean waves, Pisces fish swimming, dreamy mist"
            },
            {
                "text": "Интуиция кричит: опасность ближе, чем вы думаете. Послушайте знаки...",
                "video": "Pisces constellation, teal nebula, sleeping person"
            },
            {
                "text": "Ваше подсознание скрывает ответ на главный вопрос. Узнайте, что это...",
                "video": "crystal ball with fish, teal bubbles, underwater scene"
            },
            {
                "text": "Мечты могут стать реальностью, но время на исходе. 97% уже знают...",
                "video": "Pisces symbol glowing, teal waterfall, spiritual glow"
            },
            {
                "text": "Тайное пророчество из ваших снов: t.me/SuperAstro2027_bot?start=tiktok_pisces1",
                "video": "bot logo with moon and waves, teal sparkles, arrow"
            }
        ]
    }
}

def add_stress_marks(text: str) -> str:
    """Add '+' before stressed vowels for Svetlana TTS"""
    stress_dict = {
        "началось": "начА+лось",
        "сегодня": "сегО+дня",
        "остановитесь": "остановИ+тесь",
        "внимание": "внимА+ние",
        "предупреждают": "предупреждА+ют",
        "возможность": "возмО+жность",
        "прислушайтесь": "прислушА+йтесь",
        "мгновение": "мгновЕ+ние",
        "опасность": "опА+сность",
        "успех": "успЕ+х",
        "внимание": "внимА+ние",
        "судьба": "судьбА+",
        "звезды": "звЁ+зды",
        "энергия": "энЕ+ргия",
        "тайна": "тА+йна",
        "срочно": "срО+чно",
        "блокирует": "блокИ+рует",
        "активирует": "активИ+рует",
        "решение": "решЕ+ние",
        "секрет": "секрЕ+т",
        "прогноз": "прогнО+з",
        "уже": "ужЕ+",
        "следующий": "слЕ+дующий"
    }
    result = text
    for word, stressed in stress_dict.items():
        result = result.replace(word, stressed)
    return result

def generate_unique_script(sign: str, total_duration: int = 15, clip_duration: int = 3):
    """Generate UNIQUE script for each zodiac sign"""
    if sign not in SIGN_SCRIPTS:
        print(f"Unknown sign: {sign}")
        return None
    
    data = SIGN_SCRIPTS[sign]
    num_clips = total_duration // clip_duration
    
    script = []
    start_time = 0
    
    for i in range(min(num_clips, len(data["clips"]))):
        end_time = start_time + clip_duration
        time_str = f"{start_time:02d}:{start_time:02d}-{end_time:02d}:{end_time:02d}"
        
        clip_data = data["clips"][i]
        
        clip = {
            "clip_number": i + 1,
            "time": time_str,
            "duration": clip_duration,
            "text": clip_data["text"],
            "text_stressed": add_stress_marks(clip_data["text"]),
            "image_prompt": f"{data['color']} background, {sign} theme, {data['style']}, no watermarks",
            "video_prompt": f"{clip_data['video']}, cinematic 5s",
            "video_length": "5s"
        }
        script.append(clip)
        start_time = end_time
    
    return script

def save_script_package(sign: str, script: list, total_duration: int, clip_duration: int):
    """Save script in all formats"""
    os.makedirs("scripts", exist_ok=True)
    
    # JSON
    json_path = f"scripts/{sign}_{total_duration}s.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    print(f"[OK] JSON: {json_path}")
    
    # TTS text
    tts_path = f"scripts/{sign}_{total_duration}s_tts.txt"
    with open(tts_path, "w", encoding="utf-8") as f:
        f.write(f"=== TEXT FOR SVETLANA ({sign.upper()}, {total_duration}s) ===\n\n")
        for clip in script:
            f.write(f"[{clip['time']}]\n")
            f.write(f"{clip['text_stressed']}\n\n")
    print(f"[OK] TTS text: {tts_path}")
    
    # Video prompts
    video_path = f"scripts/{sign}_{total_duration}s_video_prompts.txt"
    with open(video_path, "w", encoding="utf-8") as f:
        f.write(f"=== VIDEO PROMPTS ({sign.upper()}, 5 clips x 5s) ===\n\n")
        for clip in script:
            f.write(f"CLIP {clip['clip_number']} ({clip['time']}, {clip['duration']}s)\n")
            f.write(f"PROMPT: {clip['video_prompt']}\n")
            f.write(f"Save to: videos/{sign}/clip{clip['clip_number']}.mp4\n")
            f.write("-" * 60 + "\n")
    print(f"[OK] Video prompts: {video_path}")
    
    return json_path, tts_path, video_path

if __name__ == "__main__":
    import sys
    
    sign = sys.argv[1] if len(sys.argv) > 1 else "aries"
    
    print("="*60)
    print(f"UNIQUE SCRIPT FOR {sign.upper()}")
    print(f"Style: {SIGN_SCRIPTS[sign]['style']}")
    print("="*60)
    
    script = generate_unique_script(sign, total_duration=15, clip_duration=3)
    
    if script:
        paths = save_script_package(sign, script, 15, 3)
        
        print("\n" + "="*60)
        print(f"DONE! UNIQUE PACKAGE FOR {sign.upper()}")
        print("="*60)
        print(f"1. Script (JSON): {paths[0]}")
        print(f"2. Text for Svetlana: {paths[1]}")
        print(f"3. Video prompts: {paths[2]}")
        print("\nSCRIPTS ARE NOW UNIQUE FOR EACH SIGN!")
        print("="*60)
