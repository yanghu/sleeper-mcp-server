"""
Multi-transport MCP server for Sleeper Fantasy Football API.

This module provides both MCP stdio transport (for Claude Desktop) and HTTP REST API
(for ADK and other agent platforms) using the same underlying Sleeper API tools.
"""

import asyncio
import logging
import sys
import json
from typing import Any, Dict, List, Optional, Sequence
from pathlib import Path

# HTTP server dependencies
try:
    import uvicorn
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False
    logging.warning("FastAPI not available. HTTP transport will be disabled.")

# MCP dependencies
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel.server import NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
    EmbeddedResource,
)

from .sleeper_client import SleeperClient
from .cache import CacheManager
from .tools.league_tools import LeagueTools
from .tools.matchup_tools import MatchupTools
from .tools.trade_tools import TradeTools
from .tools.player_tools import PlayerTools

logger = logging.getLogger(__name__)


class MultiTransportSleeperServer:
    """Sleeper MCP server with support for multiple transport protocols."""
    
    def __init__(self, transport_mode: str = "stdio", http_host: str = "0.0.0.0", http_port: int = 8000):
        """Initialize the multi-transport server.
        
        Args:
            transport_mode: Transport mode - "stdio", "http", or "both"
            http_host: HTTP server host (default: "0.0.0.0")
            http_port: HTTP server port (default: 8000)
        """
        self.transport_mode = transport_mode
        self.http_host = http_host
        self.http_port = http_port
        
        # MCP server for stdio transport
        self.mcp_server = Server("sleeper-mcp-server")
        
        # HTTP server for agent platforms
        self.fastapi_app: Optional[FastAPI] = None
        
        # Core components
        self.client: Optional[SleeperClient] = None
        self.cache: Optional[CacheManager] = None
        self.league_tools: Optional[LeagueTools] = None
        self.matchup_tools: Optional[MatchupTools] = None
        self.trade_tools: Optional[TradeTools] = None
        self.player_tools: Optional[PlayerTools] = None
        
        # Register handlers
        self._register_mcp_handlers()
        
        # Setup HTTP server if needed
        if transport_mode in ["http", "both"] and HTTP_AVAILABLE:
            self._setup_http_server()
    
    def _register_mcp_handlers(self) -> None:
        """Register MCP protocol handlers for stdio transport."""
        
        @self.mcp_server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """Handle list_tools request from Claude Desktop."""
            return await self._list_tools()
        
        @self.mcp_server.call_tool()
        async def handle_call_tool(
            name: str, 
            arguments: Optional[Dict[str, Any]] = None
        ) -> List[TextContent | EmbeddedResource]:
            """Handle call_tool request from Claude Desktop."""
            return await self._call_tool(name, arguments or {})
    
    def _setup_http_server(self) -> None:
        """Setup FastAPI HTTP server for agent platform compatibility."""
        if not HTTP_AVAILABLE:
            logger.error("Cannot setup HTTP server: FastAPI not available")
            return
            
        self.fastapi_app = FastAPI(
            title="Sleeper MCP Server",
            description="MCP server providing access to Sleeper Fantasy Football API",
            version="0.1.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # Add CORS middleware for web-based agents
        self.fastapi_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Health check endpoint
        @self.fastapi_app.get("/health")
        async def health_check():
            return {"status": "healthy", "service": "sleeper-mcp-server"}
        
        # List tools endpoint
        @self.fastapi_app.get("/tools")
        async def list_tools():
            try:
                tools = await self._list_tools()
                return {"tools": tools, "count": len(tools)}
            except Exception as e:
                logger.error(f"Error listing tools: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Call tool endpoint
        @self.fastapi_app.post("/tools/{tool_name}")
        async def call_tool(tool_name: str, request: Request):
            try:
                body = await request.json()
                arguments = body.get("arguments", {})
                
                result = await self._call_tool(tool_name, arguments)
                
                # Return both MCP format and simplified format for agent platforms
                return {
                    "tool_name": tool_name,
                    "result": result,
                    "mcp_format": result,
                    "simplified": self._simplify_response(result)
                }
            except Exception as e:
                logger.error(f"Error calling tool {tool_name}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Batch tool calls endpoint
        @self.fastapi_app.post("/tools/batch")
        async def batch_call_tools(request: Request):
            try:
                body = await request.json()
                tool_calls = body.get("tool_calls", [])
                
                results = []
                for tool_call in tool_calls:
                    tool_name = tool_call.get("name")
                    arguments = tool_call.get("arguments", {})
                    
                    if not tool_name:
                        continue
                    
                    result = await self._call_tool(tool_name, arguments)
                    results.append({
                        "tool_name": tool_name,
                        "result": result,
                        "simplified": self._simplify_response(result)
                    })
                
                return {"results": results, "count": len(results)}
            except Exception as e:
                logger.error(f"Error in batch tool calls: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Server info endpoint
        @self.fastapi_app.get("/info")
        async def server_info():
            return {
                "name": "sleeper-mcp-server",
                "version": "0.1.0",
                "transport_modes": ["stdio", "http"],
                "current_mode": self.transport_mode,
                "capabilities": self.mcp_server.get_capabilities(
                    notification_options=NotificationOptions(
                        prompts_changed=False,
                        resources_changed=False,
                        tools_changed=False
                    ),
                    experimental_capabilities={}
                )
            }
    
    def _simplify_response(self, mcp_response: List[TextContent | EmbeddedResource]) -> Dict[str, Any]:
        """Convert MCP response to simplified format for agent platforms."""
        if not mcp_response:
            return {"content": "", "type": "empty"}
        
        # Extract text content
        text_content = []
        for item in mcp_response:
            if isinstance(item, TextContent):
                text_content.append(item.text)
            elif isinstance(item, EmbeddedResource):
                text_content.append(f"[Embedded Resource: {item.mimeType}]")
        
        combined_text = "\n".join(text_content)
        
        return {
            "content": combined_text,
            "type": "text",
            "length": len(combined_text),
            "raw_mcp": mcp_response
        }
    
    async def initialize(self) -> None:
        """Initialize server components."""
        try:
            # Initialize Sleeper API client
            self.client = SleeperClient()
            
            # Initialize cache manager
            self.cache = CacheManager()
            
            # Initialize tool handlers
            self.league_tools = LeagueTools(self.client, self.cache)
            self.matchup_tools = MatchupTools(self.client, self.cache)
            self.trade_tools = TradeTools(self.client, self.cache)
            self.player_tools = PlayerTools(self.client, self.cache)
            
            logger.info("Multi-transport Sleeper MCP Server initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize server: {e}")
            raise
    
    async def _list_tools(self) -> List[Tool]:
        """List all available MCP tools."""
        # This method should be implemented with the same tool definitions
        # as in the original server.py file
        # For brevity, I'm including a subset here
        tools = [
            Tool(
                name="get_user_leagues",
                description="Get all leagues for a username in a specific season",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "Sleeper username to look up"
                        },
                        "season": {
                            "type": "string",
                            "description": "Season year (default: '2024')",
                            "default": "2024"
                        }
                    },
                    "required": ["username"]
                }
            ),
            Tool(
                name="get_league_info",
                description="Get detailed information about a specific league",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "league_id": {
                            "type": "string",
                            "description": "League ID to retrieve information for"
                        }
                    },
                    "required": ["league_id"]
                }
            ),
            # Add more tools as needed...
        ]
        
        return tools
    
    async def _call_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent | EmbeddedResource]:
        """Execute a tool call and return formatted results."""
        try:
            # Ensure server is initialized
            if not self.client or not self.cache:
                await self.initialize()
            
            # Route tool calls to appropriate handlers
            result = await self._route_tool_call(name, arguments)
            
            # Format response for Claude Desktop
            return await self._format_response(name, result)
            
        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}")
            error_result = {
                "error": f"Tool execution failed: {str(e)}",
                "suggestions": [
                    "Check your input parameters",
                    "Try again in a few moments",
                    "Verify the Sleeper API is accessible"
                ]
            }
            return await self._format_response(name, error_result)
    
    async def _route_tool_call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route tool calls to the appropriate tool handler."""
        # This method should implement the same routing logic as the original server
        # For brevity, I'm including a basic structure
        if name == "get_user_leagues":
            return await self.league_tools.get_user_leagues(
                username=arguments["username"],
                season=arguments.get("season", "2024")
            )
        elif name == "get_league_info":
            return await self.league_tools.get_league_info(
                league_id=arguments["league_id"]
            )
        # Add more routing logic as needed...
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    async def _format_response(self, tool_name: str, result: Dict[str, Any]) -> List[TextContent]:
        """Format tool results for consumption."""
        # This method should implement the same formatting logic as the original server
        # For brevity, I'm including a basic structure
        try:
            if "error" in result:
                return [TextContent(
                    type="text",
                    text=f"Error: {result['error']}"
                )]
            
            # Format successful responses
            formatted_text = f"Tool {tool_name} executed successfully: {json.dumps(result, indent=2)}"
            
            return [TextContent(
                type="text",
                text=formatted_text
            )]
            
        except Exception as e:
            logger.error(f"Error formatting response for {tool_name}: {e}")
            return [TextContent(
                type="text",
                text=f"Error formatting response: {str(e)}"
            )]
    
    async def run(self) -> None:
        """Run the server with the specified transport mode."""
        # Initialize server components
        await self.initialize()
        
        if self.transport_mode == "stdio":
            # Run MCP server with stdio transport
            async with stdio_server() as (read_stream, write_stream):
                await self.mcp_server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="sleeper-mcp-server",
                        server_version="0.1.0",
                        capabilities=self.mcp_server.get_capabilities(
                            notification_options=NotificationOptions(
                                prompts_changed=False,
                                resources_changed=False,
                                tools_changed=False
                            ),
                            experimental_capabilities={}
                        )
                    )
                )
        
        elif self.transport_mode == "http":
            # Run HTTP server using uvicorn's async interface
            if not HTTP_AVAILABLE:
                logger.error("HTTP transport requested but FastAPI not available")
                sys.exit(1)
            
            logger.info(f"Starting HTTP server on {self.http_host}:{self.http_port}")
            
            # Use uvicorn's async interface instead of blocking run()
            config = uvicorn.Config(
                self.fastapi_app, 
                host=self.http_host, 
                port=self.http_port,
                log_level="info"
            )
            server = uvicorn.Server(config)
            await server.serve()
        
        elif self.transport_mode == "both":
            # Run both MCP and HTTP servers
            if not HTTP_AVAILABLE:
                logger.error("HTTP transport requested but FastAPI not available")
                sys.exit(1)
            
            # Start HTTP server in background
            logger.info(f"Starting HTTP server on {self.http_host}:{self.http_port}")
            http_config = uvicorn.Config(
                self.fastapi_app, 
                host=self.http_host, 
                port=self.http_port,
                log_level="info"
            )
            http_server = uvicorn.Server(http_config)
            
            # Run both servers concurrently
            async def run_both():
                http_task = asyncio.create_task(http_server.serve())
                mcp_task = asyncio.create_task(self._run_mcp_server())
                
                await asyncio.gather(http_task, mcp_task)
            
            await run_both()
        
        else:
            raise ValueError(f"Unsupported transport mode: {self.transport_mode}")
    
    async def _run_mcp_server(self):
        """Run MCP server with stdio transport."""
        async with stdio_server() as (read_stream, write_stream):
            await self.mcp_server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="sleeper-mcp-server",
                    server_version="0.1.0",
                    capabilities=self.mcp_server.get_capabilities(
                        notification_options=NotificationOptions(
                            prompts_changed=False,
                            resources_changed=False,
                            tools_changed=False
                        ),
                        experimental_capabilities={}
                    )
                )
            )


async def main() -> None:
    """Main entry point for the multi-transport server."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr
    )
    
    # Parse command line arguments
    transport_mode = "stdio"  # Default for Claude Desktop compatibility
    http_host = "0.0.0.0"
    http_port = 8000
    
    if len(sys.argv) > 1:
        transport_mode = sys.argv[1]
    
    if len(sys.argv) > 2:
        http_host = sys.argv[2]
    
    if len(sys.argv) > 3:
        try:
            http_port = int(sys.argv[3])
        except ValueError:
            logger.error(f"Invalid port number: {sys.argv[3]}")
            sys.exit(1)
    
    logger.info(f"Starting Multi-transport Sleeper MCP Server in {transport_mode} mode")
    if transport_mode in ["http", "both"]:
        logger.info(f"HTTP server will run on {http_host}:{http_port}")
    
    try:
        # Create and run server
        server = MultiTransportSleeperServer(
            transport_mode=transport_mode,
            http_host=http_host,
            http_port=http_port
        )
        await server.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

