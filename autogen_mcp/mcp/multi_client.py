"""
Generic multi-MCP client that can connect to any MCP servers.
Supports dynamic tool discovery and execution across multiple servers.
"""

import logging
from typing import List, Dict, Any, Optional

from ..config import MCPSettings, AgentSettings, MCPServerConfig
from .client import HTTPMCPClient, MCPClientError

logger = logging.getLogger(__name__)


class MultiMCPClient:
    """Client that manages multiple MCP servers of any type."""
    
    def __init__(self, mcp_settings: MCPSettings, agent_settings: AgentSettings):
        self.mcp_settings = mcp_settings
        self.agent_settings = agent_settings
        self.clients: Dict[str, HTTPMCPClient] = {}
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize connections to all enabled MCP servers."""
        if not self.mcp_settings.enabled:
            logger.warning("MCP is disabled")
            return
            
        enabled_servers = self.mcp_settings.get_enabled_servers()
        if not enabled_servers:
            logger.warning("No enabled MCP servers configured")
            return
            
        for server in enabled_servers:
            try:
                # Create individual MCP client for each server
                client = HTTPMCPClient(server)
                await client.initialize()
                self.clients[server.name] = client
                logger.info(f"Connected to MCP server: {server.name} ({server.url})")
            except Exception as e:
                logger.error(f"Failed to connect to MCP server {server.name}: {e}")
                
        self._initialized = True
        logger.info(f"Multi-MCP client initialized with {len(self.clients)} servers")
    
    async def discover_tools(self) -> Dict[str, Any]:
        """Discover tools from all connected servers."""
        all_tools = {}
        
        for server_name, client in self.clients.items():
            try:
                server_tools = await client.discover_tools()
                # Prefix tools with server name to avoid conflicts
                for tool_name, tool_info in server_tools.get("tools", {}).items():
                    tool_info["server"] = server_name
                    all_tools[tool_name] = tool_info
                    
                logger.info(f"Discovered {len(server_tools.get('tools', {}))} tools from {server_name}")
            except Exception as e:
                logger.error(f"Failed to discover tools from {server_name}: {e}")
        
        return {"tools": all_tools}
    
    async def execute_tool(self, tool_name: str, server_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute any tool on any MCP server."""
        if server_name not in self.clients:
            return {
                "success": False,
                "error": f"MCP server '{server_name}' not available",
                "tool": tool_name
            }
        
        try:
            client = self.clients[server_name]
            endpoint = f"/mcp/tools/{tool_name}/call"
            
            logger.info(f"Executing tool '{tool_name}' on server '{server_name}' with parameters: {parameters}")
            response = await client.send_request("POST", endpoint, parameters)
            
            if not response.success:
                return {
                    "success": False,
                    "error": response.error,
                    "tool": tool_name,
                    "server": server_name
                }
            
            # Extract content from MCP response
            result_content = self._extract_content(response.data)
            
            return {
                "success": True,
                "content": result_content,
                "tool": tool_name,
                "server": server_name,
                "raw_data": response.data
            }
            
        except Exception as e:
            logger.error(f"Failed to execute tool '{tool_name}' on server '{server_name}': {e}")
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name,
                "server": server_name
            }
    
    async def health_check(self) -> bool:
        """Check health of all servers."""
        if not self.clients:
            return False
            
        healthy_count = 0
        for server_name, client in self.clients.items():
            try:
                if await client.health_check():
                    healthy_count += 1
                else:
                    logger.warning(f"Server {server_name} health check failed")
            except Exception as e:
                logger.error(f"Health check failed for {server_name}: {e}")
        
        return healthy_count > 0  # At least one server is healthy
    
    def is_connected(self) -> bool:
        """Check if any clients are connected."""
        return len(self.clients) > 0
    
    async def close(self) -> None:
        """Close all client connections."""
        for server_name, client in self.clients.items():
            try:
                await client.close()
                logger.info(f"Closed connection to {server_name}")
            except Exception as e:
                logger.error(f"Error closing connection to {server_name}: {e}")
        
        self.clients.clear()
        self._initialized = False

    def _extract_content(self, response_data: Dict[str, Any]) -> str:
        """Extract content from any MCP response format."""
        if isinstance(response_data, dict):
            if "content" in response_data:
                content = response_data["content"]
                if isinstance(content, list) and content:
                    # Get text from the first content item
                    first_item = content[0]
                    if isinstance(first_item, dict) and "text" in first_item:
                        return first_item["text"]
                elif isinstance(content, str):
                    return content
            elif "text" in response_data:
                return response_data["text"]
            elif "result" in response_data:
                return str(response_data["result"])
        
        return str(response_data) 


class MCPToolsClient(MultiMCPClient):
    """Generic MCP client that can execute any tools from any servers."""
    
    # No hardcoded methods! Only generic tool execution via execute_tool()
    pass 