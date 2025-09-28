#!/usr/bin/env python3
"""
Main entry point for the Web Scraping Aggregator.

This script provides multiple ways to run the application:
1. Streamlit web interface (default)
2. Command-line interface
3. Example usage demonstration
"""
import sys
import subprocess
import argparse
from pathlib import Path

def run_streamlit_app():
    """Launch the Streamlit web application."""
    print("🕷️ Starting Web Scraping Aggregator...")
    print("🌐 Opening web interface at http://localhost:8501")
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "streamlit_app.py", 
            "--server.headless", "false",
            "--server.port", "8501"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start Streamlit: {e}")
        print("Make sure Streamlit is installed: pip install streamlit")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user")

def run_example():
    """Run the example usage script."""
    print("🕷️ Running example usage demonstration...")
    
    try:
        subprocess.run([sys.executable, "example_usage.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Example script failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Example stopped by user")

def run_tests():
    """Run system tests."""
    print("🕷️ Running system tests...")
    
    try:
        subprocess.run([sys.executable, "test_setup.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Tests failed: {e}")
        sys.exit(1)

def install_dependencies():
    """Install required dependencies."""
    print("📦 Installing dependencies...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "-r", "requirements.txt"
        ], check=True)
        print("✅ Dependencies installed successfully")
        
        # Install Playwright browsers
        print("🎭 Installing Playwright browsers...")
        subprocess.run([
            sys.executable, "-m", "playwright", "install"
        ], check=True)
        print("✅ Playwright browsers installed successfully")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e}")
        sys.exit(1)

def show_status():
    """Show application status and configuration."""
    print("🕷️ Web Scraping Aggregator - Status")
    print("=" * 50)
    
    # Check if key files exist
    key_files = [
        "streamlit_app.py",
        "requirements.txt",
        ".env.example",
        "config/settings.py",
        "core/orchestrator.py"
    ]
    
    print("📁 Key Files:")
    for file in key_files:
        if Path(file).exists():
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} (missing)")
    
    # Check if .env exists
    print(f"\n🔑 Configuration:")
    if Path(".env").exists():
        print("   ✅ .env file found")
    else:
        print("   ⚠️  .env file not found (using defaults)")
        print("   📝 Copy .env.example to .env and configure API keys")
    
    # Check if dependencies are installed
    print(f"\n📦 Dependencies:")
    try:
        import streamlit
        print("   ✅ Streamlit")
    except ImportError:
        print("   ❌ Streamlit (run: pip install streamlit)")
    
    try:
        import pandas
        print("   ✅ Pandas")
    except ImportError:
        print("   ❌ Pandas")
    
    try:
        import requests
        print("   ✅ Requests")
    except ImportError:
        print("   ❌ Requests")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Web Scraping Aggregator - Multi-source data collection tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Start Streamlit web interface (default)
  python main.py --mode web         # Start Streamlit web interface
  python main.py --mode example     # Run example usage script
  python main.py --mode test        # Run system tests
  python main.py --mode install     # Install dependencies
  python main.py --mode status      # Show application status
        """
    )
    
    parser.add_argument(
        "--mode", 
        choices=["web", "example", "test", "install", "status"],
        default="web",
        help="Operation mode (default: web)"
    )
    
    args = parser.parse_args()
    
    # Print banner
    print("🕷️ Web Scraping Aggregator")
    print("   Multi-source data collection and analysis tool")
    print("   Built with Python, Streamlit, and modern scraping techniques")
    print()
    
    # Route to appropriate function
    if args.mode == "web":
        run_streamlit_app()
    elif args.mode == "example":
        run_example()
    elif args.mode == "test":
        run_tests()
    elif args.mode == "install":
        install_dependencies()
    elif args.mode == "status":
        show_status()

if __name__ == "__main__":
    main()