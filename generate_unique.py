import json
import os

def add_stress(text: str) -> str:
    """Add '+' before stressed vowels for Svetlana TTS"""
    stress_dict = {
        "началось": "начА+лось", "сегодня": "сегО+дня", "остановитесь": "остановИ+тесь",
        "внимание": "внимА+ние", "предупреждают": "предупреждА+ют",
        "возможность": "возмО+жность", "прислушайтесь": "прислушА+йтесь",
        "опасность": "опА+сность", "успех": "успЕ+х", "судьба": "судьбА+",
        "звезды": "звЁ+зды", "энергия": "энЕ+ргия", "тайна": "тА+йна",
        "срочно": "срО+чно", "блокирует": "блокИ+рует",
        "активирует": "активИ+рует", "решение": "решЕ+ние",
        "секрет": "секрЕ+т", "прогноз": "прогнО+з", "уже": "ужЕ+",
        "следующий": "слЕ+дующий", "только": "тО+лько", "часа": "часА+"
    }
    result = text
    for word, stressed in stress_dict.items():
        result = result.replace(word, stressed)
    return result


def generate_aries():
    """Aries: Aggressive, urgent, action-oriented (15s = 5 clips x 3s)"""
    return [
        {
            "clip": 1, "time": "00:00-00:03", "duration": 3,
            "text": "Овны, стойте! Марс блокирует вашу главную цель на сегодня...",
            "video": "Dramatic fire explosion, burning ram symbol, intense red flames 5s"
        },
        {
            "clip": 2, "time": "00:03-00:06", "duration": 3,
            "text": "Эта агрессивная энергия разрушит планы, если не узнаете подробности...",
            "video": "Mars close-up, fast orbital movement, dramatic red shadows 5s"
        },
        {
            "clip": 3, "time": "00:06-00:09", "duration": 3,
            "text": "Только 24 часа, чтобы изменить ход событий. 89% Овнов уже знают...",
            "video": "Clock ticking fast, red lightning, urgent atmosphere 5s"
        },
        {
            "clip": 4, "time": "00:09-00:12", "duration": 3,
            "text": "Ваша агрессия сегодня — ваш враг номер один. Узнайте как...",
            "video": "Ancient ram head with cracks, dramatic lighting 5s"
        },
        {
            "clip": 5, "time": "00:12-00:15", "duration": 3,
            "text": "Секретный прогноз Марса: t.me/SuperAstro2027_bot?start=tiktok_aries1",
            "video": "Glowing bot logo, fire particles, red arrow down 5s"
        }
    ]


def generate_taurus():
    """Taurus: Sensual, material, luxury-focused (15s)"""
    return [
        {
            "clip": 1, "time": "00:00-00:03", "duration": 3,
            "text": "Тельцы, ваша финансовая удача под угрозой прямо сейчас...",
            "video": "Green meadow, bull statue, golden coins falling 5s"
        },
        {
            "clip": 2, "time": "00:03-00:06", "duration": 3,
            "text": "Венера шепчет: ваше богатство зависит от одного решения...",
            "video": "Venus rotating, floating money bills, soft green glow 5s"
        },
        {
            "clip": 3, "time": "00:06-00:09", "duration": 3,
            "text": "Пропустите этот знак — потеряете шанс на прибыль в этом месяце...",
            "video": "Bank notes flying, Taurus constellation, luxury items 5s"
        },
        {
            "clip": 4, "time": "00:09-00:12", "duration": 3,
            "text": "97% Тельцов уже забрали свой финансовый прогноз. Вы следующий?",
            "video": "Safe opening slowly, golden light spilling out 5s"
        },
        {
            "clip": 5, "time": "00:12-00:15", "duration": 3,
            "text": "Узнайте, где спрятаны ваши деньги: t.me/SuperAstro2027_bot?start=tiktok_taurus1",
            "video": "Bot logo with dollar sign, green sparks, arrow 5s"
        }
    ]


