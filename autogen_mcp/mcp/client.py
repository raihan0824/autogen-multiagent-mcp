"""
Abstract MCP client interface and base implementation.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

import httpx

from ..config import MCPSettings
from .responses import MCPResponse

logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    """Base exception for MCP client errors."""
    pass


class MCPConnectionError(MCPClientError):
    """Raised when MCP server connection fails."""
    pass


class MCPClient(ABC):
    """Abstract base class for MCP clients."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize connection to MCP server."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if MCP server is healthy."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close connection and cleanup resources."""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if client is connected to server."""
        pass


class HTTPMCPClient(MCPClient):
    """HTTP-based MCP client implementation."""
    
    def __init__(self, server_config):
        # Handle both old MCPSettings and new MCPServerConfig
        if hasattr(server_config, 'url'):
            # New MCPServerConfig
            self.server_config = server_config
            self.settings = server_config  # For backward compatibility
        else:
            # Old MCPSettings - create a default server config
            from ..config import MCPServerConfig
            server_url = getattr(server_config, 'server_url', None)
            if not server_url:
                raise MCPClientError("Server URL is required - no default URL provided")
                
            self.server_config = MCPServerConfig(
                name="default",
                url=server_url,
                timeout_seconds=getattr(server_config, 'timeout_seconds', 30),
                api_key=getattr(server_config, 'api_key', None),
                retry_attempts=getattr(server_config, 'retry_attempts', 3),
                retry_delay_seconds=getattr(server_config, 'retry_delay_seconds', 1.0),
                health_endpoint=getattr(server_config, 'health_endpoint', '/health'),
                tools_endpoint=getattr(server_config, 'tools_endpoint', '/mcp/tools')
            )
            self.settings = self.server_config
            
        self._client: Optional[httpx.AsyncClient] = None
        self._connected = False
        
    async def initialize(self) -> None:
        """Initialize HTTP client and test connection."""
        if not self.server_config.enabled:
            logger.warning(f"MCP server {self.server_config.name} is disabled")
            return
        
        if not self.server_config.url:
            raise MCPClientError(f"Server URL is required for {self.server_config.name}")
            
        self._client = httpx.AsyncClient(
            base_url=self.server_config.url,
            timeout=httpx.Timeout(self.server_config.timeout_seconds),
            headers=self._build_headers()
        )
        
        # Test connection
        for attempt in range(self.server_config.retry_attempts):
            try:
                await self.health_check()
                self._connected = True
                logger.info(f"Connected to MCP server: {self.server_config.url}")
                return
            except Exception as e:
                if attempt == self.server_config.retry_attempts - 1:
                    raise MCPConnectionError(f"Failed to connect to MCP server after {self.server_config.retry_attempts} attempts: {e}")
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(self.server_config.retry_delay_seconds)
    
    async def health_check(self) -> bool:
        """Check MCP server health."""
        if not self._client:
            return False
            
        try:
            response = await self._client.get(self.server_config.health_endpoint)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def send_request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> MCPResponse:
        """Send HTTP request to MCP server."""
        if not self._client:
            raise MCPClientError("Client not initialized")
            
        try:
            kwargs = {"url": endpoint}
            if data:
                kwargs["json"] = data
                
            response = await self._client.request(method, **kwargs)
            
            return MCPResponse(
                success=response.status_code < 400,
                data=response.json() if response.content else {},
                error=response.text if response.status_code >= 400 else None,
                status_code=response.status_code
            )
            
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return MCPResponse(
                success=False,
                data={},
                error=str(e)
            )
    
    async def discover_tools(self) -> Dict[str, Any]:
        """Discover available tools from the MCP server using standard MCP protocol."""
        try:
            # First, discover ALL available tools from the server
            all_discovered_tools = {}
            
            # Try standard MCP tools/list endpoints
            tools_endpoints = [
                f"{self.server_config.url}/mcp/tools/list",
                f"{self.server_config.url}/mcp/tools", 
                f"{self.server_config.url}/tools/list",
                f"{self.server_config.url}/tools",
                f"{self.server_config.url}/api/tools",
                f"{self.server_config.tools_endpoint}"
            ]
            
            for endpoint in tools_endpoints:
                try:
                    logger.info(f"Trying tool discovery endpoint: {endpoint}")
                    response = await self.send_request("GET", endpoint)
                    
                    if response.success and response.data:
                        tools_data = response.data
                        
                        # Handle different response formats
                        if isinstance(tools_data, dict):
                            # Format 1: {tools: [{name: "tool1"}, ...]}
                            if "tools" in tools_data:
                                tools_list = tools_data["tools"]
                                if isinstance(tools_list, list):
                                    for tool in tools_list:
                                        if isinstance(tool, dict) and "name" in tool:
                                            tool_name = tool["name"]
                                            all_discovered_tools[tool_name] = {
                                                "name": tool_name,
                                                "endpoint": f"{self.server_config.tools_endpoint}/{tool_name}/call",
                                                "method": "POST",
                                                "available": True,
                                                "description": tool.get("description", ""),
                                                "schema": tool.get("inputSchema", {})
                                            }
                                            logger.info(f"Discovered tool: {tool_name}")
                            
                            # Format 2: {tool1: {...}, tool2: {...}}
                            else:
                                for key, value in tools_data.items():
                                    if isinstance(value, dict):
                                        # Check if this is a nested structure like {"server_name": {"tools": [...]}}
                                        if "tools" in value and isinstance(value["tools"], list):
                                            # Nested format - extract tools from the nested structure
                                            for tool in value["tools"]:
                                                if isinstance(tool, dict) and "name" in tool:
                                                    tool_name = tool["name"]
                                                    all_discovered_tools[tool_name] = {
                                                        "name": tool_name,
                                                        "endpoint": f"{self.server_config.tools_endpoint}/{tool_name}/call",
                                                        "method": "POST",
                                                        "available": True,
                                                        "description": tool.get("description", ""),
                                                        "schema": tool.get("inputSchema", {})
                                                    }
                                                    logger.info(f"Discovered tool: {tool_name}")
                                                elif isinstance(tool, str):
                                                    # Tool name as string
                                                    all_discovered_tools[tool] = {
                                                        "name": tool,
                                                        "endpoint": f"{self.server_config.tools_endpoint}/{tool}/call",
                                                        "method": "POST",
                                                        "available": True,
                                                        "description": "",
                                                        "schema": {}
                                                    }
                                                    logger.info(f"Discovered tool: {tool}")
                                        elif key not in ["server", "status", "version"]:
                                            # Regular tool format
                                            all_discovered_tools[key] = {
                                                "name": key,
                                                "endpoint": f"{self.server_config.tools_endpoint}/{key}/call",
                                                "method": "POST", 
                                                "available": True,
                                                "description": value.get("description", ""),
                                                "schema": value.get("schema", {})
                                            }
                                            logger.info(f"Discovered tool: {key}")
                        
                        # Format 3: ["tool1", "tool2", ...]
                        elif isinstance(tools_data, list):
                            for item in tools_data:
                                if isinstance(item, str):
                                    all_discovered_tools[item] = {
                                        "name": item,
                                        "endpoint": f"{self.server_config.tools_endpoint}/{item}/call",
                                        "method": "POST",
                                        "available": True,
                                        "description": "",
                                        "schema": {}
                                    }
                                    logger.info(f"Discovered tool: {item}")
                                elif isinstance(item, dict) and "name" in item:
                                    tool_name = item["name"]
                                    all_discovered_tools[tool_name] = {
                                        "name": tool_name,
                                        "endpoint": f"{self.server_config.tools_endpoint}/{tool_name}/call",
                                        "method": "POST",
                                        "available": True,
                                        "description": item.get("description", ""),
                                        "schema": item.get("schema", {})
                                    }
                                    logger.info(f"Discovered tool: {tool_name}")
                        
                        if all_discovered_tools:
                            logger.info(f"Successfully discovered {len(all_discovered_tools)} tools from endpoint: {endpoint}")
                            break  # Found tools, stop trying other endpoints
                
                except Exception as e:
                    logger.debug(f"Tool discovery failed for endpoint {endpoint}: {e}")
                    continue
            
            # Now apply tool filtering based on server configuration
            if hasattr(self.server_config, 'tools') and self.server_config.tools:
                if "*" in self.server_config.tools:
                    # Use ALL discovered tools
                    logger.info(f"Using ALL {len(all_discovered_tools)} discovered tools (wildcard * specified)")
                    return {"tools": all_discovered_tools}
                else:
                    # Use only specified tools that were discovered
                    filtered_tools = {}
                    for tool_name in self.server_config.tools:
                        if tool_name in all_discovered_tools:
                            filtered_tools[tool_name] = all_discovered_tools[tool_name]
                            logger.info(f"Using specified tool: {tool_name}")
                        else:
                            # Tool specified but not discovered - add it anyway (might exist)
                            filtered_tools[tool_name] = {
                                "name": tool_name,
                                "endpoint": f"{self.server_config.tools_endpoint}/{tool_name}/call",
                                "method": "POST",
                                "available": True,
                                "description": f"Tool from server configuration",
                                "schema": {}
                            }
                            logger.warning(f"Tool '{tool_name}' specified in config but not discovered - adding anyway")
                    
                    logger.info(f"Using {len(filtered_tools)} filtered tools from {len(all_discovered_tools)} discovered")
                    return {"tools": filtered_tools}
            else:
                # No tools config - use all discovered tools
                if all_discovered_tools:
                    logger.info(f"Using ALL {len(all_discovered_tools)} discovered tools (no tools filter specified)")
                    return {"tools": all_discovered_tools}
            
            # If nothing was discovered and no config fallback, return empty
            logger.warning(f"No tools discovered for server {self.server_config.name}")
            return {"tools": {}}
            
        except Exception as e:
            logger.error(f"Failed to discover tools: {e}")
            return {"tools": {}}
    
    async def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get schema/documentation for a specific tool."""
        try:
            # Try to get tool schema if available
            response = await self.send_request("GET", f"{self.server_config.tools_endpoint}/{tool_name}")
            if response.success:
                return response.data
            return None
        except Exception as e:
            logger.error(f"Failed to get schema for tool {tool_name}: {e}")
            return None
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            self._connected = False
            logger.info("MCP client connection closed")
    
    def is_connected(self) -> bool:
        """Check if connected to MCP server."""
        return self._connected
    
    def _build_headers(self) -> Dict[str, str]:
        """Build HTTP headers for requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if self.server_config.api_key:
            headers["Authorization"] = f"Bearer {self.server_config.api_key}"
            
        return headers 