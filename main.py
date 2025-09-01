#!/usr/bin/env python3
"""
AutoGen MCP Framework - Main Entry Point
"""

import sys
import asyncio
import os


def main():
    """Main entry point for the application."""
    try:
        # Check if we should run in API mode
        api_mode = os.getenv("AUTOGEN_API_MODE", "false").lower() in (
            "true", "1", "yes")

        if api_mode or (len(sys.argv) > 1 and sys.argv[1] == "api"):
            # Run API server
            from autogen_mcp.api.main import main as api_main
            api_main()
        else:
            # Run CLI application
            from autogen_mcp.cli.main import main_async
            asyncio.run(main_async())

    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