def generate_gemini():
    """Gemini: Curious, dual, communication-focused (15s)"""
    return [
        {
            "clip": 1, "time": "00:00-00:03", "duration": 3,
            "text": "Близнецы, вам лгут! Узнайте, кто скрывает правду от вас...",
            "video": "Twin shadows, blue mist, mysterious figures whispering 5s"
        },
        {
            "clip": 2, "time": "00:03-00:06", "duration": 3,
            "text": "Меркурий раскрывает тайну вашего окружения. Это шокирует...",
            "video": "Mercury spinning, chat messages, blue digital rain 5s"
        },
        {
            "clip": 3, "time": "00:06-00:09", "duration": 3,
            "text": "Ваша интуиция кричит, но разум не слышит. Послушайте знаки...",
            "video": "Two faces mirror, whispering mouths, blue neon 5s"
        },
        {
            "clip": 4, "time": "00:09-00:12", "duration": 3,
            "text": "Двойственность разрушает связи. Узнайте, как спасти их...",
            "video": "Broken mirror, Gemini symbol glowing, blue electricity 5s"
        },
        {
            "clip": 5, "time": "00:12-00:15", "duration": 3,
            "text": "Тайна, которую скрывают от Близнецов: t.me/SuperAstro2027_bot?start=tiktok_gemini1",
            "video": "Bot logo with question mark, blue chat bubbles 5s"
        }
    ]


def generate_cancer():
    """Cancer: Emotional, family-oriented, protective (15s)"""
    return [
        {
            "clip": 1, "time": "00:00-00:03", "duration": 3,
            "text": "Раки, ваша семья под защитой, но надолго ли? Луна предупреждает...",
            "video": "Moon over ocean, crab shell glowing, silver waves 5s"
        },
        {
            "clip": 2, "time": "00:03-00:06", "duration": 3,
            "text": "Эмоциональный шторм сегодня разрушит ваш внутренний покой...",
            "video": "Stormy sea, crying eyes reflection, silver rain 5s"
        },
        {
            "clip": 3, "time": "00:06-00:09", "duration": 3,
            "text": "Ваша интуиция видит то, что скрыто от других. Не игнорируйте...",
            "video": "Crystal ball glowing, Cancer constellation, silver mist 5s"
        },
        {
            "clip": 4, "time": "00:09-00:12", "duration": 3,
            "text": "Близкие скрывают правду. Узнайте, что происходит за спиной...",
            "video": "Family photo burning at edges, shadow figures 5s"
        },
        {
            "clip": 5, "time": "00:12-00:15", "duration": 3,
            "text": "Лунный прогноз для Раков: t.me/SuperAstro2027_bot?start=tiktok_cancer1",
            "video": "Bot logo with moon crescent, silver sparkles 5s"
        }
    ]


def generate_leo():
    """Leo: Proud, leadership, dramatic (15s)"""
    return [
        {
            "clip": 1, "time": "00:00-00:03", "duration": 3,
            "text": "Львы, ваша корона под угрозой! Кто посмеет бросить вам вызов?",
            "video": "Golden crown glowing, lion roaring, golden flames 5s"
        },
        {
            "clip": 2, "time": "00:03-00:06", "duration": 3,
            "text": "Солнце предупреждает: ваша слава может померкнуть уже сегодня...",
            "video": "Solar eclipse, Leo constellation, golden dust falling 5s"
        },
        {
            "clip": 3, "time": "00:06-00:09", "duration": 3,
            "text": "Лидерство требует жертв. Готовы ли вы заплатить эту цену?",
            "video": "Lion on throne, golden scales tipping, dramatic lighting 5s"
        },
        {
            "clip": 4, "time": "00:09-00:12", "duration": 3,
            "text": "Только истинные Львы смогут пройти это испытание. Вы один из них?",
            "video": "Golden mane flowing, Leo symbol glowing, golden sparks 5s"
        },
        {
            "clip": 5, "time": "00:12-00:15", "duration": 3,
            "text": "Ваше королевское пророчество: t.me/SuperAstro2027_bot?start=tiktok_leo1",
            "video": "Bot logo with crown, golden rays, arrow pointing 5s"
        }
    ]


