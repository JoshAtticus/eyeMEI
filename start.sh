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

# Unset any existing GUNICORN_FD to prevent conflicts
unset GUNICORN_FD

# Start the admin panel in the background with isolated environment
echo "Starting admin panel on port 5001..."
env -i PATH="$PATH" HOME="$HOME" PYTHONUNBUFFERED=1 GUNICORN_PID=1 \
    gunicorn --bind 0.0.0.0:5001 --workers 2 --timeout 120 --preload admin_panel:app &
ADMIN_PID=$!

# Give admin panel time to start
sleep 3

# Start the main application in the background with isolated environment
echo "Starting main application on port 5000..."
env -i PATH="$PATH" HOME="$HOME" PYTHONUNBUFFERED=1 GUNICORN_PID=1 \
    gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 --preload wsgi:app &
MAIN_PID=$!

echo "Both services started successfully"
echo "Admin panel PID: $ADMIN_PID"
echo "Main app PID: $MAIN_PID"

# Wait for both processes
wait $ADMIN_PID $MAIN_PID
