#!/bin/bash

echo "📋 Starting Task Tracker"
echo "========================"
echo ""
echo "⚠️  Remember: This is a minimal task tracker"
echo "No features will be added - it's meant to be disposable!"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
pip install -q flask flask-cors

echo "Starting Task Tracker on http://localhost:5000"
echo "Press Ctrl+C to stop"
echo ""

# Run the task tracker
python3 task_tracker.py

# Deactivate virtual environment when done
deactivate