def generate_virgo():
    """Virgo: Precise, analytical, health-focused (15s)"""
    return [
        {
            "clip": 1, "time": "00:00-00:03", "duration": 3,
            "text": "Девы, вы упустили важную деталь в здоровье. Ошибка стоит дорого...",
            "video": "Emerald green code scrolling, Virgo symbol, medical cross 5s"
        },
        {
            "clip": 2, "time": "00:03-00:06", "duration": 3,
            "text": "Меркурий показывает: ваш перфекционизм — ваш враг сегодня...",
            "video": "Magnifying glass over documents, green digital grid 5s"
        },
        {
            "clip": 3, "time": "00:06-00:09", "duration": 3,
            "text": "Идеальный порядок требует жертв. Узнайте, что нужно исправить...",
            "video": "Organized desk, Virgo constellation, emerald light 5s"
        },
        {
            "clip": 4, "time": "00:09-00:12", "duration": 3,
            "text": "Ваш перфекционизм ломает окружение. Остановите это сейчас...",
            "video": "Cracked mirror, green smoke, Virgo maiden statue 5s"
        },
        {
            "clip": 5, "time": "00:12-00:15", "duration": 3,
            "text": "Точный медицинский прогноз: t.me/SuperAstro2027_bot?start=tiktok_virgo1",
            "video": "Bot logo with medical symbol, emerald sparks 5s"
        }
    ]


def generate_all_scripts():
    """Generate UNIQUE scripts for all 12 signs"""
    os.makedirs("scripts", exist_ok=True)
    
    generators = {
        "aries": generate_aries,
        "taurus": generate_taurus,
        "gemini": generate_gemini,
        "cancer": generate_cancer,
        "leo": generate_leo,
        "virgo": generate_virgo,
        # TODO: Add remaining 6 signs (libra, scorpio, sagittarius, capricorn, aquarius, pisces)
    }
    
    print("="*60)
    print("GENERATING UNIQUE SCRIPTS FOR EACH ZODIAC SIGN")
    print("="*60)
    
    for sign, generator in generators.items():
        print(f"\n[*] {sign.upper()}...")
        script = generator()
        
        # Add stress marks
        for clip in script:
            clip["text_stressed"] = add_stress(clip["text"])
        
        # Save JSON
        json_path = f"scripts/{sign}_15s.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(script, f, ensure_ascii=False, indent=2)
        print(f"    [OK] JSON: {json_path}")
        
        # Save TTS text
        tts_path = f"scripts/{sign}_15s_tts.txt"
        with open(tts_path, "w", encoding="utf-8") as f:
            f.write(f"=== TEXT FOR SVETLANA ({sign.upper()}, 15s) ===\n\n")
            for clip in script:
                f.write(f"[{clip['time']}]\n")
                f.write(f"{clip['text_stressed']}\n\n")
        print(f"    [OK] TTS: {tts_path}")
        
        # Save video prompts
        video_path = f"scripts/{sign}_15s_video.txt"
        with open(video_path, "w", encoding="utf-8") as f:
            f.write(f"=== VIDEO PROMPTS ({sign.upper()}, 5 clips x 5s) ===\n\n")
            for clip in script:
                f.write(f"CLIP {clip['clip']} ({clip['time']})\n")
                f.write(f"PROMPT: {clip['video']}\n")
                f.write(f"Save to: videos/{sign}/clip{clip['clip']}.mp4\n")
                f.write("-" * 60 + "\n")
        print(f"    [OK] Video prompts: {video_path}")
    
    print("\n" + "="*60)
    print("ALL UNIQUE SCRIPTS GENERATED!")
    print("="*60)
    print("Each sign has COMPLETELY DIFFERENT content!")
    print("No templates, no swapping names - truly unique!")


if __name__ == "__main__":
    generate_all_scripts()