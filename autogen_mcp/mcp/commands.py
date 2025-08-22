"""
Generic command objects for any MCP operations.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List


@dataclass
class MCPCommand:
    """Generic command for any MCP tool execution."""
    
    tool_name: str
    server_name: str
    parameters: Dict[str, Any]
    
    def __str__(self) -> str:
        """String representation of the MCP command."""
        return f"MCP:{self.server_name}:{self.tool_name}({self.parameters})"
    
    @classmethod
    def from_text(cls, command_text: str, server_name: str = None, tool_name: str = None) -> "MCPCommand":
        """Parse generic MCP command from text."""
        # This is just a basic parser - can be extended for specific formats
        return cls(
            tool_name=tool_name or "generic_tool",
            server_name=server_name or "default",
            parameters={"query": command_text.strip()}
        )


@dataclass 
class ToolDefinition:
    """Definition of an available MCP tool."""
    
    name: str
    server: str
    description: Optional[str] = None
    parameters_schema: Optional[Dict[str, Any]] = None
    endpoint: Optional[str] = None
    
    def __str__(self) -> str:
        return f"{self.server}:{self.name}"


 