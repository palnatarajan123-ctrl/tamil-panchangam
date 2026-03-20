#!/bin/bash
echo "Starting TamilPanchangam..."

# Kill anything already on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null
sleep 1

cd tamil_panchangam_engine
source .venv/bin/activate

# Start backend
python -m uvicorn app.main:app --host 0.0.0.0 \
  --port 8000 --reload &
BACKEND_PID=$!

echo "✅ Backend running at http://localhost:8000"
echo "✅ API docs at http://localhost:8000/docs"
echo "Press Ctrl+C to stop"

# Graceful shutdown on Ctrl+C
trap "echo ''; echo 'Stopping...'; \
  kill $BACKEND_PID 2>/dev/null; \
  echo 'Stopped.'; exit 0" SIGINT SIGTERM

wait $BACKEND_PID
