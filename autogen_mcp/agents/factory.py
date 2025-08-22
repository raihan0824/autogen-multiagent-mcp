"""
Agent factory for creating and managing AutoGen agents with native MCP support.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import ChatAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelInfo

# Use AutoGen's native MCP support with SSE for standardized MCP servers
from autogen_ext.tools.mcp import SseServerParams, mcp_server_tools

from ..config.settings import AgentDefinition, LLMSettings

logger = logging.getLogger(__name__)

class AgentFactory:
    """Factory for creating different types of agents with native AutoGen MCP support."""
    
    def __init__(self, mcp_settings, agents_config):
        """Initialize the factory with MCP settings and agents configuration."""
        self.agents_config = agents_config
        self.mcp_settings = mcp_settings
        
        # Store native AutoGen MCP tools
        self.native_mcp_tools = {}
        self._cached_tools = None

    async def _get_native_mcp_tools(self, server_configs: List[Dict[str, Any]]) -> Dict[str, List]:
        """Get tools using AutoGen's native MCP support with SSE transport."""
        all_tools = {}
        
        for server_config in server_configs:
            if not server_config.enabled:
                continue
                
            server_name = server_config.name
            server_url = server_config.url
            
            try:
                # Create SSE server parameters for standard MCP servers
                # Use the SSE endpoint from server configuration
                sse_url = f"{server_url}{server_config.sse_endpoint}"
                
                server_params = SseServerParams(
                    url=sse_url,
                    timeout=server_config.timeout_seconds,
                    sse_read_timeout=300  # 5 minutes for long operations
                )
                
                logger.info(f"Connecting to MCP server {server_name} at {sse_url}")
                
                # Use AutoGen's native MCP tool discovery
                tools = await mcp_server_tools(server_params)
                
                # Apply server-level tool filtering
                server_tools = server_config.tools
                if not server_tools or server_tools == ['*']:
                    # Use all tools
                    filtered_tools = tools
                else:
                    # Filter to only specified tools
                    filtered_tools = [tool for tool in tools if tool.name in server_tools]
                
                all_tools[server_name] = filtered_tools
                logger.info(f"Discovered {len(filtered_tools)} tools from {server_name} using native AutoGen MCP")
                
            except Exception as e:
                logger.error(f"Failed to connect to MCP server {server_name} at {server_url}: {e}")
                all_tools[server_name] = []
        
        return all_tools

    async def get_available_tools(self) -> Dict[str, Any]:
        """Get all available tools using AutoGen's native MCP support."""
        if self._cached_tools is None:
            # Use native AutoGen MCP support instead of custom client
            server_configs = []
            if hasattr(self.mcp_settings, 'servers'):
                server_configs = self.mcp_settings.servers
            elif isinstance(self.mcp_settings, dict) and 'servers' in self.mcp_settings:
                server_configs = self.mcp_settings['servers']
            
            self.native_mcp_tools = await self._get_native_mcp_tools(server_configs)
            
            # Convert to the expected format for backward compatibility
            tools_dict = {}
            for server_name, tools in self.native_mcp_tools.items():
                for tool in tools:
                    tools_dict[tool.name] = {
                        "name": tool.name,
                        "description": getattr(tool, 'description', ''),
                        "server": server_name,
                        "tool_obj": tool  # Store the actual AutoGen tool object
                    }
            
            self._cached_tools = {"tools": tools_dict}
            logger.info(f"Total tools available via native AutoGen MCP: {len(tools_dict)}")
        
        return self._cached_tools

    def _tool_available_to_agent(self, tool_info: Dict[str, Any], agent_def: AgentDefinition) -> bool:
        """Check if a tool is available to a specific agent."""
        # All tools are available to all agents with mcp capability
        if not any(cap in agent_def.capabilities for cap in ["mcp"]):
            return False

        return True

    def _filter_tools_for_agent(self, agent_def: AgentDefinition, available_tools: Dict[str, Any]) -> List:
        """Filter tools for a specific agent and return AutoGen tool objects."""
        if not available_tools or "tools" not in available_tools:
            return []

        tools_dict = available_tools["tools"]
        agent_tools = []

        # Get agent's tool configuration
        agent_tool_filter = getattr(agent_def, 'mcp_tools', ['*'])
        
        for tool_name, tool_info in tools_dict.items():
            # Check if tool is available to this agent
            if not self._tool_available_to_agent(tool_info, agent_def):
                continue
            
            # Apply agent-level tool filtering
            if agent_tool_filter == ['*'] or not agent_tool_filter:
                # Agent wants all available tools
                include_tool = True
            else:
                # Agent wants only specific tools
                include_tool = tool_name in agent_tool_filter
            
            if include_tool and 'tool_obj' in tool_info:
                agent_tools.append(tool_info['tool_obj'])

        logger.info(f"Agent {agent_def.name} gets {len(agent_tools)} tools after filtering")
        return agent_tools

    async def create_agent(self, agent_def: AgentDefinition) -> Optional[ChatAgent]:
        """Create an agent using AutoGen's native MCP support."""
        try:
            # Get available tools
            available_tools = await self.get_available_tools()
            
            # Filter tools for this specific agent
            agent_tools = self._filter_tools_for_agent(agent_def, available_tools)
            
            # Get LLM settings from configuration
            from ..config.loader import load_configuration
            config = load_configuration()
            llm_settings = config.llm
            
            # Create model client
            model_info = ModelInfo(vision=False, function_calling=True, json_output=False, family="unknown")
            model_client = OpenAIChatCompletionClient(
                model=llm_settings.model_name,
                base_url=llm_settings.api_base_url.rstrip('/'),
                api_key=llm_settings.api_key,
                model_info=model_info,
                parallel_tool_calls=False  # Disable parallel calls for MCP stability
            )
            
            # Create agent with native AutoGen MCP tools and multi-turn capabilities
            agent = AssistantAgent(
                name=agent_def.name,
                model_client=model_client,
                tools=agent_tools,  # Native AutoGen MCP tools
                system_message=agent_def.system_message,
                description=f"Agent {agent_def.name} with {len(agent_tools)} MCP tools",
                reflect_on_tool_use=True,  # Agent reflects on tool results
                max_tool_iterations=5  # Allow up to 5 tool execution attempts
            )
            
            logger.info(f"Created agent: {agent_def.name} ({agent_def.agent_type}) with {len(agent_tools)} native MCP tools and multi-turn capability")
            return agent
            
        except Exception as e:
            logger.error(f"Failed to create agent {agent_def.name}: {e}")
            return None

    # Keep this method for backward compatibility
    async def create_agent_from_definition(self, agent_def: AgentDefinition) -> Optional[ChatAgent]:
        """Create agent from definition - alias for create_agent."""
        return await self.create_agent(agent_def)

    def create_all_enabled_agents(self) -> Dict[str, ChatAgent]:
        """Create all enabled agents and return them as a dictionary."""
        agents = {}
        enabled_agents = self.agents_config.get_enabled_agents()
        
        for agent_def in enabled_agents:
            try:
                # Note: This is a sync method, but create_agent is async
                # We need to handle this properly
                import asyncio
                agent = asyncio.run(self.create_agent(agent_def))
                if agent:
                    agents[agent_def.name] = agent
                    logger.info(f"Created enabled agent: {agent_def.name}")
            except Exception as e:
                logger.error(f"Failed to create enabled agent {agent_def.name}: {e}")
        
        return agents

    
    def create_agent_team(self) -> Dict[str, ChatAgent]:
        """Create a complete team of agents from configuration - backward compatibility."""
        # This method is synchronous but needs to call async methods
        # For now, return empty dict and let the orchestrator handle async creation
        logger.warning("create_agent_team called - use async agent creation instead")
        return {} 