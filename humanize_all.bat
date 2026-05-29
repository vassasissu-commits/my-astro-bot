@echo off
chcp 65001 >nul
echo =========================================================
echo  HUMANIZE ALL 12 ZODIAC SIGNS
echo  Makes texts emotional and selling
echo =========================================================
echo.

set SIGNS=aries taurus gemini cancer leo virgo libra scorpio sagittarius capricorn aquarius pisces

for %%s in (%SIGNS%) do (
    echo [*] Humanizing: %%s
    python text_humanizer_ru.py %%s
    echo.
)

echo =========================================================
echo  ALL DONE! Humanized scripts in scripts\ folder
echo =========================================================
pause