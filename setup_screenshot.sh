#!/bin/bash

echo "🎯 MiniWord Screenshot Tool Setup"
echo "================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

echo "✓ Python 3 found"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip3 first."
    exit 1
fi

echo "✓ pip3 found"

# Install required packages
echo "📦 Installing required packages..."
pip3 install -r requirements_screenshot.txt

# Check if Chrome is installed
if ! command -v google-chrome &> /dev/null && ! command -v chromium-browser &> /dev/null; then
    echo "⚠️  Chrome/Chromium not found. Please install Chrome or Chromium browser."
    echo "   Ubuntu/Debian: sudo apt-get install chromium-browser"
    echo "   Or download Chrome from: https://www.google.com/chrome/"
fi

# Make the script executable
chmod +x auto_screenshot_all_functions.py

echo "✅ Setup complete!"
echo ""
echo "🚀 To run the screenshot tool:"
echo "   1. Start your MiniWord server: python3 -m http.server 8000"
echo "   2. Run the screenshot tool: python3 auto_screenshot_all_functions.py"
echo ""
echo "📁 Screenshots will be saved in: function_screenshots/"
