import torch
import torchaudio
import os
import sys

# Skip trust prompt for Silero TTS
os.environ['TORCH_HUB_NO_TRUST_PROMPT'] = '1'

def generate_silero_samples():
    """Generate samples using Silero TTS (best Russian quality, free)"""
    os.makedirs("tts_samples", exist_ok=True)
    
    # Load Silero TTS model
    print("Loading Silero TTS model...")
    model, example_text = torch.hub.load(
        repo_or_dir='snakers4/silero-tts',
        model='silero_tts',
        language='ru',
        speaker='v3_1_ru',
        trust_repo=True  # Auto-trust the repository
    )
    
    test_text = "Сегодня отличный день для новых начинаний, Овны! Звезды благоволят вам."
    
    # Available Russian speakers in Silero v3
    speakers = ['aidar', 'baya', 'kseniya', 'irina', 'ruslan', 'alexey']
    
    for speaker in speakers:
        print(f"Generating sample for speaker: {speaker}")
        try:
            # Set speaker
            model.speaker = speaker
            # Generate audio
            audio = model.apply_tts(text=test_text, speaker=speaker, sample_rate=48000)
            # Save
            output_path = f"tts_samples/silero_{speaker}.wav"
            torchaudio.save(output_path, audio.unsqueeze(0), 48000)
            print(f"  Saved: {output_path}")
        except Exception as e:
            print(f"  Error with speaker {speaker}: {e}")
    
    print("\n✓ Silero TTS samples generated in 'tts_samples' folder")

if __name__ == "__main__":
    generate_silero_samples()