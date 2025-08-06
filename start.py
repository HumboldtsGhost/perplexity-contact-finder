#!/usr/bin/env python3
"""
Contact Finder Pro - Universal Launcher
Works on Mac, Linux, and Windows
Just double-click or run: python start.py
"""

import os
import sys
import subprocess
import time
import webbrowser
import platform
from pathlib import Path

def print_banner():
    """Print welcome banner"""
    print("=" * 50)
    print("   Contact Finder Pro - Web Interface")
    print("=" * 50)
    print()

def check_python():
    """Check Python version"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        print("   Download from: https://www.python.org/downloads/")
        input("\nPress Enter to exit...")
        sys.exit(1)
    print(f"✅ Python {version.major}.{version.minor} found")
    return True

def setup_venv():
    """Create and activate virtual environment"""
    venv_path = Path("venv")
    
    if not venv_path.exists():
        print("📦 Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✅ Virtual environment created")
    else:
        print("✅ Virtual environment found")
    
    # Get the correct Python executable from venv
    if platform.system() == "Windows":
        venv_python = venv_path / "Scripts" / "python.exe"
        venv_pip = venv_path / "Scripts" / "pip.exe"
    else:
        venv_python = venv_path / "bin" / "python"
        venv_pip = venv_path / "bin" / "pip"
    
    return str(venv_python), str(venv_pip)

def check_and_install_deps(venv_python, venv_pip):
    """Check and install dependencies"""
    print("\n📦 Checking dependencies...")
    
    # Check if FastAPI is installed
    try:
        subprocess.run(
            [venv_python, "-c", "import fastapi"],
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Dependencies already installed")
    except subprocess.CalledProcessError:
        print("📥 Installing required packages (this may take a minute)...")
        
        # Upgrade pip first
        subprocess.run(
            [venv_pip, "install", "--upgrade", "pip"],
            capture_output=True,
            text=True
        )
        
        # Install requirements
        result = subprocess.run(
            [venv_pip, "install", "-r", "requirements.txt"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ All packages installed!")
        else:
            print("❌ Error installing packages:")
            print(result.stderr)
            input("\nPress Enter to exit...")
            sys.exit(1)

def open_browser_delayed(url, delay=3):
    """Open browser after a delay"""
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except:
        pass  # Fail silently if browser can't be opened

def start_server(venv_python):
    """Start the FastAPI server"""
    print("\n" + "=" * 50)
    print("🚀 Starting Contact Finder Pro...")
    print("=" * 50)
    print()
    print("📌 Web interface: http://localhost:8000")
    print("📌 Press Ctrl+C to stop the server")
    print()
    print("=" * 50)
    print()
    
    # Start browser opening in a separate thread
    import threading
    browser_thread = threading.Thread(
        target=open_browser_delayed,
        args=("http://localhost:8000", 3)
    )
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        # Run the FastAPI app
        subprocess.run([venv_python, "api.py"], check=True)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error running server: {e}")
        input("\nPress Enter to exit...")

def main():
    """Main launcher function"""
    print_banner()
    
    # Check Python version
    check_python()
    
    # Setup virtual environment
    venv_python, venv_pip = setup_venv()
    
    # Install dependencies if needed
    check_and_install_deps(venv_python, venv_pip)
    
    # Start the server
    start_server(venv_python)

if __name__ == "__main__":
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    try:
        main()
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1)