#!/bin/bash
# Starts a local web server to serve the frontend dashboard
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

PORT=8000

echo "=========================================================="
echo "🚀 Redrob Matcher Engine: Starting Frontend Dashboard"
echo "=========================================================="
echo "Server starting on port $PORT..."
echo "Opening browser at: http://localhost:$PORT"
echo "Press Ctrl+C to stop the server."
echo "=========================================================="

# Try to open in default browser automatically after a short delay to allow port binding
(
    sleep 0.8
    if command -v xdg-open > /dev/null; then
        if command -v setsid > /dev/null; then
            setsid xdg-open "http://localhost:$PORT" >/dev/null 2>&1 &
        else
            xdg-open "http://localhost:$PORT" >/dev/null 2>&1 &
        fi
    elif command -v open > /dev/null; then
        open "http://localhost:$PORT" >/dev/null 2>&1
    fi
) &

# Run the custom python server
python3 serve.py
