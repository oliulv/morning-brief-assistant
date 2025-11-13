#!/bin/bash

# Test script for MCP server
# Usage: ./test-mcp.sh [local|deployed] [url]

MODE=${1:-local}
URL=${2:-http://localhost:3000/api/mcp}

if [ "$MODE" = "local" ]; then
  echo "Testing local MCP server at http://localhost:3000/api/mcp"
  echo "Make sure the server is running: npm run dev"
  echo ""
fi

echo "Testing MCP server at: $URL"
echo ""

# Test 1: List tools
echo "=== Test 1: List Tools ==="
curl -X POST "$URL" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/list",
    "params": {}
  }' | jq '.'
echo ""
echo ""

# Test 2: Call a simple tool (if you have env vars set)
echo "=== Test 2: Call get_calendar_events (requires GOOGLE_TOKEN_BASE64) ==="
echo "Skipping - requires environment variables"
echo ""
echo ""

echo "=== Test Complete ==="
echo ""
echo "To test with actual tools, set environment variables and call:"
echo "curl -X POST \"$URL\" -H \"Content-Type: application/json\" -d '{\"method\": \"tools/call\", \"params\": {\"name\": \"get_calendar_events\", \"arguments\": {\"time_min\": \"2024-01-01T00:00:00Z\", \"time_max\": \"2024-01-02T00:00:00Z\"}}}'"

