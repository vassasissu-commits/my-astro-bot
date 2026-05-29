import os
import json
from groq import Groq

# Groq API (free tier)
GROQ_API_KEY = "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"

def generate_script(sign: str, duration: int = 30, topic: str = "гороскоп на сегодня"):
    """
    Generate selling script for zodiac sign (style: Nastya's Wars esoteric)
    Returns: List of (time, text, video_description) tuples
    """
    client = Groq(api_key=GROQ_API_KEY)
    
    prompt = f"""Ты — топовый сценарист эзотерического контента в стиле "Насти Войны".
Пиши продающий сценарий гороскопа для знака {sign} на русском языке.

СТРУКТУРА (видео {duration} секунд):
1. ХУК (0:00-0:03) — шок, тайна, предупреждение
2. ОСНОВНАЯ ЧАСТЬ — астрология с драмой  
3. ТРИГГЕР — почему нужно узнать больше
4. CTA — призыв перейти в бота: t.me/SuperAstro2027_bot?start=tiktok_{sign}1

ФОРМАТ ВЫВОДА (строго JSON):
[
  {{"time": "0:00-0:03", "text": "Овны, остановитесь!..", "video": "огненная вспышка, символ Овна"}},
  {{"time": "0:03-0:12", "text": "Марс предупреждает...", "video": "космос, планеты"}},
  ...
]

ТЕМА: {topic}
ЗНАК: {sign}
ДЛИНА: {duration} секунд

Используй триггеры: страх, любопытство, срочность, тайна.
Текст должен ЗАСТАВИТЬ перейти по ссылке в конце!"""

    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-70b-8192",
            temperature=0.8,
            max_tokens=1000
        )
        
        script_text = response.choices[0].message.content
        
        # Try to parse JSON
        try:
            # Find JSON in response
            start = script_text.find('[')
            end = script_text.rfind(']') + 1
            if start != -1 and end != 0:
                script_json = json.loads(script_text[start:end])
                return script_json
            else:
                # Fallback: return raw text
                return [{"time": "0:00-0:30", "text": script_text, "video": "generic"}]
        except:
            return [{"time": "0:00-0:30", "text": script_text, "video": "generic"}]
            
    except Exception as e:
        print(f"Error generating script: {e}")
        return None

def save_script(sign: str, script: list, duration: int = 30):
    """Save script to file"""
    os.makedirs("scripts", exist_ok=True)
    output_path = f"scripts/{sign}_{duration}s.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    
    print(f"[OK] Script saved: {output_path}")
    
    # Also save as readable text
    text_path = f"scripts/{sign}_{duration}s.txt"
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(f"=== СЦЕНАРИЙ ДЛЯ {sign.upper()} ({duration} сек) ===\n\n")
        for item in script:
            f.write(f"[{item['time']}] {item['text']}\n")
            f.write(f"Видео: {item['video']}\n\n")
    
    print(f"[OK] Text version: {text_path}")
    return output_path

def generate_all_scripts():
    """Generate scripts for all zodiac signs"""
    signs = ["aries", "taurus", "gemini", "cancer", "leo", "virgo", 
             "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"]
    
    for sign in signs:
        print(f"\n{'='*60}")
        print(f"Generating script for {sign.upper()}...")
        print(f"{'='*60}")
        
        script = generate_script(sign, duration=30)
        if script:
            save_script(sign, script, duration=30)
        else:
            print(f"[ERROR] Failed to generate script for {sign}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        sign = sys.argv[1]
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        print(f"Generating {duration}s script for {sign}...")
        script = generate_script(sign, duration=duration)
        if script:
            save_script(sign, script, duration=duration)
    else:
        print("Usage: python script_generator.py [sign] [duration]")
        print("Example: python script_generator.py aries 30")
        print("\nGenerating for Aries (30s)...")
        script = generate_script("aries", duration=30)
        if script:
            save_script("aries", script, duration=30)
