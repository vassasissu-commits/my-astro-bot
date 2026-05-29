import os
import asyncio
from gtts import gTTS
import pyttsx3

os.makedirs("tts_samples", exist_ok=True)

test_text = "Сегодня отличный день для новых начинаний, Овны! Звезды благоволят вам."

print("Generating samples with different TTS engines...")
print("="*60)

# 1. gTTS (Google TTS - you said this is robotic)
print("1. Generating with gTTS (Google)...")
try:
    tts = gTTS(text=test_text, lang='ru')
    tts.save("tts_samples/gtts_google.mp3")
    print("   [OK] Saved: tts_samples/gtts_google.mp3")
    print("   NOTE: You said this is robotic - let's compare!")
except Exception as e:
    print(f"   [ERROR] gTTS failed: {e}")

# 2. pyttsx3 (offline, Windows SAPI5 voices)
print("\n2. Generating with pyttsx3 (offline Windows voices)...")
try:
    engine = pyttsx3.init()
    # List available voices
    voices = engine.getProperty('voices')
    print(f"   Available Windows voices: {len(voices)}")
    for idx, voice in enumerate(voices):
        if 'Russian' in voice.name or 'ru' in voice.id.lower():
            print(f"   - {voice.name} (Russian)")
            engine.setProperty('voice', voice.id)
            output_file = f"tts_samples/pyttsx3_{idx}.wav"
            engine.save_to_file(test_text, output_file)
            engine.runAndWait()
            print(f"     [OK] Saved: {output_file}")
            break
    else:
        print("   [INFO] No Russian voices found in pyttsx3")
except Exception as e:
    print(f"   [ERROR] pyttsx3 failed: {e}")

# 3. Show existing Edge-TTS samples
print("\n3. Edge-TTS (Microsoft Neural) samples already generated:")
print("   - tts_samples/Dmitry.mp3 (Male)")
print("   - tts_samples/Svetlana.mp3 (Female)")
print("   NOTE: This is NOT Google - it's Microsoft Neural (good quality!)")

print("\n" + "="*60)
print("ALL SAMPLES READY IN 'tts_samples' FOLDER")
print("Listen and choose the best one!")
print("="*60)