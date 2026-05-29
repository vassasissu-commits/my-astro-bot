import json
import os

# === TEMPLATES FOR 12 ZODIAC SIGNS ===
SIGN_DATA = {
    "aries": {
        "name_ru": "Овен",
        "element": "fire",
        "symbol": "ram",
        "colors": "red, orange, gold",
        "keywords": "energetic, bold, leadership, dynamic",
        "triggers": ["срочность", "успех", "действие", "энергия"]
    },
    "taurus": {
        "name_ru": "Телец",
        "element": "earth", 
        "symbol": "bull",
        "colors": "green, brown, gold",
        "keywords": "stable, nature, calm, luxurious",
        "triggers": ["деньги", "стабильность", "комфорт", "ресурсы"]
    },
    "gemini": {
        "name_ru": "Близнецы",
        "element": "air",
        "symbol": "twins",
        "colors": "blue, silver, yellow",
        "keywords": "communication, duality, social, curious",
        "triggers": ["тайны", "информация", "контакты", "ложь"]
    },
    "cancer": {
        "name_ru": "Рак",
        "element": "water",
        "symbol": "crab",
        "colors": "silver, blue, white",
        "keywords": "emotional, family, intuitive, protective",
        "triggers": ["семья", "эмоции", "защита", "дом"]
    },
    "leo": {
        "name_ru": "Лев",
        "element": "fire",
        "symbol": "lion",
        "colors": "gold, yellow, orange",
        "keywords": "proud, leadership, dramatic, generous",
        "triggers": ["слава", "признание", "лидерство", "успех"]
    },
    "virgo": {
        "name_ru": "Дева",
        "element": "earth",
        "symbol": "maiden",
        "colors": "green, brown, beige",
        "keywords": "precise, health, analysis, service",
        "triggers": ["здоровье", "порядок", "ошибка", "исправление"]
    },
    "libra": {
        "name_ru": "Весы",
        "element": "air",
        "symbol": "scales",
        "colors": "pink, blue, gold",
        "keywords": "balanced, harmonious, diplomatic, beautiful",
        "triggers": ["отношения", "баланс", "партнер", "скрывает"]
    },
    "scorpio": {
        "name_ru": "Скорпион",
        "element": "water",
        "symbol": "scorpion",
        "colors": "black, red, dark blue",
        "keywords": "intense, mysterious, transformative, secretive",
        "triggers": ["тайна", "правда", "трансформация", "скрытое"]
    },
    "sagittarius": {
        "name_ru": "Стрелец",
        "element": "fire",
        "symbol": "archer",
        "colors": "purple, gold, blue",
        "keywords": "adventurous, optimistic, philosophical, free",
        "triggers": ["путешествие", "рост", "будущее", "начнется"]
    },
    "capricorn": {
        "name_ru": "Козерог",
        "element": "earth",
        "symbol": "goat",
        "colors": "grey, brown, black",
        "keywords": "ambitious, disciplined, patient, successful",
        "triggers": ["карьера", "успех", "повышение", "достижение"]
    },
    "aquarius": {
        "name_ru": "Водолей",
        "element": "air",
        "symbol": "water bearer",
        "colors": "electric blue, silver, cyan",
        "keywords": "innovative, independent, humanitarian, futuristic",
        "triggers": ["будущее", "инновации", "придет", "новое"]
    },
    "pisces": {
        "name_ru": "Рыбы",
        "element": "water",
        "symbol": "fish",
        "colors": "teal, blue, sea green",
        "keywords": "intuitive, dreamy, compassionate, psychic",
        "triggers": ["сон", "интуиция", "предупреждает", "чувства"]
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
        "внимание": "внимА+ние"
    }
    result = text
    for word, stressed in stress_dict.items():
        result = result.replace(word, stressed)
    return result

def generate_script_for_sign(sign: str, total_duration: int = 15, clip_duration: int = 3):
    """Generate complete script: 5 clips (3s each) for 15s video"""
    if sign not in SIGN_DATA:
        print(f"Unknown sign: {sign}")
        return None
    
    data = SIGN_DATA[sign]
    name_ru = data["name_ru"]
    num_clips = total_duration // clip_duration
    
    script = []
    start_time = 0
    
    # Template texts (selling astrology style)
    texts = [
        f"{name_ru}, остановитесь! Звезды предупреждают...",
        f"Сегодня Марс активирует вашу судьбу. {data['triggers'][0].capitalize()} ждет вас...",
        f"У вас есть только 24 часа! {data['triggers'][1].capitalize()} зависит от решения...",
        f"97% {name_ru}ов уже получили секрет. Вы успеете?",
        f"Полный прогноз: t.me/SuperAstro2027_bot?start=tiktok_{sign}1"
    ]
    
    # Image prompts (for stock photos or AI generation)
    image_prompts = [
        f"{data['element']} background, {data['symbol']} symbol, {data['colors']}, dynamic, no watermarks",
        f"cosmic scene, planets aligning, {data['colors']}, mystical atmosphere",
        f"clock ticking, {data['colors']} lighting, dramatic shadows, urgency",
        f"stars night sky, constellation {sign}, {data['colors']}, magical",
        f"Telegram bot logo, {data['colors']}, glowing, arrow pointing to link"
    ]
    
    # Video prompts (for Luma, Pika, Kling - 5s clips)
    video_prompts = [
        f"Dramatic {data['element']} explosion, {data['symbol']} appearing, cinematic 5s",
        f"Planets moving in space, zodiac wheel spinning, cosmic energy flowing 5s",
        f"Clock hands moving fast, time running out, dramatic lighting 5s",
        f"Stars twinkling, constellation forming, mystical clouds moving 5s",
        f"Glowing logo appearing, sparkles, arrow drawing towards link 5s"
    ]
    
    for i in range(num_clips):
        end_time = start_time + clip_duration
        time_str = f"{start_time:02d}:{start_time:02d}-{end_time:02d}:{end_time:02d}"
        
        clip = {
            "clip_number": i + 1,
            "time": time_str,
            "duration": clip_duration,
            "text": texts[i],
            "text_stressed": add_stress_marks(texts[i]),
            "image_prompt": image_prompts[i],
            "video_prompt": video_prompts[i],
            "video_length": "5s"  # Each video clip is 5s (Luma/Pika)
        }
        script.append(clip)
        start_time = end_time
    
    return script

def save_complete_package(sign: str, script: list, total_duration: int, clip_duration: int):
    """Save ALL formats needed for video creation"""
    os.makedirs("scripts", exist_ok=True)
    os.makedirs(f"images/{sign}", exist_ok=True)
    os.makedirs(f"videos/{sign}", exist_ok=True)
    os.makedirs(f"audio/{sign}", exist_ok=True)
    
    # 1. JSON (structured data)
    json_path = f"scripts/{sign}_{total_duration}s.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    print(f"[OK] JSON: {json_path}")
    
    # 2. TTS text (ready for Svetlana)
    tts_path = f"scripts/{sign}_{total_duration}s_tts.txt"
    with open(tts_path, "w", encoding="utf-8") as f:
        f.write(f"=== ТЕКСТ ДЛЯ ОЗВУЧКИ СВЕТЛАНОЙ ({sign.upper()}, {total_duration}с) ===\n\n")
        for clip in script:
            f.write(f"[{clip['time']}]\n")
            f.write(f"{clip['text_stressed']}\n\n")
    print(f"[OK] TTS text: {tts_path}")
    
    # 3. Video prompts (for Luma/Pika - copy-paste)
    video_path = f"scripts/{sign}_{total_duration}s_video_prompts.txt"
    with open(video_path, "w", encoding="utf-8") as f:
        f.write(f"=== ПРОМПТЫ ДЛЯ ВИДЕО ({sign.upper()}, 5 клипов по 5с) ===\n\n")
        for clip in script:
            f.write(f"КЛИП {clip['clip_number']} ({clip['time']}, {clip['duration']}с)\n")
            f.write(f"ПРОМПТ: {clip['video_prompt']}\n")
            f.write(f"Сохранить как: videos/{sign}/clip{clip['clip_number']}.mp4\n")
            f.write("-" * 60 + "\n")
    print(f"[OK] Video prompts: {video_path}")
    
    # 4. Image prompts (for stock photos)
    img_path = f"scripts/{sign}_{total_duration}s_image_prompts.txt"
    with open(img_path, "w", encoding="utf-8") as f:
        f.write(f"=== ПРОМПТЫ ДЛЯ КАРТИНОК ({sign.upper()}) ===\n\n")
        for clip in script:
            f.write(f"КЛИП {clip['clip_number']}: {clip['image_prompt']}\n")
            f.write(f"Сохранить в: images/{sign}/clip{clip['clip_number']}.jpg\n")
    print(f"[OK] Image prompts: {img_path}")
    
    return json_path, tts_path, video_path, img_path

def generate_all_for_sign(sign: str):
    """Generate complete package for one sign"""
    print("="*60)
    print(f"ГЕНЕРАЦИЯ ПОЛНОГО ПАКЕТА: {sign.upper()}")
    print("="*60)
    
    # 15 seconds = 5 clips x 3 seconds each
    script = generate_script_for_sign(sign, total_duration=15, clip_duration=3)
    
    if script:
        paths = save_complete_package(sign, script, 15, 3)
        
        print("\n" + "="*60)
        print(f"ГОТОВО! ПАКЕТ ДЛЯ {sign.upper()}")
        print("="*60)
        print(f"1. Сценарий (JSON): {paths[0]}")
        print(f"2. Текст для Светланы: {paths[1]}")
        print(f"3. Промпты для видео (Luma/Pika): {paths[2]}")
        print(f"4. Промпты для картинок: {paths[3]}")
        print("\nСЛЕДУЮЩИЕ ШАГИ:")
        print("1. Скопируй промпты из файла видео")
        print("2. Залей в Luma/Pika (5 клипов по 5с)")
        print("3. Скачай и положи в videos/{sign}/")
        print("4. Озвучь текст через Светлану")
        print("5. Смонтируй в CapCut")
        print("="*60)
        
        return paths
    return None

if __name__ == "__main__":
    import sys
    
    sign = sys.argv[1] if len(sys.argv) > 1 else "aries"
    
    print("\n" + "="*60)
    print("АВТОМАТИЧЕСКАЯ ГЕНЕРАЦИЯ ВИДЕО-СЦЕНАРИЕВ")
    print("15 секунд = 5 клипов по 3 секунды")
    print("Каждый клип -> 5-сек видео (Luma/Pika)")
    print("="*60 + "\n")
    
    generate_all_for_sign(sign)