import os
import sys
import asyncio
import subprocess

# ========== CONFIGURATION ==========
# Choose TTS engine: "edge" (Microsoft, free, 2 Russian voices) or "piper" (open-source, better quality)
TTS_ENGINE = os.getenv("TTS_ENGINE", "edge")  # Change to "piper" after setup

# Edge-TTS voices (Microsoft Neural - NOT Google, good quality)
EDGE_VOICE_MALE = "ru-RU-DmitryNeural"
EDGE_VOICE_FEMALE = "ru-RU-SvetlanaNeural"

# Piper TTS (open-source, best natural Russian voices)
# Download: https://github.com/rhasspy/piper/releases
# Voice models: https://github.com/rhasspy/piper/releases/tag/v1.2.0
PIPER_PATH = os.getenv("PIPER_PATH", "./piper/piper.exe")
PIPER_VOICE_MODEL = os.getenv("PIPER_VOICE_MODEL", "./piper/ru_RU-irina-medium.onnx")

def get_output_dir(sign: str) -> str:
    return f"audio/{sign}"

def generate_tts_edge(text: str, sign: str, voice: str = None):
    """Generate TTS using Edge-TTS (Microsoft Neural Voices - free, good quality)"""
    output_dir = get_output_dir(sign)
    os.makedirs(output_dir, exist_ok=True)
    output_path = f"{output_dir}/{sign}_horoscope.mp3"
    
    # Use Svetlana (female) by default, or specified voice
    if voice is None:
        voice = EDGE_VOICE_FEMALE
    
    # FIX ACCENTS: Two methods supported
    # Method 1: Add '+' before stressed vowel (e.g., "начА+лось")
    # Method 2: Use SSML markup for precise control
    
    # Convert simple '+' notation to SSML if needed
    if '+' in text:
        # Simple conversion: replace "А+" with SSML stress markup
        import re
        # Surround text with SSML tags
        ssml_text = "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='ru-RU'>"
        # Add stress marks where '+' is found
        ssml_text += text.replace("+", "<break time='50ms'/>")
        ssml_text += "</speak>"
        text_to_use = ssml_text
    else:
        text_to_use = text
    
    async def _generate():
        import edge_tts
        communicate = edge_tts.Communicate(text_to_use, voice)
        await communicate.save(output_path)
    
    asyncio.run(_generate())
    print(f"[OK] Edge-TTS saved: {output_path} (voice: {voice})")
    print(f"     TIP: To add stress, put '+' before vowel: 'начА+лось'")
    print(f"     Or use SSML: <break time='50ms'/> for pauses")
    return output_path

def generate_tts_piper(text: str, sign: str):
    """Generate TTS using Piper (open-source, best Russian quality)"""
    output_dir = get_output_dir(sign)
    os.makedirs(output_dir, exist_ok=True)
    output_path = f"{output_dir}/{sign}_horoscope.wav"
    
    if not os.path.exists(PIPER_PATH):
        print(f"[ERROR] Piper not found at {PIPER_PATH}")
        print("Download from: https://github.com/rhasspy/piper/releases")
        return None
    
    if not os.path.exists(PIPER_VOICE_MODEL):
        print(f"[ERROR] Voice model not found at {PIPER_VOICE_MODEL}")
        print("Download from: https://github.com/rhasspy/piper/releases/tag/v1.2.0")
        return None
    
    process = subprocess.Popen(
        [PIPER_PATH, "--model", PIPER_VOICE_MODEL, "--output_file", output_path],
        stdin=subprocess.PIPE,
        text=True
    )
    process.communicate(input=text)
    
    print(f"[OK] Piper TTS saved: {output_path}")
    return output_path

def generate_tts(text: str, sign: str):
    """Main TTS function - uses engine specified in TTS_ENGINE"""
    if TTS_ENGINE == "piper":
        return generate_tts_piper(text, sign)
    else:  # Default to Edge-TTS
        return generate_tts_edge(text, sign)

if __name__ == "__main__":
    sign = sys.argv[1] if len(sys.argv) > 1 else "aries"
    text = sys.argv[2] if len(sys.argv) > 2 else "Сегодня отличный день для новых начинаний, Овны! Звезды благоволят вам."
    
    # Generate with both engines for comparison
    print("Generating with Edge-TTS (Microsoft Neural)...")
    generate_tts_edge(text, sign, EDGE_VOICE_FEMALE)
    generate_tts_edge(text, sign + "_male", EDGE_VOICE_MALE)
    
    if os.path.exists(PIPER_PATH):
        print("\nGenerating with Piper TTS...")
        generate_tts_piper(text, sign + "_piper")
    else:
        print("\nPiper TTS not found. Install from: https://github.com/rhasspy/piper/releases")
        print("Then set PIPER_PATH environment variable")