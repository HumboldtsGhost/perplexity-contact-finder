@echo off
REM Perplexity Contact Finder - Easy Setup Script for Windows

echo ============================================
echo    PERPLEXITY CONTACT FINDER SETUP    
echo ============================================
echo.
echo This will set up everything for you automatically!
echo Just sit back and relax...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed. Please install Python from https://www.python.org/downloads/
    echo        Make sure to check "Add Python to PATH" during installation!
    echo        After installing Python, run this script again.
    pause
    exit /b 1
)

echo Python found!
echo.

REM Create virtual environment
echo Creating virtual environment...
if exist venv (
    echo    Virtual environment already exists, skipping...
) else (
    python -m venv venv
    echo Virtual environment created!
)
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1

REM Install requirements
echo Installing required packages...
echo    This might take a minute...
pip install -r requirements.txt >nul 2>&1
echo All packages installed!
echo.

REM Check for config.json
if not exist config.json (
    echo API Key Setup
    echo    You'll need a Perplexity API key to use this tool.
    echo    Get one here: https://www.perplexity.ai/settings/api
    echo.
    set /p has_key="   Do you have your API key ready? (y/n): "
    
    if /i "%has_key%"=="y" (
        echo.
        set /p api_key="   Paste your Perplexity API key here: "
        
        REM Create config.json
        (
            echo {
            echo   "api_keys": {
            echo     "perplexity": "%api_key%"
            echo   },
            echo   "settings": {
            echo     "batch_size": 10,
            echo     "rate_limit_delay": 1.0,
            echo     "verify_emails": false,
            echo     "verify_phones": false
            echo   }
            echo }
        ) > config.json
        echo API key saved!
    ) else (
        echo.
        echo    No problem! You can add it later when you run the tool.
    )
) else (
    echo Configuration found!
)

echo.
echo ============================================
echo         SETUP COMPLETE!
echo ============================================
echo.
echo To start the Contact Finder, double-click:
echo.
echo    run.bat
echo.
echo ============================================
echo.
pause