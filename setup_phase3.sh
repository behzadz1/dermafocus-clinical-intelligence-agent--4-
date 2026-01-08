#!/bin/bash
# Phase 3 Quick Setup Script
# Sets up Vector Database & Embeddings

set -e

echo "========================================"
echo "DermaAI CKPA - Phase 3 Setup"
echo "Vector Database & Embeddings"
echo "========================================"
echo ""

# Check if we're in backend directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: Please run this script from the backend directory"
    echo "   cd backend && ./setup_phase3.sh"
    exit 1
fi

# 1. Check API keys
echo "1. Checking API keys..."
if [ -f ".env" ]; then
    if grep -q "PINECONE_API_KEY=.*your.*" .env || ! grep -q "PINECONE_API_KEY" .env; then
        echo "⚠️  Pinecone API key not configured"
        echo "   Get key from: https://app.pinecone.io/"
        read -p "   Enter Pinecone API key (or press Enter to skip): " PINECONE_KEY
        if [ ! -z "$PINECONE_KEY" ]; then
            echo "PINECONE_API_KEY=$PINECONE_KEY" >> .env
            echo "✓ Pinecone API key added"
        fi
    else
        echo "✓ Pinecone API key configured"
    fi
    
    if grep -q "OPENAI_API_KEY=.*your.*" .env || ! grep -q "OPENAI_API_KEY" .env; then
        echo "⚠️  OpenAI API key not configured"
        echo "   Get key from: https://platform.openai.com/"
        read -p "   Enter OpenAI API key (or press Enter to skip): " OPENAI_KEY
        if [ ! -z "$OPENAI_KEY" ]; then
            echo "OPENAI_API_KEY=$OPENAI_KEY" >> .env
            echo "✓ OpenAI API key added"
        fi
    else
        echo "✓ OpenAI API key configured"
    fi
else
    echo "⚠️  No .env file found"
    echo "   Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✓ Created .env file - please edit with your API keys"
    else
        echo "❌ .env.example not found"
        exit 1
    fi
fi
echo ""

# 2. Install dependencies
echo "2. Installing Phase 3 dependencies..."
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "⚠️  Virtual environment not found"
    echo "   Creating venv..."
    python3 -m venv venv
    source venv/bin/activate
fi

pip install -q pinecone-client==3.0.0 openai==1.10.0
echo "✓ Dependencies installed"
echo ""

# 3. Check processed documents
echo "3. Checking for processed documents..."
if [ -d "data/processed" ]; then
    DOC_COUNT=$(ls data/processed/*.json 2>/dev/null | wc -l)
    echo "✓ Found $DOC_COUNT processed document(s)"
    
    if [ $DOC_COUNT -eq 0 ]; then
        echo "⚠️  No processed documents found"
        echo "   Process some documents first:"
        echo "   python3 scripts/process_manual_uploads.py"
    fi
else
    echo "⚠️  Processed directory not found"
    mkdir -p data/processed
fi
echo ""

# 4. Test API keys
echo "4. Testing API connections..."
python3 << 'EOF'
import os
import sys

errors = []

# Test Pinecone
try:
    from pinecone import Pinecone
    from app.config import settings
    pc = Pinecone(api_key=settings.pinecone_api_key)
    print("✓ Pinecone connection successful")
except Exception as e:
    print(f"✗ Pinecone connection failed: {str(e)[:60]}")
    errors.append("pinecone")

# Test OpenAI
try:
    from openai import OpenAI
    from app.config import settings
    client = OpenAI(api_key=settings.openai_api_key)
    print("✓ OpenAI connection successful")
except Exception as e:
    print(f"✗ OpenAI connection failed: {str(e)[:60]}")
    errors.append("openai")

if errors:
    print(f"\n⚠️  Some connections failed: {', '.join(errors)}")
    print("   Check your API keys in .env file")
    sys.exit(1)
EOF

echo ""

# 5. Instructions
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Start backend (if not running):"
echo "   ./quickstart.sh"
echo ""
echo "2. Upload vectors to Pinecone:"
echo "   python3 scripts/upload_vectors.py --verify"
echo ""
echo "3. Test semantic search:"
echo "   curl -X POST \"http://localhost:8000/api/search/semantic?query=skin%20treatment\""
echo ""
echo "See PHASE_3_COMPLETE.md for full documentation"
echo ""
