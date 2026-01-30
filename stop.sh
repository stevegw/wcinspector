#!/bin/bash

PORT=${1:-8000}

echo "Stopping WCInspector on port $PORT..."

PID=$(lsof -ti:$PORT 2>/dev/null)
if [ ! -z "$PID" ]; then
    echo "Stopping process (PID: $PID)..."
    kill -9 $PID
    echo "Done."
else
    echo "No server running on port $PORT"
fi
