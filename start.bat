@echo off
title Contact Finder Pro - Web Interface

echo =========================================
echo    Contact Finder Pro - Web Interface   
echo =========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed. Please install Python 3.8 or higher.
    echo Visit: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python found
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment found
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check and install dependencies
echo Checking dependencies...
python -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing required packages (this may take a minute)...
    pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt
    echo [OK] All packages installed!
) else (
    echo [OK] Dependencies already installed
)

echo.
echo =========================================
echo Starting Contact Finder Pro...
echo =========================================
echo.
echo Web interface will open at: http://localhost:8000
echo Press Ctrl+C to stop the server
echo.

REM Open browser after a delay
start /b cmd /c "timeout /t 3 >nul && start http://localhost:8000"

REM Start the application
python api.py

REM Deactivate virtual environment when done
call venv\Scripts\deactivate.bat
pause