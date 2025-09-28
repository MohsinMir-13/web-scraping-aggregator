#!/bin/bash
# Launch script for Web Scraping Aggregator

echo "🕷️ Web Scraping Aggregator"
echo "=========================="
echo ""

# Change to script directory
cd "$(dirname "$0")"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed or not in PATH"
    exit 1
fi

# Check if dependencies are installed
if ! python3 -c "import streamlit" &> /dev/null; then
    echo "📦 Installing dependencies..."
    pip3 install -r requirements.txt
    
    echo "🎭 Installing Playwright browsers..."
    python3 -m playwright install
fi

echo "🚀 Starting Web Scraping Aggregator..."
echo "🌐 Opening web interface at http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the application"
echo ""

# Launch Streamlit app
python3 -m streamlit run streamlit_app.py