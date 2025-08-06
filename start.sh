#!/bin/bash

# Contact Finder Pro - Easy Launcher for Mac/Linux
# Just double-click this file or run: ./start.sh

echo "========================================="
echo "   Contact Finder Pro - Web Interface   "
echo "========================================="
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    echo "Visit: https://www.python.org/downloads/"
    read -p "Press Enter to exit..."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"
echo ""

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment found"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
echo "📦 Checking dependencies..."
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📥 Installing required packages (this may take a minute)..."
    pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt
    echo "✅ All packages installed!"
else
    echo "✅ Dependencies already installed"
fi

echo ""
echo "🚀 Starting Contact Finder Pro..."
echo "========================================="
echo ""

# Function to open browser after delay
open_browser() {
    sleep 3
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        open http://localhost:8000
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v xdg-open &> /dev/null; then
            xdg-open http://localhost:8000
        elif command -v gnome-open &> /dev/null; then
            gnome-open http://localhost:8000
        fi
    fi
}

# Start browser opening in background
open_browser &

# Start the application
echo "📌 Web interface will open at: http://localhost:8000"
echo "📌 Press Ctrl+C to stop the server"
echo ""
echo "========================================="
echo ""

# Run the FastAPI app
python api.py

# Deactivate virtual environment when done
deactivate