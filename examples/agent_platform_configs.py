"""
Example configurations for different agent platforms to integrate with the Sleeper MCP server.

This file contains sample configurations for various agent development frameworks
and platforms that can connect to the server via HTTP.
"""

# =============================================================================
# ADK (Agent Development Kit) Configuration
# =============================================================================

ADK_CONFIG = {
    "name": "fantasy_football_agent",
    "description": "Agent for fantasy football analysis using Sleeper API",
    "tools": [
        {
            "name": "sleeper_api",
            "type": "http",
            "description": "Access to Sleeper Fantasy Football API",
            "base_url": "http://localhost:8000",
            "endpoints": {
                "list_tools": "/tools",
                "call_tool": "/tools/{tool_name}",
                "batch_call": "/tools/batch",
                "health_check": "/health",
                "server_info": "/info"
            },
            "headers": {
                "Content-Type": "application/json"
            }
        }
    ],
    "config": {
        "max_concurrent_requests": 5,
        "request_timeout": 30,
        "retry_attempts": 3
    }
}

# =============================================================================
# LangChain Configuration
# =============================================================================

LANGCHAIN_CONFIG = {
    "tools": [
        {
            "name": "sleeper_api",
            "description": "Access to Sleeper Fantasy Football API",
            "base_url": "http://localhost:8000",
            "endpoints": {
                "list_tools": "/tools",
                "call_tool": "/tools/{tool_name}",
                "batch_call": "/tools/batch"
            }
        }
    ]
}

# Example LangChain tool implementation
LANGCHAIN_TOOL_IMPLEMENTATION = '''
from langchain.tools import BaseTool
import requests
from typing import Dict, Any

class SleeperTool(BaseTool):
    name = "sleeper_api"
    description = "Access to Sleeper Fantasy Football API for fantasy football data"
    base_url = "http://localhost:8000"
    
    def _run(self, tool_name: str, arguments: Dict[str, Any] = None) -> str:
        """Execute the tool synchronously."""
        if arguments is None:
            arguments = {}
        
        try:
            response = requests.post(
                f"{self.base_url}/tools/{tool_name}",
                json={"arguments": arguments},
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            # Return simplified content for LangChain
            return result.get("simplified", {}).get("content", str(result))
            
        except requests.exceptions.RequestException as e:
            return f"Error calling Sleeper API: {str(e)}"
    
    async def _arun(self, tool_name: str, arguments: Dict[str, Any] = None) -> str:
        """Execute the tool asynchronously."""
        import aiohttp
        
        if arguments is None:
            arguments = {}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/tools/{tool_name}",
                    json={"arguments": arguments},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return result.get("simplified", {}).get("content", str(result))
                    
        except Exception as e:
            return f"Error calling Sleeper API: {str(e)}"
'''

# =============================================================================
# AutoGen Configuration
# =============================================================================

AUTOGEN_CONFIG = {
    "llm_config": {
        "config_list": [
            {
                "model": "gpt-4",
                "api_key": "your-openai-api-key"
            }
        ]
    },
    "tools": [
        {
            "name": "sleeper_api",
            "description": "Access to Sleeper Fantasy Football API",
            "base_url": "http://localhost:8000",
            "endpoints": {
                "list_tools": "/tools",
                "call_tool": "/tools/{tool_name}",
                "batch_call": "/tools/batch"
            }
        }
    ]
}

# Example AutoGen tool implementation
AUTOGEN_TOOL_IMPLEMENTATION = '''
import autogen
import requests
from typing import Dict, Any

def sleeper_api_tool(tool_name: str, arguments: Dict[str, Any] = None) -> str:
    """Tool function for AutoGen to call Sleeper API."""
    if arguments is None:
        arguments = {}
    
    try:
        response = requests.post(
            f"http://localhost:8000/tools/{tool_name}",
            json={"arguments": arguments},
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get("simplified", {}).get("content", str(result))
        
    except requests.exceptions.RequestException as e:
        return f"Error calling Sleeper API: {str(e)}"

# Register the tool with AutoGen
autogen.register_tool(
    sleeper_api_tool,
    caller_name="user_proxy",
    executor_name="assistant",
    description="Access to Sleeper Fantasy Football API for fantasy football data"
)
'''

# =============================================================================
# CrewAI Configuration
# =============================================================================

CREWAI_CONFIG = {
    "tools": [
        {
            "name": "sleeper_api",
            "description": "Access to Sleeper Fantasy Football API",
            "base_url": "http://localhost:8000",
            "endpoints": {
                "list_tools": "/tools",
                "call_tool": "/tools/{tool_name}",
                "batch_call": "/tools/batch"
            }
        }
    ]
}

