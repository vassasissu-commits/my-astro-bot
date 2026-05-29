@echo off
chcp 65001 >nul
echo =========================================================
echo  RUSSIAN TEXT-HUMANIZER
echo  Makes text emotional and selling
echo  Style: 'Nastya's Wars' (astrological esoteric)
echo =========================================================
echo.

if "%1"=="" (
    set SIGN=aries
    echo [INFO] No sign specified, using Aries
) else (
    set SIGN=%1
)

echo [INFO] Humanizing text for: %SIGN%
echo [INFO] Adding emotional triggers and stress marks...
echo.

python text_humanizer_ru.py %SIGN%

echo.
echo =========================================================
echo  DONE! Humanized files in scripts\ folder:
echo =========================================================
echo  1. %SIGN%_15s_humanized.json (structure)
echo  2. %SIGN%_15s_tts_humanized.txt (for Svetlana TTS)
echo  3. %SIGN%_15s_comparison.txt (original vs humanized comparison)
echo.
echo [INFO] Check comparison file - see the difference!
echo =========================================================
pause