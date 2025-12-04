#!/bin/bash

# MiniWord local server startup script

echo "Starting MiniWord local server..."
echo "Server address: http://localhost:8000"
echo "Press Ctrl+C to stop server"
echo ""

# Check if Python is available
if command -v python3 &> /dev/null; then
    echo "Starting server with Python3..."
    python3 -m http.server 8000
elif command -v python &> /dev/null; then
    echo "Starting server with Python2..."
    python -m SimpleHTTPServer 8000
else
    echo "Error: Python not found, please install Python or use other methods"
    echo ""
    echo "Other startup methods:"
    echo "1. Using Node.js: npx http-server -p 8000"
    echo "2. Using PHP: php -S localhost:8000"
    echo "3. Using other web servers"
fi
