#!/bin/bash

# MiniWord Server Stop Script
echo "🛑 Stopping MiniWord server..."

# Find and kill any running http.server processes
echo "Looking for running servers..."
SERVER_PIDS=$(ps aux | grep "http.server" | grep -v grep | awk '{print $2}')

if [ -z "$SERVER_PIDS" ]; then
    echo "No MiniWord server found running."
else
    echo "Found server processes: $SERVER_PIDS"
    echo "Killing server processes..."
    kill $SERVER_PIDS
    sleep 2
    
    # Check if processes are still running
    REMAINING_PIDS=$(ps aux | grep "http.server" | grep -v grep | awk '{print $2}')
    if [ ! -z "$REMAINING_PIDS" ]; then
        echo "Force killing remaining processes..."
        kill -9 $REMAINING_PIDS
    fi
fi

# Check if port 8000 is free
echo "Checking port 8000..."
PORT_CHECK=$(netstat -tlnp | grep ":8000")
if [ -z "$PORT_CHECK" ]; then
    echo "✅ Port 8000 is now free"
else
    echo "⚠️  Port 8000 may still be in use:"
    echo "$PORT_CHECK"
fi

echo "🛑 MiniWord server stopped successfully!"
echo ""
echo "To start the server again, run: ./start.sh"
