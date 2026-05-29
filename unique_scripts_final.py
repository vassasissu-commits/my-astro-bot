import json
import os
import random

# === TRULY UNIQUE SCRIPTS FOR EACH ZODIAC SIGN ===
# Each sign has completely different content, triggers, and style

def generate_aries_script(total_duration=15, clip_duration=3):
    """Aries: Aggressive, urgent, action-oriented"""
    num_clips = total_duration // clip_duration
    script = []
    start_time = 0
    
    # Unique texts for Aries (no templates!)
    texts = [
        "Овны, стойте! Марс блокирует вашу главную цель на сегодня...",
        "Эта агрессивная энергия разрушит ваши планы, если не узнаете подробности...",
        "Только 24 часа, чтобы изменить ход событий. 89% Овнов уже знают...",
        "Ваша агрессия сегодня — это ваш враг номер один...",
        "Секретный прогноз Марса для Овнов: t.me/SuperAstro2027_bot?start=tiktok_aries1"
    ]
    
    video_prompts = [
        "Dramatic fire explosion, burning ram symbol, intense red flames, cinematic 5s",
        "Mars planet close up, fast orbital movement, dramatic red shadows 5s",
        "Clock ticking fast with red lightning, urgent atmosphere, flames 5s",
        "Ancient ram head statue with cracks appearing, dramatic lighting 5s",
        "Glowing bot logo with fire particles, red arrow pointing down 5s"
    ]
    
    for i in range(num_clips):
        end_time = start_time + clip_duration
        time_str = f"{start_time:02d}:{start_time:02d}-{end_time:02d}:{end_time:02d}"
        
        clip = {
            "clip_number": i + 1,
            "time": time_str,
            "duration": clip_duration,
            "text": texts[i],
            "text_stressed": add_stress(texts[i]),
            "video_prompt": video_prompts[i],
            "image_prompt": f"fire background, ram symbol, red orange colors, dynamic no watermarks"
        }
        script.append(clip)
        start_time = end_time
    
    return script


def generate_taurus_script(total_duration=15, clip_duration=3):
    """Taurus: Sensual, material, calm but warning"""
    num_clips = total_duration // clip_duration
    script = []
    start_time = 0
    
    # Unique texts for Taurus (completely different topics!)
    texts = [
        "Тельцы, ваша финансовая удача под угрозой прямо сейчас...",
        "Венера шепчет: ваше богатство зависит от одного решения сегодня...",
        "Пропустите этот знак — и потеряете шанс на прибыль в этом месяце...",
        "97% Тельцов уже забрали свой финансовый прогноз. Вы следующий?",
        "Узнайте, где спрятаны ваши деньги: t.me/SuperAstro2027_bot?start=tiktok_taurus1"
    ]
    
    video_prompts = [
        "Green meadow with bull statue, golden coins falling from sky, cinematic 5s",
        "Venus planet rotating, floating money bills, soft green glow 5s",
        "Bank notes flying in slow motion, Taurus constellation, luxury items 5s",
        "Closed safe opening slowly with golden light spilling out, dramatic 5s",
        "Bot logo with dollar sign glowing, green sparks falling, arrow down 5s"
    ]
    
    for i in range(num_clips):
        end_time = start_time + clip_duration
        time_str = f"{start_time:02d}:{start_time:02d}-{end_time:02d}:{end_time:02d}"
        
        clip = {
            "clip_number": i + 1,
            "time": time_str,
            "duration": clip_duration,
            "text": texts[i],
            "text_stressed": add_stress(texts[i]),
            "video_prompt": video_prompts[i],
            "image_prompt": f"green nature, bull symbol, gold brown colors, calm earthy no watermarks"
        }
        script.append(clip)
        start_time = end_time
    
    return script


def generate_gemini_script(total_duration=15, clip_duration=3):
    """Gemini: Curious, dual, communication-focused"""
    num_clips = total_duration // clip_duration
    script = []
    start_time = 0
    
    texts = [
        "Близнецы, вам лгут! Узнайте, кто скрывает правду от вас...",
        "Меркурий раскрывает тайну вашего окружения. Это шокирует...",
        "Ваша интуиция кричит, но разум не слышит. Послушайте знаки...",
        "Двойственность разрушает ваши связи. Узнайте, как спасти их...",
        "Тайна, которую скрывают от Близнецов: t.me/SuperAstro2027_bot?start=tiktok_gemini1"
    ]
    
    video_prompts = [
        "Twin shadows in blue mist, mysterious figures whispering, cinematic 5s",
        "Mercury planet spinning fast, chat messages appearing, blue digital rain 5s",
        "Two faces in mirror reflection, whispering mouths, blue neon signs 5s",
        "Broken mirror shards, Gemini symbol glowing, blue electricity 5s",
        "Bot logo with question mark, blue chat bubbles floating, arrow 5s"
    ]
    
    for i in range(num_clips):
        end_time = start_time + clip_duration
        time_str = f"{start_time:02d}:{start_time:02d}-{end_time:02d}:{end_time:02d}"
        
        clip = {
            "clip_number": i + 1,
            "time": time_str,
            "duration": clip_duration,
            "text": texts[i],
            "text_stressed": add_stress(texts[i]),
            "video_prompt": video_prompts[i],
            "image_prompt": f"air background, twins symbol, blue silver colors, dynamic no watermarks"
        }
        script.append(clip)
        start_time = end_time
    
    return script


