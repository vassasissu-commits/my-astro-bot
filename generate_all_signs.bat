@echo off
chcp 65001 >nul
echo ==========================================================
echo  GENERATE SCRIPTS FOR ALL 12 ZODIAC SIGNS
echo ==========================================================
echo.

set SIGNS=aries taurus gemini cancer leo virgo libra scorpio sagittarius capricorn aquarius pisces

for %%s in (%SIGNS%) do (
    echo [*] Generating for: %%s
    python auto_script_generator.py %%s
    echo.
)

echo ==========================================================
echo  DONE! All scripts in scripts\ folder
echo ==========================================================
pause