# AI VIDEO FACTORY - BATCH FILES GUIDE

## What each .bat file does:

### 1. `generate_sign.bat` - Generate video scripts for ONE zodiac sign
**What it does:**
- Creates 4 files in `scripts/` folder for the sign you specify
- Example: `generate_sign.bat aries` creates:
  - `scripts/aries_15s.json` - Video structure (5 clips x 3s)
  - `scripts/aries_15s_tts.txt` - Text for Svetlana TTS (with stress marks `+`)
  - `scripts/aries_15s_video_prompts.txt` - Prompts for Luma/Pika (5s videos)
  - `scripts/aries_15s_image_prompts.txt` - Prompts for stock photos

**Usage:**
```batch
generate_sign.bat aries
generate_sign.bat taurus
generate_sign.bat gemini
```

---

### 2. `generate_all_signs.bat` - Generate scripts for ALL 12 zodiac signs
**What it does:**
- Runs `generate_sign.bat` for all 12 signs automatically
- Creates full script packages for: aries, taurus, gemini, cancer, leo, virgo, libra, scorpio, sagittarius, capricorn, aquarius, pisces

**Usage:**
```batch
generate_all_signs.bat
```

---

### 3. `generate_tts.bat` - Generate TTS audio with Svetlana
**What it does:**
- Uses Edge-TTS (Microsoft Svetlana voice) to generate audio
- Reads text from `scripts/{sign}_15s_tts.txt`
- Saves audio to `audio/{sign}/`

**Usage:**
```batch
generate_tts.bat aries
```

---

### 4. `full_pipeline.bat` - COMPLETE WORKFLOW for one sign
**What it does (3 steps):**
1. Generate scripts (calls `generate_sign.bat`)
2. Generate TTS audio (calls `generate_tts.bat`)
3. Shows instruction what to do next (Luma/Pika video generation)

**Usage:**
```batch
full_pipeline.bat aries
```

---

### 5. `test_stress.bat` - Test stress marks in Svetlana TTS
**What it does:**
- Generates 3 test audio files in `tts_samples/`
- Tests how stress marks (`+` before vowel) work
- Files created:
  - `svetlana_normal.mp3` - without stress marks
  - `svetlana_stressed.mp3` - with `+` stress marks
  - `svetlana_ssml.mp3` - with SSML markup

**Usage:**
```batch
test_stress.bat
```

---

## Folder Structure After Running:

```
my_astro_bot/
├── scripts/           # Generated scripts and prompts
│   ├── aries_15s.json
│   ├── aries_15s_tts.txt
│   ├── aries_15s_video_prompts.txt
│   └── ... (other signs)
├── audio/             # TTS audio files
│   └── aries/
│       └── aries_horoscope.mp3
├── videos/            # Put your generated videos here (from Luma/Pika)
│   └── aries/
│       ├── clip1.mp4
│       ├── clip2.mp4
│       └── ...
├── images/            # Stock photos or generated images
│   └── aries/
│       └── aries_pexels_0.jpg
└── tts_samples/       # TTS test files
    ├── svetlana_normal.mp3
    ├── svetlana_stressed.mp3
    └── svetlana_ssml.mp3
```

---

## Quick Start:

1. **Generate scripts for Aries:**
   ```batch
   generate_sign.bat aries
   ```

2. **Generate TTS audio:**
   ```batch
   generate_tts.bat aries
   ```

3. **Or do everything at once:**
   ```batch
   full_pipeline.bat aries
   ```

4. **Then:**
   - Copy prompts from `scripts/aries_15s_video_prompts.txt`
   - Paste into Luma/Pika to generate 5 video clips (5s each)
   - Save videos to `videos/aries/`
   - Edit in CapCut (free) with audio from `audio/aries/`
   - Export 1080x1920, 15 seconds
   - Upload to TikTok @aries_horoscope

---

## Stress Marks for Svetlana TTS:

To fix pronunciation, add `+` before stressed vowel:
- "началось" → "начА+лось"
- "сегодня" → "сегО+дня"
- "остановитесь" → "остановИ+тесь"

Edit the text files in `scripts/*_tts.txt` to add stress marks!
