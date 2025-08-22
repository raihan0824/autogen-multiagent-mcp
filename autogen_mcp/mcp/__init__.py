"""MCP (Model Context Protocol) integration for AutoGen."""

from .client import HTTPMCPClient, MCPClientError
from .multi_client import MultiMCPClient, MCPToolsClient
from .commands import MCPCommand, ToolDefinition
from .responses import MCPResponse, MCPOperationResult

__all__ = [
    "HTTPMCPClient",
    "MCPClientError", 
    "MultiMCPClient",
    "MCPToolsClient",
    "MCPCommand",
    "ToolDefinition",

    "MCPResponse",
    "MCPOperationResult",  # Generic result for any MCP operation

] 