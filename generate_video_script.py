import json
import os

def generate_structured_script(sign: str, total_duration: int = 15, clip_duration: int = 3):
    """
    Generate structured script: total_duration seconds, clip_duration per image/video.
    Output: List of (time, text, image_prompt, video_prompt)
    """
    num_clips = total_duration // clip_duration
    
    # Zodiac sign themes
    themes = {
        "aries": {
            "element": "fire",
            "colors": "red, orange, gold",
            "symbol": "ram",
            "keywords": "dynamic, energetic, bold, leadership"
        },
        "taurus": {
            "element": "earth",
            "colors": "green, brown, gold",
            "symbol": "bull",
            "keywords": "stable, nature, calm, luxurious"
        },
        "gemini": {
            "element": "air",
            "colors": "blue, silver, yellow",
            "symbol": "twins",
            "keywords": "communication, duality, social, curious"
        }
        # Add all 12 signs similarly
    }
    
    theme = themes.get(sign, themes["aries"])
    
    # Generate script structure
    script = []
    start_time = 0
    
    for i in range(num_clips):
        end_time = start_time + clip_duration
        time_str = f"{start_time:02d}:{start_time:02d}-{end_time:02d}:{end_time:02d}"
        
        # Text for this clip (selling astrology style)
        texts = [
            f"{sign.capitalize()}, остановитесь! Звезды предупреждают...",
            f"Марс в {theme['element']} стихии активирует вашу судьбу...",
            f"У вас есть только 24 часа, чтобы изменить будущее...",
            f"97% {sign} уже получили секретный прогноз...",
            f"Узнайте полный прогноз: t.me/SuperAstro2027_bot?start=tiktok_{sign}1"
        ]
        
        # Image prompt (for image generation or stock photos)
        image_prompts = [
            f"{theme['element']} background, {theme['symbol']} symbol, {theme['colors']}, dynamic, no watermarks",
            f"cosmic scene, planets aligning, {theme['colors']}, mystical atmosphere",
            f"clock ticking, {theme['colors']} lighting, dramatic shadows, urgency",
            f"stars in night sky, constellation {sign}, {theme['colors']}, magical",
            f"Telegram bot logo, {theme['colors']}, glowing, arrow pointing to link"
        ]
        
        # Video prompt (for AI video generation: Luma, Pika, etc.)
        video_prompts = [
            f"Dramatic {theme['element']} explosion, {theme['symbol']} appearing, cinematic",
            f"Planets moving in space, zodiac wheel spinning, cosmic energy flowing",
            f"Clock hands moving fast, time running out, dramatic lighting",
            f"Stars twinkling, constellation forming, mystical clouds moving",
            f"Glowing logo appearing, sparkles, arrow drawing towards link"
        ]
        
        clip = {
            "clip_number": i + 1,
            "time": time_str,
            "duration": clip_duration,
            "text": texts[i % len(texts)],
            "image_prompt": image_prompts[i % len(image_prompts)],
            "video_prompt": video_prompts[i % len(video_prompts)],
            "audio_text": texts[i % len(texts)]  # Text for TTS
        }
        
        # Add stress marks for Svetlana TTS
        clip["audio_text_stressed"] = add_stress_marks(clip["audio_text"])
        
        script.append(clip)
        start_time = end_time
    
    return script

def add_stress_marks(text: str) -> str:
    """Add '+' before stressed vowels (for Edge-TTS Svetlana)"""
    stress_dict = {
        "началось": "начА+лось",
        "сегодня": "сегО+дня",
        "остановитесь": "остановИ+тесь",
        "предупреждают": "предупреждА+ют",
        "активирует": "активИ+рует",
        "внимание": "внимА+ние",
        "возможность": "возмО+жность",
        "прислушайтесь": "прислушА+йтесь"
    }
    
    result = text
    for word, stressed in stress_dict.items():
        result = result.replace(word, stressed)
    return result

def save_script(sign: str, script: list, total_duration: int, clip_duration: int):
    """Save script in multiple formats"""
    os.makedirs("scripts", exist_ok=True)
    
    # JSON format (structured data)
    json_path = f"scripts/{sign}_{total_duration}s_{clip_duration}s_clips.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    print(f"[OK] JSON saved: {json_path}")
    
    # Ready-to-use text for TTS (just copy-paste)
    tts_path = f"scripts/{sign}_{total_duration}s_tts.txt"
    with open(tts_path, "w", encoding="utf-8") as f:
        f.write(f"=== ТЕКСТ ДЛЯ ОЗВУЧКИ ({sign.upper()}, {total_duration}с) ===\n\n")
        for clip in script:
            f.write(f"[{clip['time']}] {clip['audio_text_stressed']}\n")
    print(f"[OK] TTS text saved: {tts_path}")
    
    # Prompts for image/video generation
    prompts_path = f"scripts/{sign}_{total_duration}s_prompts.txt"
    with open(prompts_path, "w", encoding="utf-8") as f:
        f.write(f"=== ПРОМПТЫ ДЛЯ ГЕНЕРАЦИИ ({sign.upper()}, {total_duration}с) ===\n\n")
        for clip in script:
            f.write(f"КЛИП {clip['clip_number']} ({clip['time']}, {clip['duration']}с)\n")
            f.write(f"ТЕКСТ: {clip['text']}\n")
            f.write(f"КАРТИНКА: {clip['image_prompt']}\n")
            f.write(f"ВИДЕО: {clip['video_prompt']}\n")
            f.write("-" * 60 + "\n")
    print(f"[OK] Prompts saved: {prompts_path}")
    
    return json_path, tts_path, prompts_path

def generate_all_formats(sign: str, total_duration: int = 15, clip_duration: int = 3):
    """Generate complete script package"""
    print("="*60)
    print(f"ГЕНЕРАЦИЯ СЦЕНАРИЯ: {sign.upper()}")
    print(f"Всего: {total_duration}с, Клипов: {total_duration//clip_duration}, По: {clip_duration}с")
    print("="*60)
    
    script = generate_structured_script(sign, total_duration, clip_duration)
    paths = save_script(sign, script, total_duration, clip_duration)
    
    print("\n" + "="*60)
    print("ГОТОВО! Файлы для:")
    print(f"1. Озвучки: {paths[1]}")
    print(f"2. Генерации картинок: см. {paths[2]}")
    print(f"3. Генерации видео: см. {paths[2]}")
    print("="*60)
    
    return paths

if __name__ == "__main__":
    import sys
    
    sign = sys.argv[1] if len(sys.argv) > 1 else "aries"
    total_dur = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    clip_dur = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    
    generate_all_formats(sign, total_dur, clip_dur)