import os
from moviepy.editor import *
from moviepy.video.fx import resize

def create_test_video():
    """Create test video for Aries with Ken Burns effect (even without real images)"""
    sign = "aries"
    output_dir = f"videos/{sign}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if we have images
    images_dir = f"images/{sign}"
    if not os.path.exists(images_dir) or not os.listdir(images_dir):
        print(f"No images in {images_dir}, creating test with colored clips...")
        # Create simple colored clips as placeholder
        clips = [
            ColorClip(size=(1080, 1920), color=(255, 100, 100), duration=3),  # Red
            ColorClip(size=(1080, 1920), color=(255, 150, 50), duration=3),   # Orange
            ColorClip(size=(1080, 1920), color=(255, 200, 0), duration=3),   # Yellow
        ]
    else:
        images = [f"{images_dir}/{img}" for img in os.listdir(images_dir) if img.endswith(('.png', '.jpg'))]
        clips = [ImageClip(img).set_duration(3).resize((1080, 1920)) for img in images[:5]]
    
    # Add Ken Burns effect (pan/zoom)
    def ken_burns(clip):
        return clip.fx(resize, lambda t: 1 + 0.05*t)
    
    clips_with_effect = [ken_burns(clip) for clip in clips]
    
    # Check audio
    audio_path = f"audio/{sign}/{sign}_horoscope.mp3"
    if os.path.exists(audio_path):
        audio = AudioFileClip(audio_path)
        final_duration = audio.duration
    else:
        print(f"No audio found at {audio_path}, using default duration")
        final_duration = sum(c.duration for c in clips_with_effect)
        audio = None
    
    # Concatenate clips
    video = concatenate_videoclips(clips_with_effect).set_duration(final_duration)
    
    # Add text overlay (horoscope text)
    text = TextClip("Овен: Сегодня отличный день!", fontsize=50, color='white', 
                    size=(1080, 200), method='caption').set_duration(final_duration).set_position(("center", "bottom"))
    
    final = CompositeVideoClip([video, text])
    
    if audio:
        final = final.set_audio(audio)
    
    # Add background music (if exists)
    music_path = "music/background.mp3"
    if os.path.exists(music_path):
        music = AudioFileClip(music_path).volumex(0.3).set_duration(final_duration)
        final_audio = CompositeAudioClip([final.audio, music])
        final = final.set_audio(final_audio)
    
    # Export
    output_path = f"{output_dir}/{sign}_test.mp4"
    final.write_videofile(output_path, fps=24, codec='libx264')
    print(f"[OK] Test video created: {output_path}")
    return output_path

if __name__ == "__main__":
    print("="*60)
    print("CREATING TEST VIDEO FOR ARIES")
    print("="*60)
    create_test_video()
    print("\nCheck videos/aries/ folder for the test video!")