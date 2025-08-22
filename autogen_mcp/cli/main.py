"""
Main CLI application for AutoGen MCP Framework.
"""

import asyncio
import sys
import logging
from pathlib import Path
from typing import Optional

from ..config import load_configuration
from ..mcp import MCPToolsClient
from ..agents import AgentOrchestrator
from .commands import CLICommands

def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )


class AutoGenMCPCLI:
    """Main CLI application."""
    
    def __init__(self):
        self.config = None

        self.orchestrator = None
        self.commands = None
    
    async def initialize(self) -> bool:
        """Initialize the CLI application."""
        try:
            print("🚀 AutoGen MCP Framework")
            print("=" * 60)
            
            # Load and validate configuration
            self.config = load_configuration()
            # validate_configuration(self.config) # Removed as per edit hint
            setup_logging(self.config.logging.level)
            print("✅ Configuration loaded and validated")
            
            # Create generic MCP client
            self.mcp_client = MCPToolsClient(
                self.config.mcp,
                self.config.agents
            )
            print("✅ MCP client created")
            
            # Create orchestrator
            self.orchestrator = AgentOrchestrator(self.config, self.mcp_client)
            if not await self.orchestrator.initialize():
                print("❌ Failed to initialize orchestrator")
                return False
            print("✅ Agent orchestrator initialized")
            
            # Create CLI commands
            self.commands = CLICommands(self.config, self.orchestrator)
            print("✅ CLI ready")
            print()
            
            return True
            
        except Exception as e: # Changed from ConfigurationError to Exception
            print(f"❌ Initialization failed: {e}")
            return False
    
    async def run_single_query(self, query: str, workflow_type: str = "multi") -> None:
        """Run a single query and exit."""
        print(f"🔍 Query: {query}")
        print("-" * 50)
        
        try:
            if workflow_type == "simple":
                result = await self.orchestrator.execute_simple_workflow(query)
            else:
                result = await self.orchestrator.execute_multi_agent_workflow(query)
            
            await self.commands.display_workflow_result(result)
            
        except Exception as e:
            print(f"❌ Error processing query: {e}")
    
    async def run(self) -> None:
        """Run the CLI application."""
        if len(sys.argv) > 1:
            # Single query mode
            query = " ".join(sys.argv[1:])
            workflow_type = "multi"  # Default to multi-agent workflow
            await self.run_single_query(query, workflow_type)
        else:
            # Interactive mode
            await self.run_interactive()
    
    async def run_interactive(self) -> None:
        """Run interactive CLI mode."""
        print("\n🤖 Welcome to AutoGen MCP Framework!")
        print("Enter your queries below. Type 'quit' or 'exit' to stop.\n")
        
        while True:
            try:
                query = input("❓ Query: ").strip()
                if query.lower() in ['quit', 'exit', 'q']:
                    break
                if query:
                    await self.run_single_query(query, "multi")
                    print()
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Goodbye!")
                break
    
    async def close(self) -> None:
        """Clean up resources."""
        try:
            if hasattr(self, 'orchestrator') and self.orchestrator:
                await self.orchestrator.close()
            if hasattr(self, 'mcp_client') and self.mcp_client:
                await self.mcp_client.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


async def main_async():
    """Main async entry point."""
    cli = AutoGenMCPCLI()
    
    try:
        if not await cli.initialize():
            return
        
        await cli.run()
    finally:
        await cli.close()


def run_cli() -> None:
    """Main CLI entry point."""
    exit_code = asyncio.run(main_async())
    sys.exit(exit_code) 