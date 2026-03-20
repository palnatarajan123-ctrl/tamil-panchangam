#!/bin/bash
echo "Starting TamilPanchangam..."

cd tamil_panchangam_engine
source .venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo "✅ Backend running at http://localhost:8000"
echo "✅ API docs at http://localhost:8000/docs"
echo "Press Ctrl+C to stop"

wait $BACKEND_PID
