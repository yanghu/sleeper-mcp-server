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
import datetime

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
        
        # Batch tool calls endpoint (MUST come before the dynamic tool_name route)
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
                    
                    # Get raw result from tool (before MCP formatting)
                    raw_result = await self._route_tool_call(tool_name, arguments)
                    
                    # Convert to structured JSON for HTTP clients
                    structured_result = self._structure_raw_result(tool_name, raw_result)
                    
                    # Check if the structured result is an error
                    is_success = "error" not in structured_result
                    
                    results.append({
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "success": is_success,
                        "result": structured_result if is_success else None,
                        "error": structured_result.get("error") if not is_success else None,
                        "timestamp": datetime.datetime.now().isoformat()
                    })
                
                return {"results": results, "count": len(results)}
            except Exception as e:
                logger.error(f"Error in batch tool calls: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Call tool endpoint (MUST come after specific routes like /tools/batch)
        @self.fastapi_app.post("/tools/{tool_name}")
        async def call_tool(tool_name: str, request: Request):
            try:
                body = await request.json()
                arguments = body.get("arguments", {})
                
                # Get raw result from tool (before MCP formatting)
                raw_result = await self._route_tool_call(tool_name, arguments)
                
                # Convert to structured JSON for HTTP clients (ADK, etc.)
                structured_result = self._structure_raw_result(tool_name, raw_result)
                
                # Check if the structured result is an error
                is_success = "error" not in structured_result
                
                return {
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "success": is_success,
                    "result": structured_result if is_success else None,
                    "error": structured_result.get("error") if not is_success else None,
                    "timestamp": datetime.datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"Error calling tool {tool_name}: {e}")
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
        tools = [
            # League Tools
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
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "username": {"type": "string"},
                        "season": {"type": "string"},
                        "leagues": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "name": {"type": "string"},
                                    "status": {"type": "string"},
                                    "teams": {"type": "integer"},
                                    "sport": {"type": "string"},
                                    "season": {"type": ["string", "null"]},
                                    "scoring_type": {"type": "string"},
                                    "roster_positions": {"type": "array"}
                                }
                            }
                        },
                        "total_leagues": {"type": "integer"}
                    }
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
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "league_id": {"type": "string"},
                        "name": {"type": "string"},
                        "season": {"type": "string"},
                        "status": {"type": "string"},
                        "sport": {"type": "string"},
                        "teams": {"type": "integer"},
                        "scoring_type": {"type": "string"},
                        "roster_positions": {"type": "array"},
                        "scoring_settings": {"type": "object"},
                        "trade_deadline": {"type": ["integer", "null"]},
                        "playoff_start_week": {"type": ["integer", "null"]},
                        "playoff_teams": {"type": ["integer", "null"]}
                    }
                }
            ),
            Tool(
                name="get_league_rosters",
                description="Get all team rosters in a league",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "league_id": {
                            "type": "string",
                            "description": "League ID to retrieve rosters for"
                        }
                    },
                    "required": ["league_id"]
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "league_id": {"type": "string"},
                        "rosters": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "roster_id": {"type": "integer"},
                                    "owner_id": {"type": "string"},
                                    "players": {"type": "array", "items": {"type": "string"}},
                                    "starters": {"type": "array", "items": {"type": "string"}},
                                    "reserve": {"type": "array", "items": {"type": "string"}},
                                    "taxi": {"type": "array", "items": {"type": "string"}},
                                    "wins": {"type": "integer"},
                                    "losses": {"type": "integer"},
                                    "ties": {"type": "integer"},
                                    "fpts": {"type": "number"},
                                    "fpts_against": {"type": "number"}
                                }
                            }
                        },
                        "total_rosters": {"type": "integer"}
                    }
                }
            ),
            Tool(
                name="get_league_rosters_with_draft_info",
                description="Get all team rosters in a league with draft position metadata for each player",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "league_id": {
                            "type": "string",
                            "description": "League ID to retrieve rosters for"
                        }
                    },
                    "required": ["league_id"]
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "league_id": {"type": "string"},
                        "draft_id": {"type": ["string", "null"]},
                        "draft_status": {"type": ["string", "null"]},
                        "rosters": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "roster_id": {"type": "integer"},
                                    "owner_id": {"type": "string"},
                                    "owner_name": {"type": "string"},
                                    "players": {"type": "array", "items": {"type": "string"}},
                                    "starters": {"type": "array", "items": {"type": "string"}},
                                    "reserve": {"type": "array", "items": {"type": "string"}},
                                    "taxi": {"type": "array", "items": {"type": "string"}},
                                    "metadata": {"type": "object"},
                                    "settings": {"type": "object"}
                                }
                            }
                        },
                        "total_rosters": {"type": "integer"}
                    }
                }
            ),
            Tool(
                name="get_league_users",
                description="Get all users/participants in a league",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "league_id": {
                            "type": "string",
                            "description": "League ID to retrieve users for"
                        }
                    },
                    "required": ["league_id"]
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "league_id": {"type": "string"},
                        "users": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "user_id": {"type": "string"},
                                    "username": {"type": "string"},
                                    "display_name": {"type": ["string", "null"]},
                                    "avatar": {"type": ["string", "null"]},
                                    "is_owner": {"type": "boolean"}
                                }
                            }
                        },
                        "total_users": {"type": "integer"}
                    }
                }
            ),
            Tool(
                name="get_roster_user_mapping",
                description="Get a clear mapping of roster IDs to user names for a league",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "league_id": {
                            "type": "string",
                            "description": "League ID to get roster-user mapping for"
                        }
                    },
                    "required": ["league_id"]
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "league_id": {"type": "string"},
                        "mappings": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "roster_id": {"type": "integer"},
                                    "user_id": {"type": "string"},
                                    "user_name": {"type": "string"},
                                    "avatar": {"type": ["string", "null"]}
                                }
                            }
                        },
                        "total_mappings": {"type": "integer"}
                    }
                }
            ),
            Tool(
                name="get_league_draft",
                description="Get draft results and pick information for a league",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "league_id": {
                            "type": "string",
                            "description": "League ID to get draft information for"
                        }
                    },
                    "required": ["league_id"]
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "league_id": {"type": "string"},
                        "draft_id": {"type": ["string", "null"]},
                        "draft_status": {"type": ["string", "null"]},
                        "draft_type": {"type": ["string", "null"]},
                        "draft_order": {"type": "array", "items": {"type": "integer"}},
                        "picks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "pick_no": {"type": "integer"},
                                    "round": {"type": "integer"},
                                    "roster_id": {"type": "integer"},
                                    "player_id": {"type": "string"},
                                    "player_name": {"type": ["string", "null"]},
                                    "position": {"type": ["string", "null"]},
                                    "team": {"type": ["string", "null"]},
                                    "is_keeper": {"type": "boolean"},
                                    "keeper_for_team": {"type": ["string", "null"]},
                                    "draft_slot": {"type": ["integer", "null"]}
                                }
                            }
                        },
                        "total_picks": {"type": "integer"}
                    }
                }
            ),
            
            # Player Tools
            Tool(
                name="search_players",
                description="Search for players by name with optional position filtering",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Player name or partial name to search for"
                        },
                        "position": {
                            "type": "string",
                            "description": "Optional position filter (QB, RB, WR, TE, K, DEF)",
                            "enum": ["QB", "RB", "WR", "TE", "K", "DEF"]
                        }
                    },
                    "required": ["query"]
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "position": {"type": ["string", "null"]},
                        "players": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "name": {"type": "string"},
                                    "position": {"type": ["string", "null"]},
                                    "team": {"type": ["string", "null"]},
                                    "status": {"type": "string"},
                                    "search_rank": {"type": ["number", "null"]},
                                    "fantasy_positions": {"type": "array"}
                                }
                            }
                        },
                        "total_players": {"type": "integer"}
                    }
                }
            ),
            Tool(
                name="get_trending_players",
                description="Get trending players (most added/dropped)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sport": {
                            "type": "string",
                            "description": "Sport type (default: 'nfl')",
                            "default": "nfl"
                        },
                        "add_drop": {
                            "type": "string",
                            "description": "Type of trend - 'add' or 'drop' (default: 'add')",
                            "enum": ["add", "drop"],
                            "default": "add"
                        }
                    }
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "sport": {"type": "string"},
                        "add_drop": {"type": "string"},
                        "players": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "name": {"type": "string"},
                                    "position": {"type": ["string", "null"]},
                                    "team": {"type": ["string", "null"]},
                                    "status": {"type": ["string", "null"]},
                                    "trend_direction": {"type": ["string", "null"]},
                                    "trend_reason": {"type": ["string", "null"]}
                                }
                            }
                        },
                        "total_players": {"type": "integer"}
                    }
                }
            ),
            Tool(
                name="get_player_stats",
                description="Get player statistics for a specific season",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "player_id": {
                            "type": "string",
                            "description": "Player ID to get stats for"
                        },
                        "season": {
                            "type": "string",
                            "description": "Season year (default: '2024')",
                            "default": "2024"
                        }
                    },
                    "required": ["player_id"]
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "player_id": {"type": "string"},
                        "player_name": {"type": ["string", "null"]},
                        "position": {"type": ["string", "null"]},
                        "team": {"type": ["string", "null"]},
                        "season": {"type": "string"},
                        "stats": {
                            "type": "object",
                            "additionalProperties": {"type": ["number", "null"]}
                        },
                        "total_stats": {"type": "integer"}
                    }
                }
            ),
            
            # Matchup Tools
            Tool(
                name="get_matchups",
                description="Get matchups for a specific week in a league",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "league_id": {
                            "type": "string",
                            "description": "League ID to retrieve matchups for"
                        },
                        "week": {
                            "type": "integer",
                            "description": "Week number (1-22)",
                            "minimum": 1,
                            "maximum": 22
                        }
                    },
                    "required": ["league_id", "week"]
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "league_id": {"type": "string"},
                        "week": {"type": "integer"},
                        "matchups": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "matchup_id": {"type": ["integer", "null"]},
                                    "roster_id": {"type": "integer"},
                                    "points": {"type": ["number", "null"]},
                                    "players": {"type": "array", "items": {"type": "string"}},
                                    "starters": {"type": "array", "items": {"type": "string"}},
                                    "reserve": {"type": "array", "items": {"type": "string"}},
                                    "taxi": {"type": "array", "items": {"type": "string"}}
                                }
                            }
                        },
                        "total_matchups": {"type": "integer"}
                    }
                }
            ),
            Tool(
                name="get_matchup_scores",
                description="Get real-time scoring information for matchups in a specific week",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "league_id": {
                            "type": "string",
                            "description": "League ID to retrieve scores for"
                        },
                        "week": {
                            "type": "integer",
                            "description": "Week number (1-22)",
                            "minimum": 1,
                            "maximum": 22
                        }
                    },
                    "required": ["league_id", "week"]
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "league_id": {"type": "string"},
                        "week": {"type": "integer"},
                        "matchups": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "matchup_id": {"type": ["integer", "null"]},
                                    "roster_id": {"type": "integer"},
                                    "points": {"type": ["number", "null"]},
                                    "starters_points": {"type": "number"},
                                    "bench_points": {"type": "number"}
                                }
                            }
                        },
                        "total_matchups": {"type": "integer"}
                    }
                }
            ),
            
            # Trade Tools
            Tool(
                name="analyze_trade_targets",
                description="Analyze potential trade targets for a roster based on positional needs",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "league_id": {
                            "type": "string",
                            "description": "League ID to analyze"
                        },
                        "roster_id": {
                            "type": "integer",
                            "description": "Roster ID requesting trade analysis"
                        },
                        "position": {
                            "type": "string",
                            "description": "Optional position to focus analysis on (QB, RB, WR, TE, K, DEF)",
                            "enum": ["QB", "RB", "WR", "TE", "K", "DEF"]
                        }
                    },
                    "required": ["league_id", "roster_id"]
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "league_id": {"type": "string"},
                        "roster_id": {"type": "integer"},
                        "position": {"type": ["string", "null"]},
                        "target_teams": {"type": "array", "items": {"type": "object"}},
                        "suggested_trades": {"type": "array", "items": {"type": "object"}},
                        "positional_needs": {"type": "object"},
                        "trade_value_analysis": {"type": "object"}
                    }
                }
            ),
            Tool(
                name="evaluate_roster_needs",
                description="Evaluate roster strengths and weaknesses across all positions",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "league_id": {
                            "type": "string",
                            "description": "League ID to analyze"
                        },
                        "roster_id": {
                            "type": "integer",
                            "description": "Roster ID to evaluate"
                        }
                    },
                    "required": ["league_id", "roster_id"]
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "league_id": {"type": "string"},
                        "roster_id": {"type": "integer"},
                        "strengths": {"type": "array", "items": {"type": "string"}},
                        "weaknesses": {"type": "array", "items": {"type": "string"}},
                        "recommendations": {"type": "array", "items": {"type": "string"}},
                        "positional_analysis": {"type": "object"},
                        "overall_grade": {"type": "string"}
                    }
                }
            )
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
        # League Tools
        if name == "get_user_leagues":
            return await self.league_tools.get_user_leagues(
                username=arguments["username"],
                season=arguments.get("season", "2024")
            )
        elif name == "get_league_info":
            return await self.league_tools.get_league_info(
                league_id=arguments["league_id"]
            )
        elif name == "get_league_rosters":
            return await self.league_tools.get_league_rosters(
                league_id=arguments["league_id"]
            )
        elif name == "get_league_rosters_with_draft_info":
            return await self.league_tools.get_league_rosters_with_draft_info(
                league_id=arguments["league_id"]
            )
        elif name == "get_league_users":
            return await self.league_tools.get_league_users(
                league_id=arguments["league_id"]
            )
        elif name == "get_roster_user_mapping":
            return await self.league_tools.get_roster_user_mapping(
                league_id=arguments["league_id"]
            )
        elif name == "get_league_draft":
            return await self.league_tools.get_league_draft(
                league_id=arguments["league_id"]
            )
        
        # Player Tools
        elif name == "search_players":
            return await self.player_tools.search_players(
                query=arguments["query"],
                position=arguments.get("position")
            )
        elif name == "get_trending_players":
            return await self.player_tools.get_trending_players(
                sport=arguments.get("sport", "nfl"),
                add_drop=arguments.get("add_drop", "add")
            )
        elif name == "get_player_stats":
            return await self.player_tools.get_player_stats(
                player_id=arguments["player_id"],
                season=arguments.get("season", "2024")
            )
        
        # Matchup Tools
        elif name == "get_matchups":
            return await self.matchup_tools.get_matchups(
                league_id=arguments["league_id"],
                week=arguments["week"]
            )
        elif name == "get_matchup_scores":
            return await self.matchup_tools.get_matchup_scores(
                league_id=arguments["league_id"],
                week=arguments["week"]
            )
        
        # Trade Tools
        elif name == "analyze_trade_targets":
            return await self.trade_tools.analyze_trade_targets(
                league_id=arguments["league_id"],
                roster_id=arguments["roster_id"],
                position=arguments.get("position")
            )
        elif name == "evaluate_roster_needs":
            return await self.trade_tools.evaluate_roster_needs(
                league_id=arguments["league_id"],
                roster_id=arguments["roster_id"]
            )
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    async def _format_response(self, tool_name: str, result: Dict[str, Any]) -> List[TextContent]:
        """Format tool results for consumption."""
        try:
            # Check if result contains an error
            if "error" in result:
                return [TextContent(
                    type="text",
                    text=self._format_error_response(tool_name, result)
                )]
            
            # Format successful responses based on tool type
            formatted_text = await self._format_success_response(tool_name, result)
            
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
    
    def _format_error_response(self, tool_name: str, result: Dict[str, Any]) -> str:
        """Format error responses in a user-friendly way."""
        error_msg = result.get("error", "Unknown error occurred")
        suggestions = result.get("suggestions", [])
        retry_after = result.get("retry_after")
        
        formatted = f"❌ **{tool_name} Error**\n\n{error_msg}"
        
        if suggestions:
            formatted += "\n\n**Suggestions:**\n"
            for suggestion in suggestions:
                formatted += f"• {suggestion}\n"
        
        if retry_after:
            formatted += f"\n⏱️ Please wait {retry_after} seconds before retrying."
        
        return formatted
    
    async def _format_success_response(self, tool_name: str, result: Dict[str, Any]) -> str:
        """Format successful responses based on tool type."""
        if tool_name == "get_user_leagues":
            return self._format_user_leagues_response(result)
        elif tool_name == "get_league_info":
            return self._format_league_info_response(result)
        elif tool_name == "get_league_rosters":
            return self._format_league_rosters_response(result)
        elif tool_name == "get_league_rosters_with_draft_info":
            return self._format_league_rosters_with_draft_response(result)
        elif tool_name == "get_league_users":
            return self._format_league_users_response(result)
        elif tool_name == "get_roster_user_mapping":
            return self._format_roster_user_mapping_response(result)
        elif tool_name == "get_league_draft":
            return self._format_league_draft_response(result)
        elif tool_name == "search_players":
            return self._format_search_players_response(result)
        elif tool_name == "get_trending_players":
            return self._format_trending_players_response(result)
        elif tool_name == "get_player_stats":
            return self._format_player_stats_response(result)
        elif tool_name == "get_matchups":
            return self._format_matchups_response(result)
        elif tool_name == "get_matchup_scores":
            return self._format_matchup_scores_response(result)
        elif tool_name == "analyze_trade_targets":
            return self._format_trade_analysis_response(result)
        elif tool_name == "evaluate_roster_needs":
            return self._format_roster_evaluation_response(result)
        else:
            # Fallback to JSON representation
            import json
            return f"**{tool_name} Result:**\n```json\n{json.dumps(result, indent=2)}\n```"
    
    def _format_user_leagues_response(self, result: Dict[str, Any]) -> str:
        """Format user leagues response."""
        username = result.get("username", "Unknown")
        season = result.get("season", "Unknown")
        leagues = result.get("leagues", [])
        
        formatted = f"🏈 **Leagues for {username} ({season} season)**\n\n"
        
        if not leagues:
            formatted += "No leagues found for this user."
            return formatted
        
        for i, league in enumerate(leagues, 1):
            formatted += f"**{i}. {league['name']}**\n"
            formatted += f"   • League ID: `{league['id']}`\n"
            formatted += f"   • Status: {league['status'].replace('_', ' ').title()}\n"
            formatted += f"   • Teams: {league['teams']}\n"
            formatted += f"   • Sport: {league['sport'].upper()}\n\n"
        
        return formatted
    
    def _format_league_info_response(self, result: Dict[str, Any]) -> str:
        """Format league info response."""
        name = result.get("name", "Unknown League")
        league_id = result.get("league_id", "Unknown")
        status = result.get("status", "unknown").replace("_", " ").title()
        season = result.get("season", "Unknown")
        total_rosters = result.get("teams", 0)
        settings = result.get("settings", {})
        
        formatted = f"🏆 **{name}**\n\n"
        formatted += f"**League Details:**\n"
        formatted += f"• ID: `{league_id}`\n"
        formatted += f"• Season: {season}\n"
        formatted += f"• Status: {status}\n"
        formatted += f"• Teams: {total_rosters}\n\n"
        
        if settings:
            formatted += f"**League Settings:**\n"
            formatted += f"• Playoff Teams: {settings.get('playoff_teams', 'N/A')}\n"
            formatted += f"• Waiver Type: {settings.get('waiver_type', 'N/A')}\n"
            formatted += f"• Reserve Slots: {settings.get('reserve_slots', 0)}\n"
            formatted += f"• Taxi Slots: {settings.get('taxi_slots', 0)}\n\n"
        
        roster_positions = result.get("roster_positions", [])
        if roster_positions:
            formatted += f"**Roster Positions:** {', '.join(roster_positions)}\n"
        
        return formatted
    
    def _format_league_rosters_response(self, result: Dict[str, Any]) -> str:
        """Format league rosters response."""
        league_id = result.get("league_id", "Unknown")
        rosters = result.get("rosters", [])
        
        formatted = f"👥 **Rosters for League {league_id}**\n\n"
        
        if not rosters:
            formatted += "No rosters found in this league."
            return formatted
        
        for roster in rosters:
            roster_id = roster.get("roster_id", "Unknown")
            owner_info = roster.get("owner_info", {})
            players = roster.get("players", [])
            starters = roster.get("starters", [])
            
            # Get the best available name for the owner
            display_name = owner_info.get("display_name")
            username = owner_info.get("username")
            is_league_owner = owner_info.get("is_owner", False)
            
            if display_name and display_name != f"User {roster.get('owner_id')}":
                owner_text = display_name
                if username:
                    owner_text += f" (@{username})"
            elif username:
                owner_text = f"@{username}"
            else:
                owner_text = f"User {roster.get('owner_id', 'Unknown')}"
            
            if is_league_owner:
                owner_text += " 👑"
            
            formatted += f"**Roster {roster_id}** - {owner_text}\n"
            
            # Show player counts
            player_count = roster.get("player_count", len(players))
            starter_count = roster.get("starter_count", len(starters))
            formatted += f"• Total Players: {player_count}\n"
            formatted += f"• Starters: {starter_count}\n"
            formatted += f"• Bench: {player_count - starter_count}\n"
            
            # Show starting lineup with player names
            if starters and len(starters) > 0:
                formatted += f"\n**Starting Lineup:**\n"
                for starter in starters[:10]:  # Limit to first 10 to avoid too much text
                    player_info = starter.get("player_info", {})
                    player_name = player_info.get("full_name", f"Player {starter.get('player_id', 'Unknown')}")
                    position = player_info.get("position", "")
                    team = player_info.get("team", "")
                    
                    player_display = player_name
                    if position:
                        player_display += f" ({position}"
                        if team:
                            player_display += f", {team}"
                        player_display += ")"
                    
                    formatted += f"  • {player_display}\n"
                
                if len(starters) > 10:
                    formatted += f"  • ... and {len(starters) - 10} more\n"
            
            formatted += "\n"
        
        return formatted
    
    def _format_league_rosters_with_draft_response(self, result: Dict[str, Any]) -> str:
        """Format league rosters with draft info response."""
        league_id = result.get("league_id", "Unknown")
        rosters = result.get("rosters", [])
        draft_available = result.get("draft_available", False)
        total_drafted = result.get("total_drafted_players", 0)
        
        formatted = f"🏈 **Rosters with Draft Info for League {league_id}**\n\n"
        
        if draft_available:
            formatted += f"📊 **Draft Summary**: {total_drafted} players drafted\n\n"
        else:
            formatted += "⚠️ **No draft data available for this league**\n\n"
        
        if not rosters:
            formatted += "No rosters found in this league."
            return formatted
        
        for roster in rosters:
            roster_id = roster.get("roster_id", "Unknown")
            owner_info = roster.get("owner_info", {})
            players = roster.get("players", [])
            starters = roster.get("starters", [])
            drafted_count = roster.get("drafted_players", 0)
            fa_count = roster.get("free_agent_pickups", 0)
            
            # Get the best available name for the owner
            display_name = owner_info.get("display_name")
            username = owner_info.get("username")
            is_league_owner = owner_info.get("is_owner", False)
            
            if display_name and display_name != f"User {roster.get('owner_id')}":
                owner_text = display_name
                if username:
                    owner_text += f" (@{username})"
            elif username:
                owner_text = f"@{username}"
            else:
                owner_text = f"User {roster.get('owner_id', 'Unknown')}"
            
            if is_league_owner:
                owner_text += " 👑"
            
            formatted += f"**Roster {roster_id}** - {owner_text}\n"
            
            # Show player counts with draft info
            player_count = roster.get("player_count", len(players))
            starter_count = roster.get("starter_count", len(starters))
            formatted += f"• Total Players: {player_count}\n"
            formatted += f"• Starters: {starter_count}\n"
            formatted += f"• Bench: {player_count - starter_count}\n"
            
            if draft_available:
                formatted += f"• Drafted Players: {drafted_count}\n"
                formatted += f"• Free Agent Pickups: {fa_count}\n"
            
            # Show starting lineup with player names and draft info
            if starters and len(starters) > 0:
                formatted += f"\n**Starting Lineup:**\n"
                for starter in starters[:10]:  # Limit to first 10 to avoid too much text
                    player_info = starter.get("player_info", {})
                    player_name = player_info.get("full_name", f"Player {starter.get('player_id', 'Unknown')}")
                    position = player_info.get("position", "")
                    team = player_info.get("team", "")
                    draft_info = player_info.get("draft_info")
                    acquisition_type = player_info.get("acquisition_type", "unknown")
                    
                    player_display = player_name
                    if position:
                        player_display += f" ({position}"
                        if team:
                            player_display += f", {team}"
                        player_display += ")"
                    
                    # Add draft information
                    if draft_info:
                        round_num = draft_info.get("round")
                        pick_no = draft_info.get("pick_no")
                        is_keeper = draft_info.get("is_keeper", False)
                        drafted_by_name = draft_info.get("drafted_by_name", "Unknown")
                        keeper_text = " 🔒" if is_keeper else ""
                        player_display += f" - Round {round_num}, Pick {pick_no} ({drafted_by_name}){keeper_text}"
                    elif acquisition_type == "free_agent":
                        player_display += " - Free Agent"
                    
                    formatted += f"  • {player_display}\n"
                
                if len(starters) > 10:
                    formatted += f"  • ... and {len(starters) - 10} more\n"
            
            # Show some bench players with draft info
            bench_players = [p for p in players if p not in starters]
            if bench_players and len(bench_players) > 0:
                formatted += f"\n**Key Bench Players:**\n"
                for bench_player in bench_players[:5]:  # Show first 5 bench players
                    player_info = bench_player.get("player_info", {})
                    player_name = player_info.get("full_name", f"Player {bench_player.get('player_id', 'Unknown')}")
                    position = player_info.get("position", "")
                    team = bench_player.get("team", "")
                    draft_info = player_info.get("draft_info")
                    acquisition_type = player_info.get("acquisition_type", "unknown")
                    
                    player_display = player_name
                    if position:
                        player_display += f" ({position}"
                        if team:
                            player_display += f", {team}"
                        player_display += ")"
                    
                    # Add draft information
                    if draft_info:
                        round_num = draft_info.get("round")
                        pick_no = draft_info.get("pick_no")
                        is_keeper = draft_info.get("is_keeper", False)
                        drafted_by_name = draft_info.get("drafted_by_name", "Unknown")
                        keeper_text = " 🔒" if is_keeper else ""
                        player_display += f" - Round {round_num}, Pick {pick_no} ({drafted_by_name}){keeper_text}"
                    elif acquisition_type == "free_agent":
                        player_display += " - Free Agent"
                    
                    formatted += f"  • {player_display}\n"
                
                if len(bench_players) > 5:
                    formatted += f"  • ... and {len(bench_players) - 5} more bench players\n"
            
            formatted += "\n"
        
        return formatted
    
    def _format_league_users_response(self, result: Dict[str, Any]) -> str:
        """Format league users response."""
        league_id = result.get("league_id", "Unknown")
        users = result.get("users", [])
        
        formatted = f"👤 **Users in League {league_id}**\n\n"
        
        if not users:
            formatted += "No users found in this league."
            return formatted
        
        for user in users:
            username = user.get("username", "Unknown")
            display_name = user.get("display_name", "Unknown")
            is_owner = user.get("is_owner", False)
            
            formatted += f"**{display_name}** (@{username})"
            if is_owner:
                formatted += " 👑 *League Owner*"
            formatted += "\n"
        
        return formatted
    
    def _format_roster_user_mapping_response(self, result: Dict[str, Any]) -> str:
        """Format roster-user mapping response."""
        league_id = result.get("league_id", "Unknown")
        roster_count = result.get("roster_count", 0)
        roster_mapping = result.get("roster_user_mapping", [])
        
        formatted = f"🔗 **Roster-User Mapping for League {league_id}**\n\n"
        
        if not roster_mapping:
            formatted += "No roster-user mapping found for this league."
            return formatted
        
        formatted += f"**{roster_count} Teams:**\n\n"
        
        for mapping in roster_mapping:
            roster_id = mapping.get("roster_id", "Unknown")
            user_info = mapping.get("user_info", {})
            player_count = mapping.get("player_count", 0)
            starter_count = mapping.get("starter_count", 0)
            
            # Get the best available name for the owner
            display_name = user_info.get("display_name")
            username = user_info.get("username")
            is_league_owner = user_info.get("is_owner", False)
            
            if display_name and display_name != f"User {mapping.get('owner_id')}":
                owner_text = display_name
                if username:
                    owner_text += f" (@{username})"
            elif username:
                owner_text = f"@{username}"
            else:
                owner_text = f"User {mapping.get('owner_id', 'Unknown')}"
            
            if is_league_owner:
                owner_text += " 👑"
            
            formatted += f"**Roster {roster_id}** → {owner_text}\n"
            formatted += f"  • Players: {player_count} | Starters: {starter_count}\n\n"
        
        return formatted
    
    def _format_league_draft_response(self, result: Dict[str, Any]) -> str:
        """Format league draft response."""
        league_id = result.get("league_id", "Unknown")
        draft_id = result.get("draft_id", "Unknown")
        draft_type = result.get("draft_type", "unknown")
        status = result.get("status", "unknown")
        season = result.get("season", "unknown")
        total_picks = result.get("total_picks", 0)
        draft_picks = result.get("draft_picks", [])
        
        formatted = f"📋 **Draft Results for League {league_id}**\n\n"
        formatted += f"**Draft Info:**\n"
        formatted += f"• Draft ID: `{draft_id}`\n"
        formatted += f"• Season: {season}\n"
        formatted += f"• Type: {draft_type.replace('_', ' ').title()}\n"
        formatted += f"• Status: {status.replace('_', ' ').title()}\n"
        formatted += f"• Total Picks: {total_picks}\n\n"
        
        if not draft_picks:
            formatted += "No draft picks found."
            return formatted
        
        # Group picks by round for better display
        rounds = {}
        for pick in draft_picks:
            round_num = pick.get("round", 0)
            if round_num not in rounds:
                rounds[round_num] = []
            rounds[round_num].append(pick)
        
        # Show first few rounds in detail
        max_rounds_to_show = 3
        rounds_shown = 0
        
        for round_num in sorted(rounds.keys()):
            if rounds_shown >= max_rounds_to_show:
                remaining_rounds = len(rounds) - rounds_shown
                formatted += f"**... and {remaining_rounds} more rounds with {sum(len(picks) for r, picks in rounds.items() if r > round_num)} picks**\n"
                break
                
            round_picks = rounds[round_num]
            formatted += f"**Round {round_num}:**\n"
            
            for pick in round_picks[:12]:  # Show max 12 picks per round
                pick_no = pick.get("pick_no", 0)
                player_info = pick.get("player_info", {})
                user_info = pick.get("user_info", {})
                is_keeper = pick.get("is_keeper", False)
                
                player_name = player_info.get("full_name", "Unknown Player")
                position = player_info.get("position", "")
                team = player_info.get("team", "")
                
                # Format user name
                display_name = user_info.get("display_name")
                username = user_info.get("username")
                if display_name and display_name != f"User {pick.get('picked_by')}":
                    user_text = display_name
                    if username:
                        user_text += f" (@{username})"
                elif username:
                    user_text = f"@{username}"
                else:
                    user_text = f"User {pick.get('picked_by', 'Unknown')}"
                
                # Format player info
                player_display = player_name
                if position:
                    player_display += f" ({position}"
                    if team:
                        player_display += f", {team}"
                    player_display += ")"
                
                keeper_indicator = " 🔒" if is_keeper else ""
                formatted += f"  {pick_no}. {player_display} → {user_text}{keeper_indicator}\n"
            
            if len(round_picks) > 12:
                formatted += f"  ... and {len(round_picks) - 12} more picks in this round\n"
            
            formatted += "\n"
            rounds_shown += 1
        
        # Add keeper legend if any keepers exist
        if any(pick.get("is_keeper", False) for pick in draft_picks):
            formatted += "🔒 = Keeper pick\n"
        
        return formatted
    
    def _format_matchups_response(self, result: Dict[str, Any]) -> str:
        """Format matchups response."""
        league_id = result.get("league_id", "Unknown")
        week = result.get("week", "Unknown")
        matchups = result.get("matchups", [])
        total_matchups = result.get("total_matchups", 0)
        
        formatted = f"⚔️ **Week {week} Matchups - League {league_id}**\n\n"
        
        if not matchups:
            formatted += "No matchups found for this week."
            return formatted
        
        for i, matchup in enumerate(matchups, 1):
            matchup_type = matchup.get("type", "unknown")
            teams = matchup.get("teams", [])
            
            if matchup_type == "bye":
                team = teams[0] if teams else {}
                user_info = team.get("user_info", {})
                team_name = self._format_team_name(team.get('roster_id', 'Unknown'), user_info)
                formatted += f"**Matchup {i}: BYE WEEK**\n"
                formatted += f"• {team_name}: {team.get('points', 0):.1f} pts\n\n"
            else:
                formatted += f"**Matchup {i}:**\n"
                for team in teams:
                    user_info = team.get("user_info", {})
                    team_name = self._format_team_name(team.get('roster_id', 'Unknown'), user_info)
                    formatted += f"• {team_name}: {team.get('points', 0):.1f} pts\n"
                formatted += "\n"
        
        return formatted
    
    def _format_matchup_scores_response(self, result: Dict[str, Any]) -> str:
        """Format matchup scores response."""
        league_id = result.get("league_id", "Unknown")
        week = result.get("week", "Unknown")
        scores = result.get("scores", [])
        summary = result.get("summary", {})
        
        formatted = f"📊 **Week {week} Scores - League {league_id}**\n\n"
        
        if summary:
            formatted += f"**Summary:**\n"
            formatted += f"• Teams: {summary.get('total_teams', 0)}\n"
            formatted += f"• Average Score: {summary.get('average_score', 0):.1f}\n"
            formatted += f"• Highest Score: {summary.get('highest_score', 0):.1f}\n"
            formatted += f"• Lowest Score: {summary.get('lowest_score', 0):.1f}\n\n"
        
        if not scores:
            formatted += "No scores found for this week."
            return formatted
        
        # Group scores by matchup for better display
        head_to_head = [s for s in scores if s.get("type") == "head_to_head"]
        byes = [s for s in scores if s.get("type") == "bye"]
        
        if head_to_head:
            formatted += "**Head-to-Head Matchups:**\n"
            matchup_groups = {}
            for score in head_to_head:
                matchup_id = score.get("matchup_id")
                if matchup_id not in matchup_groups:
                    matchup_groups[matchup_id] = []
                matchup_groups[matchup_id].append(score)
            
            for matchup_id, teams in matchup_groups.items():
                formatted += f"• Matchup {matchup_id}: "
                team_scores = []
                for team in teams:
                    roster_id = team.get("roster_id", "Unknown")
                    user_info = team.get("user_info", {})
                    team_name = self._format_team_name(roster_id, user_info)
                    points = team.get("points", 0)
                    is_winning = team.get("is_winning", False)
                    status = " 🏆" if is_winning else ""
                    team_scores.append(f"{team_name}: {points:.1f}{status}")
                formatted += " vs ".join(team_scores) + "\n"
            formatted += "\n"
        
        if byes:
            formatted += "**Bye Weeks:**\n"
            for score in byes:
                roster_id = score.get("roster_id", "Unknown")
                user_info = score.get("user_info", {})
                team_name = self._format_team_name(roster_id, user_info)
                points = score.get("points", 0)
                formatted += f"• {team_name}: {points:.1f} pts\n"
        
        return formatted
    
    def _format_trade_analysis_response(self, result: Dict[str, Any]) -> str:
        """Format trade analysis response."""
        roster_id = result.get("roster_id", "Unknown")
        target_position = result.get("target_position")
        roster_analysis = result.get("roster_analysis", {})
        target_teams = result.get("target_teams", [])
        suggested_trades = result.get("suggested_trades", [])
        analysis_summary = result.get("analysis_summary", "")
        
        formatted = f"🔄 **Trade Analysis for Roster {roster_id}**\n\n"
        
        if target_position:
            formatted += f"**Target Position:** {target_position}\n\n"
        
        if analysis_summary:
            formatted += f"**Summary:** {analysis_summary}\n\n"
        
        # Roster strength analysis
        positional_strength = roster_analysis.get("positional_strength", {})
        if positional_strength:
            formatted += "**Positional Strength:**\n"
            for position, strength in positional_strength.items():
                strength_pct = strength * 100
                if strength >= 0.8:
                    emoji = "💪"
                elif strength >= 0.6:
                    emoji = "👍"
                elif strength >= 0.4:
                    emoji = "⚠️"
                else:
                    emoji = "🔴"
                formatted += f"• {position}: {strength_pct:.0f}% {emoji}\n"
            formatted += "\n"
        
        # Trade targets
        if target_teams:
            formatted += f"**Potential Trade Partners:** {len(target_teams)} teams\n"
            formatted += f"• Target Roster IDs: {', '.join(map(str, target_teams))}\n"
        
        # Trade suggestions
        if suggested_trades:
            formatted += "\n**Trade Suggestions:**\n"
            for i, trade in enumerate(suggested_trades[:3], 1):  # Show top 3
                target_roster = trade.get("target_roster_id", "Unknown")
                rationale = trade.get("trade_rationale", "No rationale provided")
                confidence = trade.get("confidence", 0) * 100
                formatted += f"{i}. **Target Roster {target_roster}** (Confidence: {confidence:.0f}%)\n"
                formatted += f"   {rationale}\n\n"
        
        return formatted
    
    def _format_roster_evaluation_response(self, result: Dict[str, Any]) -> str:
        """Format roster evaluation response."""
        roster_id = result.get("roster_id", "Unknown")
        positional_strength = result.get("positional_strength", {})
        overall_rating = result.get("overall_rating", 0)
        recommendations = result.get("recommendations", [])
        league_comparison = result.get("league_comparison", {})
        
        formatted = f"📋 **Roster Evaluation for Roster {roster_id}**\n\n"
        
        # Overall rating
        rating_pct = overall_rating * 100
        if overall_rating >= 0.8:
            rating_emoji = "🌟"
        elif overall_rating >= 0.6:
            rating_emoji = "👍"
        elif overall_rating >= 0.4:
            rating_emoji = "⚠️"
        else:
            rating_emoji = "🔴"
        
        formatted += f"**Overall Rating:** {rating_pct:.0f}% {rating_emoji}\n\n"
        
        # Positional breakdown
        if positional_strength:
            formatted += "**Positional Strength:**\n"
            sorted_positions = sorted(positional_strength.items(), key=lambda x: x[1], reverse=True)
            
            for position, strength in sorted_positions:
                strength_pct = strength * 100
                if strength >= 0.8:
                    emoji = "💪"
                elif strength >= 0.6:
                    emoji = "👍"
                elif strength >= 0.4:
                    emoji = "⚠️"
                else:
                    emoji = "🔴"
                
                # Add league comparison if available
                comparison = league_comparison.get(position, 0)
                if comparison > 0.1:
                    comp_text = f" (+{comparison*100:.0f}% vs league avg)"
                elif comparison < -0.1:
                    comp_text = f" ({comparison*100:.0f}% vs league avg)"
                else:
                    comp_text = " (≈ league avg)"
                
                formatted += f"• {position}: {strength_pct:.0f}% {emoji}{comp_text}\n"
            formatted += "\n"
        
        # Recommendations
        if recommendations:
            formatted += "**Recommendations:**\n"
            for rec in recommendations:
                formatted += f"• {rec}\n"
        
        return formatted
    
    def _format_search_players_response(self, result: Dict[str, Any]) -> str:
        """Format search players response."""
        query = result.get("query", "Unknown")
        position_filter = result.get("position_filter")
        total_results = result.get("total_results", 0)
        players = result.get("players", [])
        
        formatted = f"🔍 **Player Search Results for '{query}'**"
        if position_filter:
            formatted += f" (Position: {position_filter})"
        formatted += f"\n\n**Found {total_results} players:**\n\n"
        
        if not players:
            formatted += "No players found matching your search criteria."
            return formatted
        
        for i, player in enumerate(players, 1):
            name = player.get("full_name", "Unknown")
            position = player.get("position", "Unknown")
            team = player.get("team", "FA")
            status = player.get("status", "Unknown")
            
            status_emoji = "✅" if status == "Active" else "❌"
            formatted += f"{i}. **{name}** ({position} - {team}) {status_emoji}\n"
            formatted += f"   Player ID: `{player.get('player_id', 'Unknown')}`\n\n"
        
        return formatted
    
    def _format_trending_players_response(self, result: Dict[str, Any]) -> str:
        """Format trending players response."""
        sport = result.get("sport", "nfl").upper()
        trend_type = result.get("trend_type", "add")
        total_results = result.get("total_results", 0)
        players = result.get("players", [])
        
        trend_emoji = "📈" if trend_type == "add" else "📉"
        trend_text = "Most Added" if trend_type == "add" else "Most Dropped"
        
        formatted = f"{trend_emoji} **{trend_text} Players ({sport})**\n\n"
        formatted += f"**Top {total_results} trending players:**\n\n"
        
        if not players:
            formatted += f"No trending {trend_type} data available."
            return formatted
        
        for i, player in enumerate(players, 1):
            name = player.get("full_name", "Unknown")
            position = player.get("position", "Unknown")
            team = player.get("team", "FA")
            count = player.get("count", 0)
            status = player.get("status", "Unknown")
            
            status_emoji = "✅" if status == "Active" else "❌"
            formatted += f"{i}. **{name}** ({position} - {team}) {status_emoji}\n"
            formatted += f"   {trend_type.title()} count: {count:,}\n\n"
        
        return formatted
    
    def _format_player_stats_response(self, result: Dict[str, Any]) -> str:
        """Format player stats response."""
        player_name = result.get("player_name", "Unknown")
        position = result.get("position", "Unknown")
        team = result.get("team", "Unknown")
        season = result.get("season", "Unknown")
        stats = result.get("stats", {})
        
        formatted = f"📊 **{player_name} Stats ({season})**\n\n"
        formatted += f"**Player Info:**\n"
        formatted += f"• Position: {position}\n"
        formatted += f"• Team: {team}\n"
        formatted += f"• Season: {season}\n\n"
        
        if not stats:
            formatted += "No statistics available for this player/season."
            return formatted
        
        formatted += "**Statistics:**\n"
        
        # Group stats by category for better display
        passing_stats = {k: v for k, v in stats.items() if k.startswith('pass_')}
        rushing_stats = {k: v for k, v in stats.items() if k.startswith('rush_')}
        receiving_stats = {k: v for k, v in stats.items() if k.startswith('rec_')}
        other_stats = {k: v for k, v in stats.items() 
                      if not any(k.startswith(prefix) for prefix in ['pass_', 'rush_', 'rec_'])}
        
        if passing_stats:
            formatted += "\n**Passing:**\n"
            for stat, value in passing_stats.items():
                stat_name = stat.replace('pass_', '').replace('_', ' ').title()
                formatted += f"• {stat_name}: {value}\n"
        
        if rushing_stats:
            formatted += "\n**Rushing:**\n"
            for stat, value in rushing_stats.items():
                stat_name = stat.replace('rush_', '').replace('_', ' ').title()
                formatted += f"• {stat_name}: {value}\n"
        
        if receiving_stats:
            formatted += "\n**Receiving:**\n"
            for stat, value in receiving_stats.items():
                stat_name = stat.replace('rec_', '').replace('_', ' ').title()
                formatted += f"• {stat_name}: {value}\n"
        
        if other_stats:
            formatted += "\n**Other:**\n"
            for stat, value in other_stats.items():
                stat_name = stat.replace('_', ' ').title()
                formatted += f"• {stat_name}: {value}\n"
        
        return formatted
    
    def _format_team_name(self, roster_id: str, user_info: Dict[str, Any]) -> str:
        """Format a team name with user information."""
        display_name = user_info.get("display_name")
        username = user_info.get("username")
        is_league_owner = user_info.get("is_owner", False)
        
        if display_name and display_name != f"User {roster_id}":
            team_name = display_name
            if username:
                team_name += f" (@{username})"
        elif username:
            team_name = f"@{username}"
        else:
            team_name = f"Roster {roster_id}"
        
        if is_league_owner:
            team_name += " 👑"
        
        return team_name
    
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

    def _structure_raw_result(self, tool_name: str, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Convert raw Sleeper API result to structured JSON for HTTP clients."""
        try:
            if "error" in raw_result:
                return {
                    "error": raw_result.get("error"),
                    "suggestions": raw_result.get("suggestions", []),
                    "type": "error"
                }
            
            # Structure based on tool type
            if tool_name == "get_user_leagues":
                return self._structure_user_leagues(raw_result)
            elif tool_name == "get_league_info":
                return self._structure_league_info(raw_result)
            elif tool_name == "get_league_rosters":
                return self._structure_league_rosters(raw_result)
            elif tool_name == "get_league_rosters_with_draft_info":
                return self._structure_league_rosters_with_draft(raw_result)
            elif tool_name == "get_league_users":
                return self._structure_league_users(raw_result)
            elif tool_name == "get_roster_user_mapping":
                return self._structure_roster_user_mapping(raw_result)
            elif tool_name == "get_league_draft":
                return self._structure_league_draft(raw_result)
            elif tool_name == "search_players":
                return self._structure_search_players(raw_result)
            elif tool_name == "get_trending_players":
                return self._structure_trending_players(raw_result)
            elif tool_name == "get_player_stats":
                return self._structure_player_stats(raw_result)
            elif tool_name == "get_matchups":
                return self._structure_matchups(raw_result)
            elif tool_name == "get_matchup_scores":
                return self._structure_matchup_scores(raw_result)
            elif tool_name == "analyze_trade_targets":
                return self._structure_trade_analysis(raw_result)
            elif tool_name == "evaluate_roster_needs":
                return self._structure_roster_evaluation(raw_result)
            else:
                # Fallback: return the raw result as-is
                return {"data": raw_result, "type": "raw"}
                
        except Exception as e:
            logger.error(f"Error structuring {tool_name} result: {e}")
            return {"error": f"Failed to structure result: {str(e)}", "type": "error"}

    def _structure_user_leagues(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Structure user leagues data."""
        username = raw_result.get("username", "Unknown")
        season = raw_result.get("season", "Unknown")
        leagues = raw_result.get("leagues", [])
        
        return {
            "username": username,
            "season": season,
            "leagues": [
                {
                    "id": league.get("league_id"),
                    "name": league.get("name"),
                    "status": league.get("status"),
                    "teams": league.get("total_rosters"),
                    "sport": league.get("sport"),
                    "season": league.get("season"),
                    "scoring_type": league.get("scoring_settings", {}).get("v", "Standard"),
                    "roster_positions": league.get("roster_positions", [])
                }
                for league in leagues
            ],
            "total_leagues": len(leagues)
        }

    def _structure_league_info(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Structure league info data."""
        league = raw_result.get("league", {})
        settings = raw_result.get("settings", {})
        
        return {
            "league_id": league.get("league_id"),
            "name": league.get("name"),
            "season": league.get("season"),
            "status": league.get("status"),
            "sport": league.get("sport"),
            "teams": league.get("total_rosters"),
            "scoring_type": settings.get("v", "Standard"),
            "roster_positions": settings.get("roster_positions", []),
            "scoring_settings": settings.get("scoring_settings", {}),
            "trade_deadline": settings.get("trade_deadline"),
            "playoff_start_week": settings.get("playoff_start_week"),
            "playoff_teams": settings.get("playoff_teams")
        }

    def _structure_league_rosters(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Structure league rosters data."""
        rosters = raw_result.get("rosters", [])
        users = raw_result.get("users", [])
        
        # Create user lookup
        user_lookup = {user["user_id"]: user for user in users}
        
        return {
            "league_id": raw_result.get("league_id"),
            "rosters": [
                {
                    "roster_id": roster.get("roster_id"),
                    "owner_id": roster.get("owner_id"),
                    "owner_name": user_lookup.get(roster.get("owner_id"), {}).get("display_name", "Unknown"),
                    "players": roster.get("players", []),
                    "starters": roster.get("starters", []),
                    "reserve": roster.get("reserve", []),
                    "taxi": roster.get("taxi", []),
                    "metadata": roster.get("metadata", {}),
                    "settings": roster.get("settings", {})
                }
                for roster in rosters
            ],
            "total_rosters": len(rosters)
        }

    def _structure_league_rosters_with_draft(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Structure league rosters with draft info data."""
        rosters = raw_result.get("rosters", [])
        users = raw_result.get("users", [])
        draft = raw_result.get("draft", {})
        
        # Create user lookup
        user_lookup = {user["user_id"]: user for user in users}
        
        return {
            "league_id": raw_result.get("league_id"),
            "draft_id": draft.get("draft_id"),
            "draft_status": draft.get("status"),
            "rosters": [
                {
                    "roster_id": roster.get("roster_id"),
                    "owner_id": roster.get("owner_id"),
                    "owner_name": user_lookup.get(roster.get("owner_id"), {}).get("display_name", "Unknown"),
                    "players": roster.get("players", []),
                    "starters": roster.get("starters", []),
                    "reserve": roster.get("reserve", []),
                    "taxi": roster.get("taxi", []),
                    "metadata": roster.get("metadata", {}),
                    "settings": roster.get("settings", {})
                }
                for roster in rosters
            ],
            "total_rosters": len(rosters)
        }

    def _structure_league_users(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Structure league users data."""
        users = raw_result.get("users", [])
        
        return {
            "league_id": raw_result.get("league_id"),
            "users": [
                {
                    "user_id": user.get("user_id"),
                    "display_name": user.get("display_name"),
                    "avatar": user.get("avatar"),
                    "metadata": user.get("metadata", {})
                }
                for user in users
            ],
            "total_users": len(users)
        }

    def _structure_roster_user_mapping(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Structure roster user mapping data."""
        # The get_roster_user_mapping method returns roster_user_mapping directly
        roster_mappings = raw_result.get("roster_user_mapping", [])
        
        return {
            "league_id": raw_result.get("league_id"),
            "mappings": [
                {
                    "roster_id": mapping.get("roster_id"),
                    "user_id": mapping.get("owner_id"),
                    "user_name": mapping.get("user_info", {}).get("display_name", "Unknown"),
                    "avatar": mapping.get("user_info", {}).get("avatar")
                }
                for mapping in roster_mappings
            ],
            "total_mappings": len(roster_mappings)
        }

    def _structure_league_draft(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Structure league draft data."""
        picks = raw_result.get("draft_picks", [])
        
        return {
            "league_id": raw_result.get("league_id"),
            "draft_id": raw_result.get("draft_id"),
            "draft_status": raw_result.get("status"),
            "draft_type": raw_result.get("draft_type"),
            "draft_order": raw_result.get("draft_order", []),
            "picks": [
                {
                    "pick_no": pick.get("pick_no"),
                    "round": pick.get("round"),
                    "roster_id": pick.get("picked_by"),  # Use picked_by as roster_id
                    "player_id": pick.get("player_id"),
                    "player_name": pick.get("player_info", {}).get("full_name"),
                    "position": pick.get("player_info", {}).get("position"),
                    "team": pick.get("player_info", {}).get("team"),
                    "is_keeper": pick.get("is_keeper", False),
                    "keeper_for_team": pick.get("keeper_for_team"),
                    "draft_slot": pick.get("draft_slot")
                }
                for pick in picks
            ],
            "total_picks": len(picks)
        }

    def _structure_search_players(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Structure search players data."""
        players = raw_result.get("players", [])
        
        return {
            "query": raw_result.get("query", ""),
            "position": raw_result.get("position"),
            "players": [
                {
                    "id": player.get("id"),
                    "name": player.get("name"),
                    "position": player.get("position"),
                    "team": player.get("team"),
                    "status": player.get("status"),
                    "search_rank": player.get("search_rank"),
                    "fantasy_positions": player.get("fantasy_positions", [])
                }
                for player in players
            ],
            "total_players": len(players)
        }

    def _structure_trending_players(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Structure trending players data."""
        players = raw_result.get("players", [])
        
        return {
            "sport": raw_result.get("sport", "nfl"),
            "add_drop": raw_result.get("add_drop", "add"),
            "players": [
                {
                    "id": player.get("player_id"),
                    "name": player.get("full_name"),
                    "position": player.get("position"),
                    "team": player.get("team"),
                    "status": player.get("status"),
                    "trend_direction": player.get("trend_direction"),
                    "trend_reason": player.get("trend_reason")
                }
                for player in players
            ],
            "total_players": len(players)
        }

    def _structure_player_stats(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Structure player stats data."""
        stats = raw_result.get("stats", {})
        
        return {
            "player_id": raw_result.get("player_id"),
            "player_name": raw_result.get("player_name"),
            "position": raw_result.get("position"),
            "team": raw_result.get("team"),
            "season": raw_result.get("season"),
            "stats": stats,
            "total_stats": raw_result.get("total_stats", len(stats))
        }

    def _structure_matchups(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Structure matchups data."""
        matchups = raw_result.get("matchups", [])
        
        return {
            "league_id": raw_result.get("league_id"),
            "week": raw_result.get("week"),
            "matchups": [
                {
                    "matchup_id": matchup.get("matchup_id"),
                    "roster_id": matchup.get("roster_id"),
                    "points": matchup.get("points"),
                    "players": matchup.get("players", []),
                    "starters": matchup.get("starters", []),
                    "reserve": matchup.get("reserve", []),
                    "taxi": matchup.get("taxi", [])
                }
                for matchup in matchups
            ],
            "total_matchups": len(matchups)
        }

    def _structure_matchup_scores(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Structure matchup scores data."""
        scores = raw_result.get("scores", [])
        
        return {
            "league_id": raw_result.get("league_id"),
            "week": raw_result.get("week"),
            "matchups": [
                {
                    "matchup_id": score.get("matchup_id"),
                    "roster_id": score.get("roster_id"),
                    "points": score.get("points"),
                    "starters_points": score.get("points", 0),  # Use points as starters_points
                    "bench_points": score.get("points_bonus", 0)  # Use points_bonus as bench_points
                }
                for score in scores
            ],
            "total_matchups": len(scores)
        }

    def _structure_trade_analysis(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Structure trade analysis data."""
        return {
            "league_id": raw_result.get("league_id"),
            "roster_id": raw_result.get("roster_id"),
            "position": raw_result.get("position"),
            "target_teams": raw_result.get("target_teams", []),
            "suggested_trades": raw_result.get("suggested_trades", []),
            "positional_needs": raw_result.get("positional_needs", {}),
            "trade_value_analysis": raw_result.get("trade_value_analysis", {})
        }

    def _structure_roster_evaluation(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Structure roster evaluation data."""
        return {
            "league_id": raw_result.get("league_id"),
            "roster_id": raw_result.get("roster_id"),
            "strengths": raw_result.get("strengths", []),
            "weaknesses": raw_result.get("weaknesses", []),
            "recommendations": raw_result.get("recommendations", []),
            "positional_analysis": raw_result.get("positional_analysis", {}),
            "overall_grade": raw_result.get("overall_grade", "N/A")
        }


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

