#!/bin/bash

echo "Starting Tamil Panchangam Engine..."

# Start the Python backend
echo "Starting backend on port 8000..."
cd tamil_panchangam_engine && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to be ready
sleep 3

# Start the frontend
echo "Starting frontend on port 5000..."
npx vite &
FRONTEND_PID=$!

# Handle shutdown
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
