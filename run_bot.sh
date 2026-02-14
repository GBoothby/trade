#!/bin/bash
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Starting Smart Trading Bot Backend..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000
