"""
Configuration settings and data models.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class LLMSettings:
    """Settings for Language Model configuration."""
    model_name: str
    api_base_url: str
    api_key: str
    timeout_seconds: int
    temperature: float
    max_tokens: int
    model_family: str
    supports_function_calling: bool = True
    supports_json_output: bool = True
    supports_vision: bool = False


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server."""
    name: str
    url: str
    enabled: bool = True
    timeout_seconds: int = 30  # Keep reasonable default
    api_key: Optional[str] = None
    retry_attempts: int = 3  # Keep reasonable default
    retry_delay_seconds: float = 1.0  # Keep reasonable default
    tools: List[str] = field(default_factory=list)
    health_endpoint: str = "/health"
    tools_endpoint: str = "/mcp/tools"
    sse_endpoint: str = "/mcp-server/sse"


@dataclass
class MCPSettings:
    """Settings for MCP integration."""
    enabled: bool = True
    servers: List[MCPServerConfig] = field(default_factory=list)
    auto_discover_tools: bool = True

    def add_server(self, server: MCPServerConfig) -> None:
        """Add an MCP server."""
        self.servers.append(server)

    def get_server(self, name: str) -> Optional[MCPServerConfig]:
        """Get server by name."""
        for server in self.servers:
            if server.name == name:
                return server
        return None

    def get_enabled_servers(self) -> List[MCPServerConfig]:
        """Get all enabled servers."""
        return [server for server in self.servers if server.enabled]


@dataclass
class AgentDefinition:
    """Definition of an agent configuration."""
    name: str
    agent_type: str = "custom"  # Remove hardcoded comment about specific types
    role: str = ""
    system_message: str = ""
    enabled: bool = True
    capabilities: List[str] = field(default_factory=list)
    order: int = 99  # Default low priority
    tools: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    _mcp_tools: List[Dict[str, Any]] = field(default_factory=list, init=False)


@dataclass
class AgentSettings:
    """Settings for agent configuration and behavior."""
    max_conversation_rounds: int = 0  # Will be set from environment or config
    allowed_namespaces: List[str] = field(default_factory=list)  # Will be set from environment or config
    enable_safety_checks: bool = True
    conversation_timeout_seconds: int = 0  # Will be set from environment or config
    agent_definitions: List[AgentDefinition] = field(default_factory=list)
    conversation_flow: List[str] = field(default_factory=list)  # Remove hardcoded default

    def add_agent(self, agent: AgentDefinition) -> None:
        """Add an agent definition."""
        self.agent_definitions.append(agent)

    def get_agent_by_name(self, name: str) -> Optional[AgentDefinition]:
        """Get agent definition by name."""
        for agent in self.agent_definitions:
            if agent.name == name:
                return agent
        return None

    def get_enabled_agents(self) -> List[AgentDefinition]:
        """Get all enabled agent definitions."""
        return [agent for agent in self.agent_definitions if agent.enabled]

    def get_auto_conversation_flow(self) -> List[str]:
        """Generate conversation flow automatically from agent order values."""
        enabled_agents = self.get_enabled_agents()
        # Sort by order field (ascending - lower order = higher priority)
        enabled_agents.sort(key=lambda x: x.order)
        return [agent.name for agent in enabled_agents]

    def get_conversation_flow_agents(self) -> List[AgentDefinition]:
        """Get agents in conversation flow order."""
        flow_agents = []
        # Use auto-generated flow if no custom flow is set
        flow = self.conversation_flow if self.conversation_flow else self.get_auto_conversation_flow()
        
        for agent_name in flow:
            agent = self.get_agent_by_name(agent_name)
            if agent and agent.enabled:
                flow_agents.append(agent)
        return flow_agents


@dataclass
class LoggingSettings:
    """Logging configuration."""
    
    level: str = "INFO"
    format_string: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_file_logging: bool = False
    log_file_path: Optional[Path] = None
    max_file_size_mb: int = 10
    backup_count: int = 5


@dataclass
class AppConfig:
    """Main application configuration."""
    
    llm: LLMSettings
    mcp: MCPSettings
    agents: AgentSettings = field(default_factory=AgentSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Validate LLM settings
        if not self.llm.api_key or self.llm.api_key == "your-api-key-here":
            errors.append("LLM API key is not configured")
        
        if not self.llm.api_base_url:
            errors.append("LLM API base URL is not configured")
            
        # Validate MCP settings
        if self.mcp.enabled and not self.mcp.servers:
            errors.append("At least one MCP server must be configured when MCP is enabled")
            
        # Validate agent settings
        if self.agents.max_conversation_rounds < 1:
            errors.append("Max conversation rounds must be at least 1")
            
        if not self.agents.allowed_namespaces:
            errors.append("At least one namespace must be allowed")
            
        # Validate agent definitions
        agent_names = [agent.name for agent in self.agents.agent_definitions]
        if len(agent_names) != len(set(agent_names)):
            errors.append("Duplicate agent names found in configuration")
            
        return errors 