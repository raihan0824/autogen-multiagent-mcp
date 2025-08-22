"""
AutoGen MCP Framework - Generic Multi-Agent System with MCP Integration
"""

__version__ = "1.0.0"

# Core imports
from .config import load_configuration, AppConfig, LLMSettings, MCPSettings, AgentSettings
from .agents import AgentFactory, AgentOrchestrator
from .cli import run_cli

# AutoGen native MCP support - use autogen_ext.tools.mcp directly

__all__ = [
    "load_configuration",
    "AppConfig", 
    "LLMSettings",
    "MCPSettings",
    "AgentSettings",
    "AgentFactory",
    "AgentOrchestrator",
    "run_cli"
] 