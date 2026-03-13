#!/bin/bash

echo "=================================="
echo "  FLY BRAIN WAVE CONSCIOUSNESS"
echo "=================================="
echo ""

echo "[1/3] Installing frontend dependencies..."
cd frontend
npm install

echo ""
echo "[2/3] Starting FastAPI backend server..."
cd ..
python3 server.py &
BACKEND_PID=$!

sleep 3

echo ""
echo "[3/3] Starting frontend development server..."
cd frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "=================================="
echo "  SYSTEM RUNNING"
echo "=================================="
echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT

wait
