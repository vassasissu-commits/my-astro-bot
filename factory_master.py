from groq import Groq
from generate_images import save_images
from tts_batch import generate_tts
from video_assembly import assemble_video
import sys

GROQ_KEY = os.getenv("GROQ_KEY", "YOUR_FREE_GROQ_KEY")  # groq.com
SIGNS = ["aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"]

def get_horoscope(sign: str) -> str:
    """Generate short Russian horoscope via Groq (free tier)"""
    client = Groq(api_key=GROQ_KEY)
    res = client.chat.completions.create(
        messages=[{"role": "user", "content": f"Короткий гороскоп на сегодня для {sign} на русском, до 300 символов."}],
        model="llama3-70b-8192"
    )
    return res.choices[0].message.content

def run(sign: str, use_local_images: bool = False):
    """Run full pipeline for one sign"""
    print(f"\n{'='*50}")
    print(f"Processing {sign.upper()}...")
    print(f"{'='*50}")
    
    # 1. Generate horoscope (Russian)
    print("1. Generating horoscope...")
    horoscope = get_horoscope(sign)
    print(f"Horoscope: {horoscope[:50]}...")
    
    # 2. Get images (local or API)
    print("2. Getting images...")
    save_images(sign, use_local_first=use_local_images)
    
    # 3. Generate TTS (Piper, natural Russian)
    print("3. Generating TTS...")
    generate_tts(horoscope, sign)
    
    # 4. Assemble video with Ken Burns effect
    print("4. Assembling video...")
    assemble_video(sign, horoscope)
    
    print(f"✓ {sign.upper()} video ready!")

def test_mode():
    """Test pipeline with Aries only (1 image, 1 TTS, 1 video)"""
    print("TEST MODE: Generating 1 test video for Aries...")
    run("aries", use_local_images=False)  # Use API for test

if __name__ == "__main__":
    import os
    
    # Parse arguments
    if "--test" in sys.argv:
        test_mode()
    else:
        sign = sys.argv[1] if len(sys.argv) > 1 else "all"
        use_local = "--local" in sys.argv
        
        if sign == "all":
            for s in SIGNS:
                run(s, use_local_images=use_local)
        else:
            run(sign, use_local_images=use_local)