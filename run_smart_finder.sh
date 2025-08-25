#!/bin/bash

echo "🚀 Starting Smart Contact Finder with AI"
echo "==========================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo ""
echo "✅ Dependencies installed"
echo ""

# Check for config
if [ ! -f "config.json" ]; then
    echo "⚠️  No configuration found. The setup wizard will help you configure API keys."
    echo ""
fi

# Run the smart finder
echo "Starting Smart Contact Finder..."
echo "================================"
python3 smart_contact_finder.py

# Deactivate virtual environment when done
deactivate