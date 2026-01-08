#!/bin/bash

# =============================================================================
# DermaAI CKPA - Quick Start Script
# =============================================================================
# This script gets you up and running in one command

set -e

echo "╔════════════════════════════════════════╗"
echo "║   DermaAI CKPA - Quick Start          ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Check if we're in the backend directory
if [ ! -f "app/main.py" ]; then
    echo "Error: Please run this script from the backend/ directory"
    exit 1
fi

# Run setup if venv doesn't exist
if [ ! -d "venv" ]; then
    echo "🔧 First-time setup detected. Running setup script..."
    echo ""
    ./setup.sh
    echo ""
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found"
    echo ""
    echo "Creating .env from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your API keys before the server will work fully"
    echo ""
    read -p "Press Enter to continue with placeholder keys (health checks will still work)..."
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

echo ""
echo "🚀 Starting server..."
echo ""
echo "Server will be available at:"
echo "  → API: http://localhost:8000"
echo "  → Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "─────────────────────────────────────────"
echo ""

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
