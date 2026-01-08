#!/bin/bash

# =============================================================================
# DermaAI CKPA Backend API Test Script
# =============================================================================
# Tests all API endpoints to verify functionality

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

API_URL="${API_URL:-http://localhost:8000}"
PASSED=0
FAILED=0

echo "=================================="
echo "DermaAI CKPA API Test Suite"
echo "=================================="
echo "Testing API at: $API_URL"
echo ""

# Function to test endpoint
test_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local expected_status=$4
    local data=$5
    
    echo -n "Testing $name... "
    
    if [ "$method" == "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$API_URL$endpoint")
    elif [ "$method" == "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_URL$endpoint")
    fi
    
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$status_code" == "$expected_status" ]; then
        echo -e "${GREEN}✓ PASS${NC} (Status: $status_code)"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected: $expected_status, Got: $status_code)"
        echo "Response: $body"
        ((FAILED++))
        return 1
    fi
}

echo "1. Health Check Tests"
echo "─────────────────────"
test_endpoint "Basic Health Check" "GET" "/api/health" "200"
test_endpoint "Detailed Health Check" "GET" "/api/health/detailed" "200"
test_endpoint "Readiness Check" "GET" "/api/health/ready" "200"
test_endpoint "Liveness Check" "GET" "/api/health/live" "200"
echo ""

echo "2. Chat Endpoint Tests"
echo "─────────────────────"
test_endpoint "Chat Request" "POST" "/api/chat" "200" '{
    "question": "What is Plinest?",
    "conversation_id": "test_123",
    "history": []
}'
echo ""

echo "3. Root Endpoint Test"
echo "─────────────────────"
test_endpoint "Root Endpoint" "GET" "/" "200"
echo ""

echo "=================================="
echo "Test Results"
echo "=================================="
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
