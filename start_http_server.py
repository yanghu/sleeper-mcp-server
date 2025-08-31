#!/usr/bin/env python3
"""
Simple script to start the Sleeper MCP server in HTTP mode.

This script should be run from the virtual environment:
    source .venv/bin/activate
    python start_http_server.py

Or run directly with the virtual environment Python:
    .venv/bin/python start_http_server.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from sleeper_mcp_server.multi_transport_server import MultiTransportSleeperServer
except ImportError as e:
    print(f"❌ Error importing MultiTransportSleeperServer: {e}")
    print(f"💡 Make sure you're in the virtual environment:")
    print(f"   source .venv/bin/activate")
    print(f"   # or run directly with:")
    print(f"   .venv/bin/python start_http_server.py")
    sys.exit(1)


async def main():
    """Start the HTTP server."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr
    )
    
    logger = logging.getLogger(__name__)
    
    # Configuration
    transport_mode = "http"
    http_host = "0.0.0.0"
    http_port = 8000
    
    logger.info(f"Starting Sleeper MCP Server in {transport_mode} mode")
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
