#!/bin/bash

# MiniWord Server Start Script
echo "🚀 Starting MiniWord server..."

# Navigate to MiniWord directory
cd /shared/nas/data/m1/jiateng5/Mini_Word

# Check if port 8000 is already in use
echo "Checking port 8000..."
PORT_CHECK=$(netstat -tlnp | grep ":8000")
if [ ! -z "$PORT_CHECK" ]; then
    echo "⚠️  Port 8000 is already in use:"
    echo "$PORT_CHECK"
    echo ""
    echo "Please run ./stop.sh first to stop the existing server."
    exit 1
fi

# Start the server
echo "Starting server on port 8000..."
python3 -m http.server 8000 --bind 0.0.0.0 &

# Wait a moment for server to start
sleep 3

# Check if server started successfully
SERVER_PID=$(ps aux | grep "http.server.*8000" | grep -v grep | awk '{print $2}')
if [ ! -z "$SERVER_PID" ]; then
    echo "✅ MiniWord server started successfully!"
    echo "📡 Server PID: $SERVER_PID"
    echo "🌐 Server URL: http://172.22.225.5:8000/index.html"
    echo "🌐 Local URL: http://localhost:8000/index.html"
    echo ""
    echo "📋 Available pages:"
    echo "   • Main interface: http://172.22.225.5:8000/index.html"
    echo "   • Test page: http://172.22.225.5:8000/test.html"
    echo ""
    echo "💡 Tips:"
    echo "   • Press Ctrl+F5 in browser to force refresh"
    echo "   • Run ./stop.sh to stop the server"
    echo "   • Server is running in background"
else
    echo "❌ Failed to start server"
    echo "Please check for any error messages above"
    exit 1
fi
