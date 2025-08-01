@echo off
REM Perplexity Contact Finder - Easy Run Script for Windows

REM Activate virtual environment if it exists
if exist venv (
    call venv\Scripts\activate
) else (
    echo ERROR: Setup not complete! Please run setup.bat first
    pause
    exit /b 1
)

REM Clear the screen for a clean start
cls

REM Run the contact finder in interactive mode
python perplexity_contact_finder.py --interactive