#!/bin/bash

# Perplexity Contact Finder - Easy Run Script

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Setup not complete! Please run ./setup.sh first"
    exit 1
fi

# Clear the screen for a clean start
clear

# Run the contact finder in interactive mode
python3 perplexity_contact_finder.py --interactive