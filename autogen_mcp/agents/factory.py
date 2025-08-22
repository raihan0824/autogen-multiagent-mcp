"""
Agent factory for creating and managing AutoGen agents.
"""

import logging
import re
from typing import Dict, Any, List, Optional

from autogen_agentchat.agents import AssistantAgent

from ..config import AppConfig, AgentDefinition
from ..mcp import MCPToolsClient, MCPCommand
from .base import AgentBase

logger = logging.getLogger(__name__)


class ConfigurableAgent(AgentBase):
    """Agent created from configuration definition."""
    
    def __init__(self, agent_definition: AgentDefinition, llm_settings, tools=None):
        self.agent_definition = agent_definition
        self.tools = tools or []
        super().__init__(agent_definition.name, llm_settings)
    
    def _create_agent(self) -> AssistantAgent:
        """Create agent from definition."""
        return AssistantAgent(
            name=self.name,
            model_client=self.model_client,
            system_message=self.get_system_message(),
            tools=self.tools if self.tools else None
        )
    
    def get_system_message(self) -> str:
        """Get system message from definition."""
        return self.agent_definition.system_message
    
    def parse_mcp_command(self, message_content: str) -> Optional[MCPCommand]:
        """Parse generic MCP command from agent message."""
        # Look for EXECUTE_MCP pattern
        if "EXECUTE_MCP:" not in message_content:
            return None
            
        try:
            # Extract command after EXECUTE_MCP:
            command_start = message_content.find("EXECUTE_MCP:") + len("EXECUTE_MCP:")
            command_text = message_content[command_start:].strip()
            
            # Parse different command formats:
            
            # Format 1: "server:tool:params" -> MCP:postgres:sql_query:SELECT * FROM users
            if command_text.startswith("MCP:") and command_text.count(":") >= 2:
                parts = command_text[4:].split(":", 2)  # Remove "MCP:" prefix
                server_name = parts[0]
                tool_name = parts[1] 
                params_text = parts[2] if len(parts) > 2 else ""
                
                # Parse parameters (could be JSON or simple text)
                try:
                    import json
                    parameters = json.loads(params_text)
                except:
                    parameters = {"query": params_text}
                
                return MCPCommand(
                    tool_name=tool_name,
                    server_name=server_name,
                    parameters=parameters
                )
            

            
            # Format 3: Generic "server_name.tool_name params"
            elif "." in command_text.split()[0]:
                parts = command_text.split(maxsplit=1)
                tool_spec = parts[0]
                params_text = parts[1] if len(parts) > 1 else ""
                
                if "." in tool_spec:
                    server_name, tool_name = tool_spec.split(".", 1)
                    return MCPCommand(
                        tool_name=tool_name,
                        server_name=server_name,
                        parameters={"query": params_text}
                    )
            
            # Format 4: Auto-detect from available tools
            else:
                # Try to match against available tools
                words = command_text.lower().split()
                
                for tool_name, tool_info in self._available_tools.get("tools", {}).items():
                    if any(word in tool_name.lower() for word in words):
                        server_name = tool_info.get("server", "default")
                        return MCPCommand(
                            tool_name=tool_name,
                            server_name=server_name,
                            parameters={"query": command_text}
                        )
                
                # Default fallback - assume first available server
                available_tools = self._available_tools.get("tools", {})
                if available_tools:
                    first_tool = next(iter(available_tools.values()))
                    return MCPCommand(
                        tool_name="generic_query",
                        server_name=first_tool.get("server", "default"),
                        parameters={"query": command_text}
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to parse MCP command: {e}")
            return None


class AgentFactory:
    """Factory for creating and managing agents with MCP integration."""
    
    def __init__(self, config: AppConfig, mcp_client: MCPToolsClient):
        self.config = config
        self.mcp_client = mcp_client
        self._available_tools = {}
        
    async def initialize_tools(self) -> None:
        """Initialize and discover tools from MCP servers with agent-level filtering."""
        try:
            # Discover tools from all MCP servers
            if self.config.mcp.auto_discover_tools:
                discovered_tools = await self.mcp_client.discover_tools()
                self._available_tools = discovered_tools
                logger.info(f"Discovered {len(discovered_tools.get('tools', {}))} MCP tools")
            else:
                logger.info("Tool auto-discovery is disabled")
                self._available_tools = {"tools": {}}
        except Exception as e:
            logger.error(f"Failed to discover MCP tools: {e}")
            self._available_tools = {"tools": {}}

    def filter_tools_for_agent(self, agent_def: AgentDefinition) -> Dict[str, Any]:
        """Filter available tools based on agent's tool preferences."""
        all_tools = self._available_tools.get("tools", {})
        
        # If agent has no tool filter, return all available tools
        if not hasattr(agent_def, 'mcp_tools') or not agent_def.mcp_tools:
            logger.info(f"Agent {agent_def.name} gets ALL available tools (no filter specified)")
            return {"tools": all_tools}
        
        # If agent specifies "*", return all tools
        if "*" in agent_def.mcp_tools:
            logger.info(f"Agent {agent_def.name} gets ALL available tools (wildcard * specified)")
            return {"tools": all_tools}
        
        # Filter tools based on agent's preferences
        filtered_tools = {}
        for tool_name in agent_def.mcp_tools:
            if tool_name in all_tools:
                filtered_tools[tool_name] = all_tools[tool_name]
                logger.info(f"Agent {agent_def.name} gets tool: {tool_name}")
            else:
                logger.warning(f"Agent {agent_def.name} requested tool '{tool_name}' but it's not available")
        
        logger.info(f"Agent {agent_def.name} gets {len(filtered_tools)} filtered tools from {len(all_tools)} available")
        return {"tools": filtered_tools}
    
    def get_tools_for_agent(self, agent_def: AgentDefinition) -> List[Dict[str, Any]]:
        """Get available tools for a specific agent based on its configuration."""
        # For now, don't pass MCP tools as AutoGen tools since they need different handling
        # MCP tools will be handled through the MCP execution logic in the orchestrator
        agent_tools = []
        available_tools = self._available_tools.get("tools", {})
        
        # Store MCP tools separately for the agent (for reference and execution)
        agent_def._mcp_tools = []
        
        # If agent specifies specific tools, validate them
        if agent_def.tools:
            for tool_name in agent_def.tools:
                if tool_name in available_tools:
                    tool_info = available_tools[tool_name]
                    # Check if agent can use this tool
                    if self._can_agent_use_tool(agent_def, tool_info):
                        agent_def._mcp_tools.append(tool_info)
                        logger.info(f"Agent {agent_def.name} can use tool: {tool_name}")
                    else:
                        logger.warning(f"Agent {agent_def.name} cannot use tool {tool_name} (insufficient capabilities)")
                else:
                    logger.warning(f"Tool {tool_name} specified for agent {agent_def.name} but not found in available tools")
        
        # Auto-assign tools based on capabilities
        else:
            for tool_name, tool_info in available_tools.items():
                if self._can_agent_use_tool(agent_def, tool_info):
                    agent_def._mcp_tools.append(tool_info)
                    logger.info(f"Auto-assigned tool {tool_name} to agent {agent_def.name}")
        
        # Return empty list for AutoGen tools (we'll handle MCP tools through orchestrator)
        return agent_tools
    
    def _can_agent_use_tool(self, agent_def: AgentDefinition, tool_info: Dict[str, Any]) -> bool:
        """Check if an agent can use a specific tool."""
        # Check required capabilities
        required_caps = tool_info.get("required_capabilities", [])
        if required_caps:
            if not any(cap in agent_def.capabilities for cap in required_caps):
                return False
        
        # All tools are available to all agents with mcp capability
        if not any(cap in agent_def.capabilities for cap in ["mcp"]):
            return False
        
        return True
    
    def create_agent_from_definition(self, agent_def: AgentDefinition) -> AgentBase:
        """Create an agent instance from definition - legacy method name."""
        return self.create_agent(agent_def)
    
    def create_agent(self, agent_def: AgentDefinition) -> AgentBase:
        """Create an agent instance from definition with filtered tools."""
        try:
            # Get filtered tools for this specific agent
            agent_tools = self.filter_tools_for_agent(agent_def)
            
            # Auto-assign tools to agent if they match server tools
            if hasattr(agent_def, 'mcp_servers') and agent_def.mcp_servers:
                for tool_name in agent_tools.get("tools", {}):
                    tool_info = agent_tools["tools"][tool_name]
                    server_name = tool_info.get("server", "unknown")
                    if server_name in agent_def.mcp_servers:
                        logger.info(f"Auto-assigned tool {tool_name} to agent {agent_def.name}")
            
            # Create agent with filtered tools
            agent = ConfigurableAgent(
                agent_definition=agent_def,
                llm_settings=self.config.llm,
                tools=[]  # Don't pass MCP tools to AutoGen - handle separately
            )
            
            # Store MCP tools separately for our framework
            agent.mcp_tools = agent_tools
            
            # Add MCP command parsing capability
            agent.parse_mcp_command = self._create_mcp_parser(agent_tools)
            
            logger.info(f"Created agent: {agent_def.name} ({agent_def.agent_type}) with {len(agent_tools.get('tools', {}))} tools")
            return agent
            
        except Exception as e:
            logger.error(f"Failed to create agent {agent_def.name}: {e}")
            raise
    
    def _create_mcp_parser(self, available_tools: Dict[str, Any]):
        """Create MCP command parser for an agent with its available tools."""
        def parse_mcp_command(message_content: str) -> Optional[MCPCommand]:
            """Parse generic MCP command from agent message."""
            # Look for EXECUTE_MCP pattern
            if "EXECUTE_MCP:" not in message_content:
                return None
            
            try:
                # Extract command after EXECUTE_MCP:
                command_start = message_content.find("EXECUTE_MCP:") + len("EXECUTE_MCP:")
                command_text = message_content[command_start:].strip()
                
                # Parse different command formats:
                
                # Format 1: "server:tool:params" -> MCP:postgres:sql_query:SELECT * FROM users
                if command_text.startswith("MCP:") and command_text.count(":") >= 2:
                    parts = command_text[4:].split(":", 2)  # Remove "MCP:" prefix
                    server_name = parts[0]
                    tool_name = parts[1] 
                    params_text = parts[2] if len(parts) > 2 else ""
                    
                    # Parse parameters (could be JSON or simple text)
                    try:
                        import json
                        parameters = json.loads(params_text)
                    except:
                        parameters = {"query": params_text}
                    
                    return MCPCommand(
                        tool_name=tool_name,
                        server_name=server_name,
                        parameters=parameters
                    )
                

                
                # Format 3: Generic "tool_name args" 
                else:
                    # Generic command parsing - no hardcoded tool-specific logic
                    parts = command_text.split()
                    tool_name = parts[0]
                    
                    # Generic parameter parsing - try to extract common patterns
                    if len(parts) > 1:
                        # Look for -n namespace pattern (common in many tools)
                        namespace = None
                        resource = None
                        remaining_args = []
                        
                        i = 1
                        while i < len(parts):
                            if parts[i] == "-n" and i + 1 < len(parts):
                                namespace = parts[i + 1]
                                i += 2
                            elif not resource and not parts[i].startswith("-"):
                                resource = parts[i]
                                i += 1
                            else:
                                remaining_args.append(parts[i])
                                i += 1
                        
                        # Create flexible parameters that work with different MCP servers
                        structured_params = {}
                        if resource:
                            structured_params["resourceType"] = resource
                        if namespace:
                            structured_params["namespace"] = namespace
                        if remaining_args:
                            structured_params["args"] = " ".join(remaining_args)
                        
                        # Also include the raw command for servers that prefer it
                        structured_params["query"] = " ".join(parts[1:])
                    else:
                        structured_params = {}
                    
                    # Find the server that has this tool dynamically - NO DEFAULTS!
                    server_name = None
                    
                    # Handle nested structure: available_tools = {"tools": {tool_name: tool_info}}
                    tools_dict = available_tools.get("tools", {}) if available_tools else {}
                    
                    if tools_dict and tool_name in tools_dict:
                        server_name = tools_dict[tool_name].get("server")
                    
                    # If not found, use the first available server from any tool
                    if not server_name:
                        for tool_info in tools_dict.values():
                            if "server" in tool_info:
                                server_name = tool_info["server"]
                                break
                    
                    # If still no server found, this is an error
                    if not server_name:
                        raise ValueError(f"No MCP server found for tool '{tool_name}'")
                    
                    return MCPCommand(
                        tool_name=tool_name,
                        server_name=server_name,
                        parameters=structured_params
                    )
            
            except Exception as e:
                logger.error(f"Failed to parse MCP command: {e}")
                return None
        
        return parse_mcp_command
    

    

    

    
    def create_agent_team(self) -> Dict[str, AgentBase]:
        """Create a complete team of agents from configuration."""
        team = {}
        
        # Get enabled agents from configuration
        enabled_agents = self.config.agents.get_enabled_agents()
        
        if not enabled_agents:
            logger.warning("No enabled agents found in configuration")
            return team
        
        # Create agents from definitions
        for agent_def in enabled_agents:
            try:
                agent = self.create_agent_from_definition(agent_def)
                team[agent_def.name] = agent
                logger.info(f"Created agent: {agent_def.name} ({agent_def.agent_type})")
            except Exception as e:
                logger.error(f"Failed to create agent {agent_def.name}: {e}")
                continue
        
        return team
    
    def create_conversation_flow_agents(self) -> List[AgentBase]:
        """Create agents in conversation flow order."""
        agents = []
        flow_agent_defs = self.config.agents.get_conversation_flow_agents()
        
        for agent_def in flow_agent_defs:
            try:
                agent = self.create_agent_from_definition(agent_def)
                agents.append(agent)
                logger.info(f"Added agent to flow: {agent_def.name}")
            except Exception as e:
                logger.error(f"Failed to create flow agent {agent_def.name}: {e}")
                continue
        
        return agents 

    def create_all_enabled_agents(self) -> Dict[str, AgentBase]:
        """Create all enabled agents."""
        agents = {}
        
        for agent_def in self.config.agents.agents:
            if agent_def.enabled:
                try:
                    agent = self.create_agent(agent_def)
                    agents[agent_def.name] = agent
                except Exception as e:
                    logger.error(f"Failed to create agent {agent_def.name}: {e}")
                    
        logger.info(f"Created {len(agents)} enabled agents")
        return agents 