@echo off
chcp 65001 >nul
echo ==========================================================
echo  FULL PIPELINE FOR ONE ZODIAC SIGN
echo  1. Generate script
echo  2. Generate TTS audio (Svetlana)
echo  3. Instructions for next steps
echo ==========================================================
echo.

if "%1"=="" (
    set SIGN=aries
    echo [INFO] No sign specified, using Aries
) else (
    set SIGN=%1
)

echo [STEP 1/3] Generating script for %SIGN%...
call generate_sign.bat %SIGN%

echo.
echo [STEP 2/3] Generating TTS audio for %SIGN%...
call generate_tts.bat %SIGN%

echo.
echo [STEP 3/3] Done! Next steps:
echo  1. Take prompts from scripts\%SIGN%_15s_video_prompts.txt
echo  2. Generate videos in Luma/Pika (5 clips x 5s)
echo  3. Save videos to videos\%SIGN%\
echo  4. Edit in CapCut with audio from audio\%SIGN%\
echo.
echo ==========================================================
echo  RESULTS IN FOLDERS:
echo  - scripts\  (scripts and prompts)
echo  - audio\    (TTS audio)
echo  - videos\   (save generated videos here)
echo  - images\   (save images here)
echo ==========================================================
pause