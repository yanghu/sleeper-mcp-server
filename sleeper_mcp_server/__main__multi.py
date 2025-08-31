"""Main entry point for the multi-transport Sleeper MCP server."""

import asyncio
import sys
from typing import Optional

from .multi_transport_server import main as multi_transport_main


def main(args: Optional[list[str]] = None) -> int:
    """Main entry point for the multi-transport Sleeper MCP server.
    
    This entry point supports multiple transport modes:
    - stdio: MCP protocol for Claude Desktop (default)
    - http: HTTP REST API for agent platforms
    - both: Both MCP and HTTP simultaneously
    
    Args:
        args: Command line arguments (defaults to sys.argv[1:])
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    if args is None:
        args = sys.argv[1:]
    
    try:
        # Run the multi-transport MCP server
        asyncio.run(multi_transport_main())
        return 0
    except KeyboardInterrupt:
        print("\nServer stopped by user", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
