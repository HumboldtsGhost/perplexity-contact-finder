#!/bin/bash

# Perplexity Contact Finder - Easy Setup Script
# This script sets up everything automatically!

echo "============================================"
echo "   🚀 PERPLEXITY CONTACT FINDER SETUP 🚀   "
echo "============================================"
echo ""
echo "This will set up everything for you automatically!"
echo "Just sit back and relax... ☕"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python from https://www.python.org/downloads/"
    echo "   After installing Python, run this script again."
    exit 1
fi

echo "✅ Python 3 found!"
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
if [ -d "venv" ]; then
    echo "   Virtual environment already exists, skipping..."
else
    python3 -m venv venv
    echo "✅ Virtual environment created!"
fi
echo ""

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "🔧 Upgrading pip..."
pip install --upgrade pip --quiet

# Install requirements
echo "📚 Installing required packages..."
echo "   This might take a minute..."
pip install -r requirements.txt --quiet
echo "✅ All packages installed!"
echo ""

# Check for Perplexity API key
if [ -z "$PERPLEXITY_API_KEY" ] && [ ! -f "config.json" ]; then
    echo "🔑 API Key Setup"
    echo "   You'll need a Perplexity API key to use this tool."
    echo "   Get one here: https://www.perplexity.ai/settings/api"
    echo ""
    read -p "   Do you have your API key ready? (y/n): " has_key
    
    if [ "$has_key" = "y" ] || [ "$has_key" = "Y" ]; then
        echo ""
        read -p "   Paste your Perplexity API key here: " api_key
        
        # Create config.json
        cat > config.json << EOF
{
  "api_keys": {
    "perplexity": "$api_key"
  },
  "settings": {
    "batch_size": 10,
    "rate_limit_delay": 1.0,
    "verify_emails": false,
    "verify_phones": false
  }
}
EOF
        echo "✅ API key saved!"
    else
        echo ""
        echo "   No problem! You can add it later when you run the tool."
    fi
else
    echo "✅ Configuration found!"
fi

echo ""
echo "============================================"
echo "        ✨ SETUP COMPLETE! ✨"
echo "============================================"
echo ""
echo "To start the Contact Finder, run:"
echo ""
echo "   ./run.sh"
echo ""
echo "Or if that doesn't work:"
echo ""
echo "   bash run.sh"
echo ""
echo "============================================"