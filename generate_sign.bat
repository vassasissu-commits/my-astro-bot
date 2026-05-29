@echo off
chcp 65001 >nul
echo ===========================================================
echo  GENERATING VIDEO SCRIPT FOR ONE ZODIAC SIGN
echo  15 seconds = 5 clips x 3 seconds each
echo ===========================================================
echo.

if "%1"=="" (
    set SIGN=aries
    echo [INFO] No sign specified, using Aries
) else (
    set SIGN=%1
)

echo [INFO] Generating package for sign: %SIGN%
echo [INFO] Creating files:
echo   - scripts\%SIGN%_15s.json (structure)
echo   - scripts\%SIGN%_15s_tts.txt (text for Svetlana)
echo   - scripts\%SIGN%_15s_video_prompts.txt (prompts for Luma/Pika)
echo   - scripts\%SIGN%_15s_image_prompts.txt (prompts for images)
echo.

python auto_script_generator.py %SIGN%

echo.
echo ===========================================================
echo  DONE! Files in scripts\ folder
echo ===========================================================
pause