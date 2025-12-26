@echo off
:loop
echo Starting BetHero Scraper...
"C:\Users\Alberto Tabera\AppData\Local\Microsoft\WindowsApps\python3.11.exe" "c:\Users\Alberto Tabera\.gemini\antigravity\scratch\bethero_scraper.py"
echo.
echo Scraper stopped or crashed. Restarting in 5 seconds...
echo Press Ctrl+C to stop completely.
timeout /t 5
goto loop
