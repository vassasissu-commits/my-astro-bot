import asyncio
import edge_tts
import os

async def list_russian_voices():
    """List all available Russian voices in Edge-TTS"""
    voices = await edge_tts.list_voices()
    ru_voices = [v for v in voices if v['Locale'] == 'ru-RU']
    print("Available Russian voices in Edge-TTS:")
    print("="*60)
    for v in ru_voices:
        print(f"ShortName: {v['ShortName']}")
        print(f"  FriendlyName: {v['FriendlyName']}")
        print(f"  Gender: {v['Gender']}")
        print()
    return ru_voices

async def generate_samples():
    """Generate sample audio for each Russian voice"""
    os.makedirs("tts_samples", exist_ok=True)
    voices = await edge_tts.list_voices()
    ru_voices = [v for v in voices if v['Locale'] == 'ru-RU']
    
    test_text = "Сегодня отличный день для новых начинаний, Овны! Звезды благоволят вам."
    
    for voice in ru_voices:
        voice_name = voice['ShortName']
        output_file = f"tts_samples/{voice_name.replace('ru-RU-', '').replace('Neural', '')}.mp3"
        print(f"Generating sample: {voice_name}...")
        
        communicate = edge_tts.Communicate(test_text, voice_name)
        await communicate.save(output_file)
        print(f"  Saved: {output_file}")
    
    print("\n✓ All samples generated in 'tts_samples' folder")

if __name__ == "__main__":
    asyncio.run(list_russian_voices())
    print("\n" + "="*60)
    asyncio.run(generate_samples())