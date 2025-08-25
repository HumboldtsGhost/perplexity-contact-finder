#!/usr/bin/env python3
"""
Simple Launcher - One script to run everything
"""
import os
import sys
import subprocess
from pathlib import Path

def check_dependencies():
    """Install any missing dependencies"""
    required = ['openai', 'anthropic', 'rich', 'questionary', 'pyfiglet', 'flask', 'flask-cors', 'openpyxl']
    missing = []
    
    for module in required:
        try:
            __import__(module.replace('-', '_'))
        except ImportError:
            missing.append(module)
    
    if missing:
        print(f"Installing missing dependencies: {', '.join(missing)}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q'] + missing)

def main():
    print("\n🚀 Contact Finder & Task Tracker System")
    print("=" * 50)
    
    # Check dependencies first
    check_dependencies()
    
    # Check for Anthropic API key
    # Users should set their own API key through environment or config
    
    # Check for Perplexity API key
    from config import Config
    config = Config()
    
    if not config.perplexity_api_key:
        print("\n⚠️  Perplexity API key not found!")
        print("Please set it:")
        print("  export PERPLEXITY_API_KEY='your-key-here'")
        print("\nGet your key at: https://www.perplexity.ai/settings/api")
        
        key = input("\nEnter your Perplexity API key (or press Enter to skip): ").strip()
        if key:
            os.environ['PERPLEXITY_API_KEY'] = key
            config.set_api_key('perplexity', key)
            config.save_to_file()
            print("✅ API key saved!")
    
    # Menu
    print("\nWhat would you like to do?")
    print("1. Find & Enrich Contacts (AI-powered)")
    print("2. Run Task Tracker (for BDRs)")
    print("3. Run Both (contacts then tracker)")
    print("4. Exit")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == '1':
        print("\n Starting Smart Contact Finder...")
        print("-" * 50)
        import smart_contact_finder
        smart_contact_finder.main()
        
    elif choice == '2':
        print("\n Starting Task Tracker...")
        print("-" * 50)
        print("Opening http://localhost:5000 in your browser...")
        print("Press Ctrl+C to stop the server\n")
        
        # Try to open browser
        import webbrowser
        webbrowser.open('http://localhost:5000')
        
        # Run task tracker
        subprocess.run([sys.executable, 'task_tracker.py'])
        
    elif choice == '3':
        print("\n Starting Smart Contact Finder first...")
        print("-" * 50)
        import smart_contact_finder
        smart_contact_finder.main()
        
        print("\n✅ Contact finding complete!")
        if input("\nStart Task Tracker now? (y/n): ").lower() == 'y':
            print("Opening http://localhost:5000...")
            import webbrowser
            webbrowser.open('http://localhost:5000')
            subprocess.run([sys.executable, 'task_tracker.py'])
    
    elif choice == '4':
        print("\n👋 Goodbye!")
        sys.exit(0)
    
    else:
        print("\n❌ Invalid choice")

if __name__ == "__main__":
    main()