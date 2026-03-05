@echo off
echo ==============================================
echo =   Starting GeM Tender Scraper Locally     =
echo ==============================================
echo.

cd /d "%~dp0"

echo Activating virtual environment...
if exist "..\venv\Scripts\activate.bat" (
    call "..\venv\Scripts\activate.bat"
) else (
    echo [ERROR] Virtual environment not found at ..\venv
    pause
    exit /b
)

echo Starting Scraper Scheduler...
echo [INFO] Press Ctrl+C to stop.
echo.

python main.py

pause
