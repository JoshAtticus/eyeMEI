#!/bin/bash
set -e

# Function to handle shutdown gracefully
shutdown() {
    echo "Shutting down services..."
    kill -TERM $ADMIN_PID 2>/dev/null || true
    kill -TERM $MAIN_PID 2>/dev/null || true
    wait $ADMIN_PID 2>/dev/null || true
    wait $MAIN_PID 2>/dev/null || true
    exit 0
}

trap shutdown SIGTERM SIGINT

# Start the admin panel in the background
echo "Starting admin panel on port 5001..."
gunicorn --bind 0.0.0.0:5001 --workers 2 --timeout 120 --preload admin_panel:app &
ADMIN_PID=$!

# Give admin panel time to start
sleep 2

# Start the main application in the background
echo "Starting main application on port 5000..."
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 --preload wsgi:app &
MAIN_PID=$!

echo "Both services started successfully"
echo "Admin panel PID: $ADMIN_PID"
echo "Main app PID: $MAIN_PID"

# Wait for both processes
wait $ADMIN_PID $MAIN_PID
