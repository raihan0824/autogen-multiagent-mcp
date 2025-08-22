"""
CLI commands and utilities.
"""

import logging
from typing import Optional

from ..config import AppConfig
from ..agents import AgentOrchestrator, WorkflowResult

logger = logging.getLogger(__name__)


class CLICommands:
    """CLI commands for the AutoGen MCP application."""
    
    def __init__(self, config: AppConfig, orchestrator: AgentOrchestrator):
        self.config = config
        self.orchestrator = orchestrator
    
    async def display_workflow_result(self, result: WorkflowResult) -> None:
        """Display the result of a workflow execution."""
        if not result.success:
            print(f"❌ Workflow failed: {result.error}")
            return
        
        print(f"\n🔄 Multi-Agent Conversation ({len(result.messages)} agents participated):")
        print("=" * 80)
        
        for i, message in enumerate(result.messages, 1):
            print(f"\n[{i}] 🤖 {message.agent_name.upper()}:")
            print("-" * 40)
            print(message.content)
            
            if message.mcp_result:
                if message.mcp_result.get("success", False):
                    print(f"\n📊 MCP Results from {message.agent_name}:")
                    print("=" * 50)
                    print(message.mcp_result.get("content", "No content available"))
                    print("=" * 50)
                else:
                    print(f"\n❌ MCP Error: {message.mcp_result.get('error', 'Unknown error')}")
        
        print("\n" + "=" * 80)
        print(f"✅ Workflow completed with {len(result.messages)} agent responses")
    
    async def show_status(self) -> None:
        """Show system status."""
        print("\n📊 System Status:")
        print(f"  MCP Connected: {'✅' if self.orchestrator.kubernetes_client.is_connected() else '❌'}")
        print(f"  MCP Server: {self.config.mcp.server_url}")
        print(f"  LLM Model: {self.config.llm.model_name}")
        print(f"  Allowed Namespaces: {', '.join(self.config.agents.allowed_namespaces)}")
        print(f"  Max Rounds: {self.config.agents.max_conversation_rounds}")
        
        # Test MCP health
        try:
            healthy = await self.orchestrator.kubernetes_client.health_check()
            print(f"  MCP Health: {'✅ Healthy' if healthy else '❌ Unhealthy'}")
        except Exception as e:
            print(f"  MCP Health: ❌ Error - {e}")
    
    def show_config(self) -> None:
        """Show configuration (with sensitive data masked)."""
        print("\n⚙️  Configuration:")
        print("  LLM Settings:")
        print(f"    Model: {self.config.llm.model_name}")
        print(f"    Base URL: {self.config.llm.api_base_url}")
        print(f"    API Key: {'*' * 20}")
        print(f"    Timeout: {self.config.llm.timeout_seconds}s")
        print(f"    Temperature: {self.config.llm.temperature}")
        
        print("  MCP Settings:")
        print(f"    Server URL: {self.config.mcp.server_url}")
        print(f"    Enabled: {self.config.mcp.enabled}")
        print(f"    Timeout: {self.config.mcp.timeout_seconds}s")
        print(f"    Retry Attempts: {self.config.mcp.retry_attempts}")
        
        print("  Agent Settings:")
        print(f"    Max Rounds: {self.config.agents.max_conversation_rounds}")
        print(f"    Safety Checks: {self.config.agents.enable_safety_checks}")
        print(f"    Allowed Namespaces: {', '.join(self.config.agents.allowed_namespaces)}")
        
        print("  Logging:")
        print(f"    Level: {self.config.logging.level}")
        print(f"    File Logging: {self.config.logging.enable_file_logging}")
    
    def show_help(self) -> None:
        """Show help information."""
        print("\n📖 AutoGen MCP Framework Help")
        print("=" * 40)
        print("Available commands:")
        print("  query <text>     - Process a Kubernetes query using simple workflow")
        print("  multi <text>     - Process query using multi-agent workflow")
        print("  status          - Show system status and health")
        print("  config          - Show current configuration")
        print("  help            - Show this help message")
        print("  exit            - Exit the application")
        print()
        print("Examples:")
        print("  query get all pods in default namespace")
        print("  multi describe failing pods")
        print("  status")
        print()
        print("Command line usage:")
        print("  autogen-mcp \"get pods\"           # Simple workflow")
        print("  autogen-mcp --multi \"get pods\"  # Multi-agent workflow")
        print("  autogen-mcp                      # Interactive mode") 