"""
AutoGen MCP Framework - Generic Multi-Agent System with MCP Integration
"""

__version__ = "1.0.0"

# Core imports
from .config import load_configuration, AppConfig, LLMSettings, MCPSettings, AgentSettings
from .agents import AgentFactory, AgentOrchestrator
from .mcp import HTTPMCPClient, MultiMCPClient, MCPToolsClient
from .cli import run_cli

__all__ = [
    "load_configuration",
    "AppConfig", 
    "LLMSettings",
    "MCPSettings",
    "AgentSettings",
    "AgentFactory",
    "AgentOrchestrator",
    "HTTPMCPClient",
    "MultiMCPClient", 
    "MCPToolsClient",
    "run_cli"
] 