def generate_cancer_script(total_duration=15, clip_duration=3):
    """Cancer: Emotional, family-oriented, protective"""
    num_clips = total_duration // clip_duration
    script = []
    start_time = 0
    
    texts = [
        "Раки, ваша семья под защитой, но надолго ли? Луна предупреждает...",
        "Эмоциональный шторм сегодня разрушит ваш внутренний покой...",
        "Ваша интуиция видит то, что скрыто от других. Не игнорируйте знаки...",
        "Близкие скрывают правду. Узнайте, что происходит за вашей спиной...",
        "Лунный прогноз для Раков, который изменит всё: t.me/SuperAstro2027_bot?start=tiktok_cancer1"
    ]
    
    video_prompts = [
        "Moon over ocean waves, crab shell glowing silver, cinematic 5s",
        "Stormy sea with crying eyes reflection, silver rain drops 5s",
        "Crystal ball glowing mysteriously, Cancer constellation, silver mist 5s",
        "Family photo burning at edges, shadow figures, silver light leaking 5s",
        "Bot logo with moon crescent, silver sparkles, arrow up 5s"
    ]
    
    for i in range(num_clips):
        end_time = start_time + clip_duration
        time_str = f"{start_time:02d}:{start_time:02d}-{end_time:02d}:{end_time:02d}"
        
        clip = {
            "clip_number": i + 1,
            "time": time_str,
            "duration": clip_duration,
            "text": texts[i],
            "text_stressed": add_stress(texts[i]),
            "video_prompt": video_prompts[i],
            "image_prompt": f"water background, crab symbol, silver blue colors, emotional no watermarks"
        }
        script.append(clip)
        start_time = end_time
    
    return script


def generate_leo_script(total_duration=15, clip_duration=3):
    """Leo: Proud, leadership, dramatic"""
    num_clips = total_duration // clip_duration
    script = []
    start_time = 0
    
    texts = [
        "Львы, ваша корона под угрозой! Кто посмеет бросить вам вызов?",
        "Солнце предупреждает: ваша слава может померкнуть уже сегодня...",
        "Лидерство требует жертв. Готовы ли вы заплатить эту цену?",
        "Только истинные Львы смогут пройти это испытание. Вы один из них?",
        "Ваше королевское пророчество здесь: t.me/SuperAstro2027_bot?start=tiktok_leo1"
    ]
    
    video_prompts = [
        "Golden crown glowing with fire, lion roaring, golden flames 5s",
        "Solar eclipse with Leo constellation, golden dust falling 5s",
        "Lion sitting on throne, golden scales tipping, dramatic lighting 5s",
        "Golden mane flowing in wind, Leo symbol glowing, golden sparks 5s",
        "Bot logo with crown on top, golden rays shining, arrow pointing 5s"
    ]
    
    for i in range(num_clips):
        end_time = start_time + clip_duration
        time_str = f"{start_time:02d}:{start_time:02d}-{end_time:02d}:{end_time:02d}"
        
        clip = {
            "clip_number": i + 1,
            "time": time_str,
            "duration": clip_duration,
            "text": texts[i],
            "text_stressed": add_stress(texts[i]),
            "video_prompt": video_prompts[i],
            "image_prompt": f"gold background, lion symbol, yellow orange colors, majestic no watermarks"
        }
        script.append(clip)
        start_time = end_time
    
    return script


def add_stress(text: str) -> str:
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


def save_script(sign: str, script: list, total_duration: int):
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


def generate_all_signs():
    """Generate UNIQUE scripts for all 12 zodiac signs"""
    signs = {
        "aries": generate_aries_script,
        "taurus": generate_taurus_script,
        "gemini": generate_gemini_script,
        "cancer": generate_cancer_script,
        "leo": generate_leo_script,
        # Add remaining 7 signs...
    }
    
    print("="*60)
    print("GENERATING UNIQUE SCRIPTS FOR ALL ZODIAC SIGNS")
    print("="*60)
    
    for sign, generator_func in signs.items():
        print(f"\n[*] Generating UNIQUE script for {sign.upper()}...")
        script = generator_func(total_duration=15, clip_duration=3)
        paths = save_script(sign, script, 15)
        print(f"    Done! Files: {paths[0]}, {paths[1]}, {paths[2]}")
    
    print("\n" + "="*60)
    print("ALL UNIQUE SCRIPTS GENERATED!")
    print("="*60)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        sign = sys.argv[1]
        print(f"Generating UNIQUE script for {sign.upper()}...")
        
        generators = {
            "aries": generate_aries_script,
            "taurus": generate_taurus_script,
            "gemini": generate_gemini_script,
            "cancer": generate_cancer_script,
            "leo": generate_leo_script,
        }
        
        if sign in generators:
            script = generators[sign](total_duration=15, clip_duration=3)
            save_script(sign, script, 15)
        else:
            print(f"Generator for {sign} not implemented yet. Available: aries, taurus, gemini, cancer, leo")
    else:
        generate_all_signs()