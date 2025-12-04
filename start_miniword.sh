#!/bin/bash

# MiniWord startup script

echo "🚀 Starting MiniWord server..."
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python3 not found"
    exit 1
fi

# Enter project directory
cd "$(dirname "$0")"

# Check if port is occupied
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port occupied
    else
        return 1  # Port free
    fi
}

# Try different ports
PORT=8000
while check_port $PORT; do
    echo "⚠️  Port $PORT is occupied, trying port $((PORT+1))"
    PORT=$((PORT+1))
    if [ $PORT -gt 8100 ]; then
        echo "❌ Error: Cannot find available port"
        exit 1
    fi
done

echo "✅ Using port: $PORT"
echo ""

# Start server
echo "📡 Starting server..."
echo "🌐 Server address: http://localhost:$PORT"
echo "📁 Service directory: $(pwd)"
echo ""
echo "💡 Tips:"
echo "   • Open http://localhost:$PORT in browser to view interface"
echo "   • Press Ctrl+C to stop server"
echo "   • Server will run continuously until manually stopped"
echo ""
echo "=" * 60
echo ""

# Start server
python3 run_server.py $PORT
