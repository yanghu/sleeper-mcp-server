#!/usr/bin/env python3
"""
Startup script for the Sleeper MCP server.

This script provides an easy way to start the server in different transport modes
and with different configurations.
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path and activate virtual environment
project_root = Path(__file__).parent.parent
venv_path = project_root / ".venv"

# Add project root to Python path
sys.path.insert(0, str(project_root))

# Try to activate virtual environment if it exists
if venv_path.exists():
    # Add virtual environment site-packages to Python path
    site_packages = venv_path / "lib" / "python3.12" / "site-packages"
    if site_packages.exists():
        sys.path.insert(0, str(site_packages))
    
    # Also try alternative Python version paths
    for python_version in ["3.11", "3.10", "3.9", "3.8"]:
        alt_site_packages = venv_path / "lib" / f"python{python_version}" / "site-packages"
        if alt_site_packages.exists():
            sys.path.insert(0, str(alt_site_packages))
            break

try:
    from sleeper_mcp_server.multi_transport_server import MultiTransportSleeperServer
except ImportError as e:
    print(f"❌ Error importing MultiTransportSleeperServer: {e}")
    print(f"💡 Make sure you're in the virtual environment:")
    print(f"   source .venv/bin/activate")
    print(f"   # or")
    print(f"   python -m venv .venv && source .venv/bin/activate")
    print(f"   pip install -e .")
    sys.exit(1)


def setup_logging(level: str = "INFO"):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr
    )


def get_environment_config():
    """Get configuration from environment variables."""
    return {
        "transport_mode": os.getenv("TRANSPORT_MODE", "stdio"),
        "http_host": os.getenv("HTTP_HOST", "0.0.0.0"),
        "http_port": int(os.getenv("HTTP_PORT", "8000")),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
    }


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Start the Sleeper MCP server in different transport modes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start in stdio mode (Claude Desktop)
  python scripts/start_server.py

  # Start HTTP server on default port
  python scripts/start_server.py --http

  # Start HTTP server on custom port
  python scripts/start_server.py --http --port 8080

  # Start both MCP and HTTP simultaneously
  python scripts/start_server.py --both

  # Start with custom host and port
  python scripts/start_server.py --http --host 127.0.0.1 --port 9000

Environment Variables:
  TRANSPORT_MODE    Transport mode (stdio, http, both)
  HTTP_HOST         HTTP server host (default: 0.0.0.0)
  HTTP_PORT         HTTP server port (default: 8000)
  LOG_LEVEL         Logging level (default: INFO)
        """
    )
    
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="Start in stdio mode for Claude Desktop (default)"
    )
    
    parser.add_argument(
        "--http",
        action="store_true",
        help="Start HTTP server for agent platforms"
    )
    
    parser.add_argument(
        "--both",
        action="store_true",
        help="Start both MCP and HTTP servers simultaneously"
    )
    
    parser.add_argument(
        "--host",
        default=None,
        help="HTTP server host (default: from TRANSPORT_MODE env var or 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="HTTP server port (default: from HTTP_PORT env var or 8000)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="Logging level (default: from LOG_LEVEL env var or INFO)"
    )
    
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Check if all required dependencies are available"
    )
    
    return parser.parse_args()


def check_dependencies():
    """Check if all required dependencies are available."""
    print("🔍 Checking dependencies...")
    
    # Check MCP dependencies
    try:
        import mcp
        print("   ✅ MCP library available")
    except ImportError:
        print("   ❌ MCP library not available")
        return False
    
    # Check HTTP dependencies
    try:
        import fastapi
        import uvicorn
        print("   ✅ FastAPI and Uvicorn available")
    except ImportError:
        print("   ⚠️  FastAPI/Uvicorn not available - HTTP transport will be disabled")
        print("   💡 Install with: pip install fastapi uvicorn[standard]")
    
    # Check other dependencies
    try:
        import httpx
        import pydantic
        print("   ✅ Core dependencies available")
    except ImportError:
        print("   ❌ Core dependencies not available")
        return False
    
    print("   ✅ All required dependencies are available")
    return True


def determine_transport_mode(args):
    """Determine the transport mode based on arguments and environment."""
    # Priority: command line args > environment variables > defaults
    
    if args.both:
        return "both"
    elif args.http:
        return "http"
    elif args.stdio:
        return "stdio"
    else:
        # Check environment variable
        env_config = get_environment_config()
        return env_config["transport_mode"]


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Check dependencies if requested
    if args.check_deps:
        if not check_dependencies():
            sys.exit(1)
        return
    
    # Determine transport mode
    transport_mode = determine_transport_mode(args)
    
    # Get configuration
    env_config = get_environment_config()
    
    http_host = args.host or env_config["http_host"]
    http_port = args.port or env_config["http_port"]
    log_level = args.log_level or env_config["log_level"]
    
    # Setup logging
    setup_logging(log_level)
    logger = logging.getLogger(__name__)
    
    # Display configuration
    logger.info(f"Starting Sleeper MCP Server")
    logger.info(f"Transport Mode: {transport_mode}")
    if transport_mode in ["http", "both"]:
        logger.info(f"HTTP Server: {http_host}:{http_port}")
    logger.info(f"Log Level: {log_level}")
    
    # Validate configuration
    if transport_mode not in ["stdio", "http", "both"]:
        logger.error(f"Invalid transport mode: {transport_mode}")
        sys.exit(1)
    
    if transport_mode in ["http", "both"] and (http_port < 1 or http_port > 65535):
        logger.error(f"Invalid port number: {http_port}")
        sys.exit(1)
    
    try:
        # Create server
        server = MultiTransportSleeperServer(
            transport_mode=transport_mode,
            http_host=http_host,
            http_port=http_port
        )
        
        # Run the server using asyncio.run() to avoid event loop conflicts
        asyncio.run(server.run())
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
