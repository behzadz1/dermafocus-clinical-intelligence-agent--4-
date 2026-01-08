#!/bin/bash

# =============================================================================
# DermaAI CKPA Backend Setup Script
# =============================================================================
# This script helps you set up the backend environment

set -e  # Exit on error

echo "=================================="
echo "DermaAI CKPA Backend Setup"
echo "=================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "ℹ $1"
}

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.9"

if python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
    print_success "Python $python_version (OK)"
else
    print_error "Python 3.11+ required. Current: $python_version"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_success "Virtual environment exists"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate
print_success "Virtual environment activated"

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip -q
print_success "pip upgraded"

# Install dependencies
print_info "Installing dependencies (this may take a minute)..."
if pip install -r requirements.txt -q; then
    print_success "Dependencies installed"
else
    print_error "Failed to install dependencies"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found"
    echo ""
    read -p "Would you like to create .env from .env.example? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp .env.example .env
        print_success ".env file created"
        echo ""
        print_warning "IMPORTANT: Edit .env and add your API keys:"
        echo "  - ANTHROPIC_API_KEY"
        echo "  - PINECONE_API_KEY"
        echo "  - OPENAI_API_KEY"
        echo "  - SECRET_KEY (generate a random string)"
        echo ""
    fi
else
    print_success ".env file exists"
fi

# Create necessary directories
print_info "Creating data directories..."
mkdir -p data/uploads data/processed logs
print_success "Directories created"

# Test import
print_info "Testing imports..."
if python3 -c "from app.main import app" 2>/dev/null; then
    print_success "Import test passed"
else
    print_warning "Import test failed (this is OK if .env is not configured)"
fi

echo ""
echo "=================================="
print_success "Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Configure your .env file with API keys:"
echo "   nano .env"
echo ""
echo "2. Start the development server:"
echo "   source venv/bin/activate"
echo "   python3 -m app.main"
echo ""
echo "3. Or use uvicorn directly:"
echo "   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "4. Test the API:"
echo "   curl http://localhost:8000/api/health"
echo ""
echo "5. View API docs:"
echo "   http://localhost:8000/docs"
echo ""
