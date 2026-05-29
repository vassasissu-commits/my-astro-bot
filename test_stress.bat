@echo off
chcp 65001 >nul
echo ==========================================================
echo  TEST STRESS MARKS IN SVETLANA TTS
echo  Testing '+' before stressed vowels
echo ==========================================================
echo.

echo [INFO] Generating test audio files...
python test_svetlana_stress.py

echo.
echo [INFO] Test files in tts_samples\ folder:
echo  - svetlana_normal.mp3 (normal text)
echo  - svetlana_stressed.mp3 (with '+' stress marks)
echo  - svetlana_ssml.mp3 (with SSML markup)
echo.
echo [INFO] Listen and choose the best version!
echo [INFO] If '+' works - add to texts in scripts\*_tts.txt
echo ==========================================================
pause