#!/usr/bin/env bash
set -e

echo "=== Jules Agent Local Setup ==="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed. Please install Python 3.10+."
    exit 1
fi

echo "Installing backend dependencies..."
python3 -m pip install -r backend/requirements.txt

echo "Running backend test suite..."
PYTHONPATH=. pytest backend/tests

echo "=== Setup Complete! ==="
echo "To start the Jules Agent server, run:"
echo "  uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"
echo "Then navigate to http://localhost:8000 in your browser."
