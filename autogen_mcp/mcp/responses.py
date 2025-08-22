"""
Response objects for MCP operations.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class MCPResponse:
    """Standard MCP response."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status_code: Optional[int] = None


@dataclass
class MCPOperationResult:
    """Generic result for any MCP tool execution on any server."""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    tool_name: Optional[str] = None
    server_name: Optional[str] = None
    command: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


 