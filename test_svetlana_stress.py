import asyncio
import edge_tts
import os

async def test_stress_marks():
    """Test stress marks with Edge-TTS Svetlana voice"""
    os.makedirs("tts_samples", exist_ok=True)
    
    # Test 1: Normal text (might have wrong stress)
    text_normal = "Сегодня началось что-то интересное"
    
    # Test 2: With '+' before stressed vowel (our method)
    text_with_stress = "Сегодня начА+лось что-то интересное"
    
    # Test 3: With SSML break for emphasis
    text_ssml = """<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='ru-RU'>
        Сегодня <break time='100ms'/> начА+лось что-то интересное
    </speak>"""
    
    print("Testing Svetlana voice with different stress methods...")
    print("="*60)
    
    # Test normal
    print("1. Normal text (may have wrong stress)...")
    communicate = edge_tts.Communicate(text_normal, "ru-RU-SvetlanaNeural")
    await communicate.save("tts_samples/svetlana_normal.mp3")
    print("   Saved: tts_samples/svetlana_normal.mp3")
    
    # Test with '+' stress marker
    print("\n2. With '+' stress marker (начА+лось)...")
    communicate = edge_tts.Communicate(text_with_stress, "ru-RU-SvetlanaNeural")
    await communicate.save("tts_samples/svetlana_stressed.mp3")
    print("   Saved: tts_samples/svetlana_stressed.mp3")
    
    # Test with SSML
    print("\n3. With SSML markup...")
    try:
        communicate = edge_tts.Communicate(text_ssml, "ru-RU-SvetlanaNeural")
        await communicate.save("tts_samples/svetlana_ssml.mp3")
        print("   Saved: tts_samples/svetlana_ssml.mp3")
    except Exception as e:
        print(f"   SSML may not be supported: {e}")
    
    print("\n" + "="*60)
    print("LISTEN TO ALL THREE SAMPLES:")
    print("1. svetlana_normal.mp3 - might have wrong stress")
    print("2. svetlana_stressed.mp3 - with '+' marker")
    print("3. svetlana_ssml.mp3 - with SSML (if worked)")
    print("\nTIP: If '+' works, we'll use it in all horoscopes!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_stress_marks())