import os
from moviepy.editor import *
from moviepy.video.fx import resize, pan

IMAGES_DIR = f"images/{sign}"
AUDIO_DIR = f"audio/{sign}"
MUSIC_PATH = "music/background.mp3"  # Free royalty-free
OUTPUT_DIR = f"videos/{sign}"
CLIP_DURATION = 5  # Seconds per image

def add_ken_burns(clip: ImageClip) -> ImageClip:
    return clip.fx(resize, lambda t: 1 + 0.1*t).fx(pan, lambda t: 0.1*t)

def assemble_video(sign: str, horoscope: str):
    os.makedirs(OUTPUT_DIR.format(sign=sign), exist_ok=True)
    images = sorted([f"{IMAGES_DIR.format(sign=sign)}/{img}" for img in os.listdir(IMAGES_DIR.format(sign=sign)) if img.endswith(".png")])
    clips = [add_ken_burns(ImageClip(img).set_duration(CLIP_DURATION)) for img in images]
    
    audio = AudioFileClip(f"{AUDIO_DIR.format(sign=sign)}/{sign}_horoscope.wav")
    music = AudioFileClip(MUSIC_PATH).volumex(0.3).set_duration(audio.duration)
    
    text = TextClip(horoscope, fontsize=30, color="white", size=(1080,1920), method="caption").set_duration(audio.duration).set_position(("center", "bottom"))
    
    final = CompositeVideoClip([concatenate_videoclips(clips), text]).set_audio(CompositeAudioClip([audio, music]))
    final.write_videofile(f"{OUTPUT_DIR.format(sign=sign)}/{sign}_video.mp4", fps=24)

if __name__ == "__main__":
    import sys
    sign = sys.argv[1] if len(sys.argv) > 1 else "aries"
    horoscope = sys.argv[2] if len(sys.argv) > 2 else "Сегодня отличный день для новых начинаний, Овны!"
    assemble_video(sign, horoscope)