# Example CrewAI tool implementation
CREWAI_TOOL_IMPLEMENTATION = '''
from crewai import Tool
import requests
from typing import Dict, Any

class SleeperTool(Tool):
    name: str = "sleeper_api"
    description: str = "Access to Sleeper Fantasy Football API for fantasy football data"
    base_url: str = "http://localhost:8000"
    
    def _run(self, tool_name: str, arguments: Dict[str, Any] = None) -> str:
        """Execute the tool."""
        if arguments is None:
            arguments = {}
        
        try:
            response = requests.post(
                f"{self.base_url}/tools/{tool_name}",
                json={"arguments": arguments},
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("simplified", {}).get("content", str(result))
            
        except requests.exceptions.RequestException as e:
            return f"Error calling Sleeper API: {str(e)}"

# Create the tool instance
sleeper_tool = SleeperTool()
'''

# =============================================================================
# Custom Agent Framework Configuration
# =============================================================================

CUSTOM_AGENT_CONFIG = {
    "name": "fantasy_football_agent",
    "version": "1.0.0",
    "tools": [
        {
            "name": "sleeper_api",
            "type": "http_rest",
            "description": "Sleeper Fantasy Football API integration",
            "base_url": "http://localhost:8000",
            "endpoints": {
                "health": "/health",
                "info": "/info",
                "tools": "/tools",
                "call_tool": "/tools/{tool_name}",
                "batch": "/tools/batch"
            },
            "authentication": None,  # No auth required for local server
            "rate_limiting": {
                "requests_per_minute": 60,
                "burst_limit": 10
            },
            "error_handling": {
                "retry_attempts": 3,
                "backoff_factor": 2,
                "max_wait_time": 30
            }
        }
    ],
    "agent_config": {
        "max_concurrent_requests": 5,
        "request_timeout": 30,
        "log_level": "INFO",
        "enable_caching": True,
        "cache_ttl": 3600
    }
}

# =============================================================================
# Docker Compose Configuration
# =============================================================================

DOCKER_COMPOSE_CONFIG = '''
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
      - LOG_LEVEL=INFO
    volumes:
      - ./config:/app/config
    restart: unless-stopped
    
  # Example agent service
  fantasy-agent:
    image: python:3.11-slim
    working_dir: /app
    command: python agent.py
    environment:
      - SLEEPER_API_URL=http://sleeper-mcp-server:8000
    depends_on:
      - sleeper-mcp-server
    volumes:
      - ./agents:/app
    restart: unless-stopped
'''

# =============================================================================
# Environment Variables Configuration
# =============================================================================

ENVIRONMENT_CONFIG = '''
# Sleeper MCP Server Configuration
TRANSPORT_MODE=http                    # stdio, http, or both
HTTP_HOST=0.0.0.0                     # HTTP server host
HTTP_PORT=8000                         # HTTP server port
LOG_LEVEL=INFO                         # Logging level

# Sleeper API Configuration
SLEEPER_API_BASE_URL=https://api.sleeper.app/v1
CACHE_TTL_SECONDS=3600
MAX_RETRIES=3

# Agent Platform Configuration
AGENT_PLATFORM=adk                    # adk, langchain, autogen, crewai, custom
AGENT_NAME=fantasy_football_agent
AGENT_TIMEOUT=30
AGENT_MAX_RETRIES=3
'''

# =============================================================================
# Usage Examples
# =============================================================================

USAGE_EXAMPLES = '''
# Start the server in HTTP mode
python scripts/start_server.py --http

# Start the server in both modes
python scripts/start_server.py --both

# Test the HTTP endpoints
python examples/test_http_server.py

# Test with interactive mode
python examples/test_http_server.py --interactive

# Check dependencies
python scripts/start_server.py --check-deps

# Start with custom configuration
TRANSPORT_MODE=http HTTP_PORT=8080 python scripts/start_server.py
'''

if __name__ == "__main__":
    print("Sleeper MCP Server - Agent Platform Configuration Examples")
    print("=" * 60)
    print("\nAvailable configurations:")
    print("1. ADK Configuration")
    print("2. LangChain Configuration") 
    print("3. AutoGen Configuration")
    print("4. CrewAI Configuration")
    print("5. Custom Agent Framework Configuration")
    print("6. Docker Compose Configuration")
    print("7. Environment Variables Configuration")
    print("8. Usage Examples")
    
    print("\nTo use these configurations:")
    print("1. Copy the relevant configuration to your agent platform")
    print("2. Update the base_url if running on a different host/port")
    print("3. Start the server in HTTP mode: python scripts/start_server.py --http")
    print("4. Test the connection with: python examples/test_http_server.py")
