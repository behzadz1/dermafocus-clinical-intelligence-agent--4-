#!/bin/bash
# Start backend server using virtualenv Python
cd "$(dirname "$0")"
../.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
