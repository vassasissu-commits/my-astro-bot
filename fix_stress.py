import re
import json
import os

def add_stress_marks(text: str) -> str:
    """
    Add '+' before stressed vowels in Russian text for Edge-TTS Svetlana.
    Common stress patterns for Russian words.
    """
    # Dictionary of words with stress marks (add more as you find errors)
    stress_dict = {
        # Common words where Svetlana might stress wrong
        "началось": "начА+лось",
        "начинается": "начинА+ется",
        "согласие": "соглА+сие",
        "успех": "успЕ+х",
        "препятствие": "препЯ+тствие",
        "возможность": "возмО+жность",
        "сегодня": "сегО+дня",
        "завтра": "зА+втра",
        "предупреждают": "предупреждА+ют",
        "опасность": "опА+сность",
        "советую": "совЕ+тую",
        "посмотрите": "посмотрИ+те",
        "прислушайтесь": "прислушА+йтесь",
        "остановитесь": "остановИ+тесь",
        "внимание": "внимА+ние",
        "мгновение": "мгновЕ+ние",
    }
    
    result = text
    for word, stressed in stress_dict.items():
        # Replace whole word only (case-insensitive)
        pattern = re.compile(r'\b' + word + r'\b', re.IGNORECASE)
        result = pattern.sub(stressed, result)
    
    return result

def process_script_file(sign: str, duration: int = 30):
    """Process script JSON and add stress marks to all text fields"""
    script_path = f"scripts/{sign}_{duration}s.json"
    
    if not os.path.exists(script_path):
        print(f"Script not found: {script_path}")
        print("Generating example script for", sign)
        # Create example script if not exists
        example = [
            {"time": "0:00-0:03", "text": "Овны, остановитесь! Плутон заблокировал вашу удачу...", "video": "fire"},
            {"time": "0:03-0:12", "text": "Сегодня началось что-то важное. Марс предупреждает...", "video": "mars"},
            {"time": "0:12-0:25", "text": "У вас есть возможность изменить успех. Прислушайтесь к звездам!", "video": "stars"},
            {"time": "0:25-0:30", "text": "Полный прогноз: t.me/SuperAstro2027_bot?start=tiktok_aries1", "video": "bot"}
        ]
        os.makedirs("scripts", exist_ok=True)
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(example, f, ensure_ascii=False, indent=2)
    
    # Load and process
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)
    
    print(f"Processing script: {script_path}")
    print("="*60)
    
    for i, item in enumerate(script):
        original = item["text"]
        stressed = add_stress_marks(original)
        
        if original != stressed:
            print(f"\n[{item['time']}]")
            print(f"  БЫЛО: {original}")
            print(f"  СТАЛО: {stressed}")
            item["text_stressed"] = stressed
        else:
            item["text_stressed"] = original
    
    # Save processed script
    output_path = f"scripts/{sign}_{duration}s_stressed.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    
    # Also save as ready-to-use text file
    text_path = f"scripts/{sign}_{duration}s_ready.txt"
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(f"=== ГОТОВЫЙ ТЕКСТ ДЛЯ ОЗВУЧКИ ({sign.upper()}) ===\n\n")
        for item in script:
            f.write(f"[{item['time']}]\n")
            f.write(f"{item['text_stressed']}\n\n")
    
    print(f"\n[OK] Saved: {output_path}")
    print(f"[OK] Saved: {text_path}")
    print("\n" + "="*60)
    print("ИСПОЛЬЗУЙ ФАЙЛ С '_stressed' ДЛЯ ОЗВУЧКИ!")
    print("В тексте '+' перед гласной = ударение")
    print("="*60)
    
    return output_path

def generate_tts_with_stress(sign: str, duration: int = 30):
    """Generate TTS using processed script with stress marks"""
    import sys
    sys.path.append('.')
    from tts_batch import generate_tts_edge
    
    script_path = f"scripts/{sign}_{duration}s_stressed.json"
    if not os.path.exists(script_path):
        script_path = process_script_file(sign, duration)
    
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)
    
    # Combine all text with pauses
    full_text = ""
    for item in script:
        full_text += item["text_stressed"] + " <break time='500ms'/> "
    
    print(f"\nGenerating TTS for {sign} with stress marks...")
    output_dir = f"audio/{sign}"
    os.makedirs(output_dir, exist_ok=True)
    output_path = f"{output_dir}/{sign}_{duration}s.mp3"
    
    # Use Svetlana voice
    result = generate_tts_edge(full_text, sign, voice="ru-RU-SvetlanaNeural")
    return result

if __name__ == "__main__":
    import sys
    sign = sys.argv[1] if len(sys.argv) > 1 else "aries"
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    print("="*60)
    print(f"PROCESSING SCRIPT FOR {sign.upper()} ({duration}s)")
    print("="*60)
    
    # Process script and add stress marks
    process_script_file(sign, duration)
    
    # Generate TTS with proper stress
    # generate_tts_with_stress(sign, duration)
    print("\nTIP: Edit 'stress_dict' in this script to add more words!")