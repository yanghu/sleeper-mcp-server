#!/bin/bash
# Simple curl-based testing script for Sleeper MCP Server

echo "🧪 Testing Sleeper MCP Server with curl commands"
echo "=================================================="

# Check if server is running
echo "1. Checking server health..."
curl -s http://localhost:8000/health | jq '.' 2>/dev/null || curl -s http://localhost:8000/health

echo -e "\n2. Getting server info..."
curl -s http://localhost:8000/info | jq '.' 2>/dev/null || curl -s http://localhost:8000/info

echo -e "\n3. Listing available tools..."
curl -s http://localhost:8000/tools | jq '.count' 2>/dev/null || curl -s http://localhost:8000/tools

echo -e "\n4. Testing get_user_leagues with huyang/2025..."
curl -s -X POST http://localhost:8000/tools/get_user_leagues \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"username": "huyang", "season": "2025"}}' | jq '.' 2>/dev/null || \
curl -s -X POST http://localhost:8000/tools/get_user_leagues \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"username": "huyang", "season": "2025"}}'

echo -e "\n5. Testing search_players for Patrick Mahomes..."
curl -s -X POST http://localhost:8000/tools/search_players \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"query": "Patrick Mahomes", "position": "QB"}}' | jq '.' 2>/dev/null || \
curl -s -X POST http://localhost:8000/tools/search_players \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"query": "Patrick Mahomes", "position": "QB"}}'

echo -e "\n6. Testing get_trending_players..."
curl -s -X POST http://localhost:8000/tools/get_trending_players \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"sport": "nfl", "add_drop": "add"}}' | jq '.' 2>/dev/null || \
curl -s -X POST http://localhost:8000/tools/get_trending_players \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"sport": "nfl", "add_drop": "add"}}'

echo -e "\n7. Testing batch tool calls..."
curl -s -X POST http://localhost:8000/tools/batch \
  -H "Content-Type: application/json" \
  -d '{
    "tool_calls": [
      {
        "name": "get_user_leagues",
        "arguments": {"username": "huyang", "season": "2025"}
      },
      {
        "name": "search_players", 
        "arguments": {"query": "Christian McCaffrey"}
      }
    ]
  }' | jq '.' 2>/dev/null || \
curl -s -X POST http://localhost:8000/tools/batch \
  -H "Content-Type: application/json" \
  -d '{
    "tool_calls": [
      {
        "name": "get_user_leagues",
        "arguments": {"username": "huyang", "season": "2025"}
      },
      {
        "name": "search_players", 
        "arguments": {"query": "Christian McCaffrey"}
      }
    ]
  }'

echo -e "\n✅ curl testing complete!"
echo -e "\n💡 Note: If you see 'jq: command not found', install jq for prettier output:"
echo "   sudo apt-get install jq  # Ubuntu/Debian"
echo "   brew install jq          # macOS"
