#!/usr/bin/env python3
"""
AutoGen MCP Framework - Main Entry Point
"""

import sys
import asyncio


def main():
    """Main entry point for the application."""
    try:
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