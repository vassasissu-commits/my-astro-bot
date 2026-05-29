@echo off
chcp 65001 >nul
echo ==========================================================
echo  TEXT-TO-SPEECH (SVETLANA - Edge-TTS)
echo ==========================================================
echo.

if "%1"=="" (
    set SIGN=aries
    echo [INFO] No sign specified, using Aries
) else (
    set SIGN=%1
)

echo [INFO] Generating TTS for sign: %SIGN%
echo [INFO] Text from: scripts\%SIGN%_15s_tts.txt
echo.

if not exist "scripts\%SIGN%_15s_tts.txt" (
    echo [ERROR] File scripts\%SIGN%_15s_tts.txt not found!
    echo [INFO] Run generate_sign.bat %SIGN% first
    pause
    exit /b 1
)

echo [INFO] Starting TTS generation...
python tts_batch.py %SIGN% "Test audio for %SIGN%"

echo.
echo [INFO] Audio saved to: audio\%SIGN%\
echo [INFO] Voice used: ru-RU-SvetlanaNeural (Svetlana)
echo [INFO] To fix stress marks: add '+' before stressed vowel
echo ==========================================================
pause