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

# Try to open in default browser automatically
if command -v xdg-open > /dev/null; then
    xdg-open "http://localhost:$PORT" &
elif command -v open > /dev/null; then
    open "http://localhost:$PORT" &
fi

# Run the python http server
python3 -m http.server $PORT
