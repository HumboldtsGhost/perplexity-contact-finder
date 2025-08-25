#!/usr/bin/env python3
"""
SUPER SIMPLE LAUNCHER - Just run this!
"""
import os
import sys
import subprocess

print("""
╔════════════════════════════════════════════════════╗
║     🚀 SMART CONTACT FINDER & TASK TRACKER 🚀      ║
╚════════════════════════════════════════════════════╝
""")

# Auto-install dependencies if needed
print("Checking dependencies...")
required = ['openai', 'anthropic', 'rich', 'questionary', 'pyfiglet', 'flask', 'flask-cors', 'openpyxl']
for module in required:
    try:
        __import__(module.replace('-', '_'))
    except ImportError:
        print(f"Installing {module}...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', module])

# Check for Anthropic API key
# Users should set their own API key

# Check Perplexity key
from config import Config
config = Config()

if not config.perplexity_api_key:
    print("\n⚠️  PERPLEXITY API KEY NEEDED!")
    print("Get one at: https://www.perplexity.ai/settings/api")
    key = input("\nPaste your Perplexity API key here: ").strip()
    if key:
        config.set_api_key('perplexity', key)
        config.save_to_file()
        print("✅ Saved!")

print("""
WHAT DO YOU WANT TO DO?

1️⃣  Find Contacts (Upload your schools CSV)
2️⃣  Task Tracker (Simple BDR todo list)
3️⃣  Exit
""")

choice = input("Enter 1, 2, or 3: ").strip()

if choice == '1':
    print("\n▶️  Starting Contact Finder...\n")
    import smart_contact_finder
    smart_contact_finder.main()
    
elif choice == '2':
    print("\n▶️  Starting Task Tracker...")
    print("📋 Opening http://localhost:5000")
    print("   (Press Ctrl+C to stop)\n")
    import webbrowser
    webbrowser.open('http://localhost:5000')
    subprocess.run([sys.executable, 'task_tracker.py'])
    
else:
    print("\n👋 Bye!")