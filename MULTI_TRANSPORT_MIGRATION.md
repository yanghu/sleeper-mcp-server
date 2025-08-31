# Multi-Transport Migration Guide

This document explains how to migrate from the Claude Desktop-only MCP server to the new multi-transport server that supports ADK and other agent platforms.

## What Changed

The original server was designed exclusively for Claude Desktop using the MCP protocol over stdio. The new multi-transport server adds:

1. **HTTP REST API endpoints** for agent platforms
2. **Multiple transport modes** (stdio, http, both)
3. **Simplified response formatting** for non-MCP clients
4. **Health check and monitoring endpoints**
5. **Batch tool execution** capabilities

## New Files

- `sleeper_mcp_server/multi_transport_server.py` - New multi-transport server
- `sleeper_mcp_server/__main__multi.py` - Entry point for multi-transport
- `scripts/start_server.py` - Easy startup script
- `examples/test_http_server.py` - HTTP endpoint testing
- `examples/agent_platform_configs.py` - Platform-specific configs
- `requirements-http.txt` - HTTP transport dependencies

## Migration Steps

### 1. Install New Dependencies

```bash
# Install HTTP transport dependencies
pip install -r requirements-http.txt

# Or install individually
pip install fastapi uvicorn[standard]
```

### 2. Choose Transport Mode

#### Option A: HTTP Only (for agent platforms)
```bash
python scripts/start_server.py --http
```

#### Option B: Both MCP and HTTP (hybrid)
```bash
python scripts/start_server.py --both
```

#### Option C: MCP Only (original behavior)
```bash
python scripts/start_server.py --stdio
# or just run the original server
python -m sleeper_mcp_server
```

### 3. Update Agent Platform Configurations

#### For ADK:
```python
from adk import Agent

agent = Agent(
    name="fantasy_football_agent",
    tools=[
        {
            "name": "sleeper_api",
            "type": "http",
            "base_url": "http://localhost:8000",
            "endpoints": {
                "list_tools": "/tools",
                "call_tool": "/tools/{tool_name}",
                "batch_call": "/tools/batch"
            }
        }
    ]
)
```

#### For LangChain:
```python
from langchain.tools import BaseTool
import requests

class SleeperTool(BaseTool):
    name = "sleeper_api"
    description = "Access to Sleeper Fantasy Football API"
    base_url = "http://localhost:8000"
    
    def _run(self, tool_name: str, arguments: dict):
        response = requests.post(
            f"{self.base_url}/tools/{tool_name}",
            json={"arguments": arguments}
        )
        return response.json()
```

### 4. Test the Setup

```bash
# Test HTTP endpoints
python examples/test_http_server.py

# Test with interactive mode
python examples/test_http_server.py --interactive
```

## API Endpoints

### HTTP Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Server health check |
| `/info` | GET | Server information and capabilities |
| `/tools` | GET | List available tools |
| `/tools/{tool_name}` | POST | Execute a specific tool |
| `/tools/batch` | POST | Execute multiple tools |

### Request Format

```json
{
  "arguments": {
    "username": "your_username",
    "season": "2024"
  }
}
```

### Response Format

```json
{
  "tool_name": "get_user_leagues",
  "result": [...],  // MCP format
  "mcp_format": [...],  // Full MCP response
  "simplified": {  // Simplified for agent platforms
    "content": "Formatted text content",
    "type": "text",
    "length": 1234,
    "raw_mcp": [...]
  }
}
```

## Environment Variables

```bash
# Transport configuration
export TRANSPORT_MODE="http"        # stdio, http, or both
export HTTP_HOST="0.0.0.0"          # HTTP server host
export HTTP_PORT="8000"              # HTTP server port
export LOG_LEVEL="INFO"              # Logging level

# Existing Sleeper API configuration
export SLEEPER_API_BASE_URL="https://api.sleeper.app/v1"
export CACHE_TTL_SECONDS="3600"
export MAX_RETRIES="3"
```

## Command Line Options

```bash
# Basic usage
python scripts/start_server.py --http

# Custom host and port
python scripts/start_server.py --http --host 127.0.0.1 --port 8080

# Both transport modes
python scripts/start_server.py --both

# Check dependencies
python scripts/start_server.py --check-deps

# Help
python scripts/start_server.py --help
```

## Docker Support

```yaml
# docker-compose.yml
version: '3.8'
services:
  sleeper-mcp-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - TRANSPORT_MODE=http
      - HTTP_HOST=0.0.0.0
      - HTTP_PORT=8000
    restart: unless-stopped
```

## Troubleshooting

### Common Issues

1. **Port already in use**: Change the port with `--port` or `HTTP_PORT` env var
2. **Dependencies missing**: Run `python scripts/start_server.py --check-deps`
3. **Permission denied**: Check if the port requires elevated privileges
4. **Connection refused**: Verify the server is running and accessible

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL="DEBUG"
python scripts/start_server.py --http

# Or use command line
python scripts/start_server.py --http --log-level DEBUG
```

### Health Checks

```bash
# Check server health
curl http://localhost:8000/health

# Get server info
curl http://localhost:8000/info

# List available tools
curl http://localhost:8000/tools
```

## Backward Compatibility

The original MCP server functionality is preserved:
- All existing tools work exactly the same
- MCP protocol over stdio is unchanged
- Claude Desktop configuration remains the same
- Existing tool implementations are reused

## Performance Considerations

- **HTTP mode**: Adds minimal overhead (~5-10ms per request)
- **Both modes**: Runs both servers concurrently
- **Caching**: Shared between transport modes
- **Rate limiting**: Applies to all transport modes

## Security Notes

- HTTP server runs on `0.0.0.0` by default (accessible from any IP)
- No authentication required for local development
- CORS enabled for web-based agents
- Consider firewall rules for production use

## Next Steps

1. Test the HTTP endpoints with your agent platform
2. Update your agent configurations
3. Monitor server performance and logs
4. Consider production deployment options
5. Explore additional transport protocols if needed

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the example configurations
3. Test with the provided test scripts
4. Check server logs for error details
