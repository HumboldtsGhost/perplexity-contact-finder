#!/usr/bin/env python3
"""
ONE CLICK WEB APP LAUNCHER
"""
import subprocess
import sys
import os

print("""
╔══════════════════════════════════════════════════════════╗
║   🚀 SMART CONTACT FINDER - WEB INTERFACE 🚀            ║
╚══════════════════════════════════════════════════════════╝
""")

# Install any missing dependencies
required = ['flask', 'flask-cors']
for module in required:
    try:
        __import__(module.replace('-', '_'))
    except ImportError:
        print(f"Installing {module}...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', module])

# Set API keys if configured
# Users should set their own API keys through the web interface

from config import Config
config = Config()

if not config.perplexity_api_key:
    print("\n⚠️  PERPLEXITY API KEY NEEDED!")
    print("Get one at: https://www.perplexity.ai/settings/api")
    key = input("\nPaste your key here: ").strip()
    if key:
        config.set_api_key('perplexity', key)
        config.save_to_file()

print("\n✅ Starting web app...")
print("🌐 Opening http://localhost:8000 in your browser...")
print("\nPress Ctrl+C to stop\n")

# Run the web app
subprocess.run([sys.executable, 'web_app.py'])