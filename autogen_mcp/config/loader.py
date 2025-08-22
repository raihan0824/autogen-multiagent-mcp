"""
Configuration loading and validation utilities.
"""

import json
import logging
import os
from pathlib import Path
from typing import List, Any, Union, Optional

from .settings import AppConfig, LLMSettings, MCPSettings, AgentSettings, LoggingSettings, AgentDefinition, MCPServerConfig

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""
    pass


def _get_env_var(key: str, default: Any = None, required: bool = False, var_type: type = str) -> Any:
    """Get environment variable with type conversion and validation."""
    value = os.getenv(key, default)
    
    if required and value is None:
        raise ConfigurationError(f"Required environment variable '{key}' is not set")
    
    if value is None:
        return default
        
    # Type conversion
    if var_type == bool:
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes", "on")
    elif var_type == int:
        try:
            return int(value)
        except ValueError:
            raise ConfigurationError(f"Environment variable '{key}' must be an integer, got: {value}")
    elif var_type == float:
        try:
            return float(value)
        except ValueError:
            raise ConfigurationError(f"Environment variable '{key}' must be a float, got: {value}")
    elif var_type == list:
        if isinstance(value, list):
            return value
        return [item.strip() for item in str(value).split(",") if item.strip()]
    
    return value


def load_environment_file(env_file_path: Optional[Path] = None) -> None:
    """Load environment variables from .env file if it exists."""
    if env_file_path is None:
        env_file_path = Path(".env")
    
    if env_file_path.exists():
        try:
            # Try to import python-dotenv
            from dotenv import load_dotenv
            load_dotenv(env_file_path)
            logger.info(f"Loaded environment variables from {env_file_path}")
        except ImportError:
            logger.warning("python-dotenv not installed, skipping .env file loading")
        except Exception as e:
            logger.warning(f"Error loading .env file: {e}")


def load_llm_settings() -> LLMSettings:
    """Load LLM configuration from environment variables."""
    return LLMSettings(
        model_name=_get_env_var("AUTOGEN_LLM_MODEL", required=True),
        api_base_url=_get_env_var("AUTOGEN_LLM_API_BASE", required=True),
        api_key=_get_env_var("AUTOGEN_LLM_API_KEY", required=True),
        timeout_seconds=_get_env_var("AUTOGEN_LLM_TIMEOUT", required=True, var_type=int),
        temperature=_get_env_var("AUTOGEN_LLM_TEMPERATURE", 0.7, var_type=float),  # Keep reasonable default
        max_tokens=_get_env_var("AUTOGEN_LLM_MAX_TOKENS", 4096, var_type=int),  # Keep reasonable default
        model_family=_get_env_var("AUTOGEN_LLM_FAMILY", "qwen"),  # Keep reasonable default
        supports_function_calling=_get_env_var("AUTOGEN_LLM_FUNCTION_CALLING", True, var_type=bool),
        supports_json_output=_get_env_var("AUTOGEN_LLM_JSON_OUTPUT", True, var_type=bool),
        supports_vision=_get_env_var("AUTOGEN_LLM_VISION", False, var_type=bool)
    )


def load_mcp_settings() -> MCPSettings:
    """Load MCP configuration from environment variables."""
    settings = MCPSettings(
        auto_discover_tools=_get_env_var("AUTOGEN_MCP_AUTO_DISCOVER_TOOLS", True, var_type=bool),
        enabled=_get_env_var("AUTOGEN_MCP_ENABLED", True, var_type=bool)
    )
    
    # Load servers from configuration
    servers = load_mcp_servers()
    
    if not servers:
        # Add default server if no servers configured
        default_server = settings.get_default_server_config()
        # Override with environment variables if provided
        default_server.url = _get_env_var("AUTOGEN_MCP_SERVER_URL", default_server.url)
        default_server.timeout_seconds = _get_env_var("AUTOGEN_MCP_TIMEOUT", default_server.timeout_seconds, var_type=int)
        default_server.api_key = _get_env_var("AUTOGEN_MCP_API_KEY", default_server.api_key)
        servers.append(default_server)
    
    for server in servers:
        settings.add_server(server)
    
    return settings

def load_mcp_servers() -> List[MCPServerConfig]:
    """Load MCP server configurations from various sources."""
    servers = []
    
    # 1. Load from JSON file if specified
    servers_config_file = _get_env_var("AUTOGEN_MCP_SERVERS_CONFIG_FILE", "mcp_servers.json")
    if servers_config_file and Path(servers_config_file).exists():
        servers.extend(load_mcp_servers_from_json(servers_config_file))
    
    # 2. Load from environment variables
    servers.extend(load_mcp_servers_from_env())
    
    return servers

def load_mcp_servers_from_json(file_path: str) -> List[MCPServerConfig]:
    """Load MCP servers from JSON configuration file."""
    servers = []
    
    try:
        with open(file_path, 'r') as f:
            config = json.load(f)
        
        for server_config in config.get("servers", []):
            server = MCPServerConfig(
                name=server_config["name"],
                url=server_config["url"],
                enabled=server_config.get("enabled", True),
                timeout_seconds=server_config.get("timeout_seconds", 30),
                api_key=server_config.get("api_key"),
                retry_attempts=server_config.get("retry_attempts", 3),
                retry_delay_seconds=server_config.get("retry_delay_seconds", 1.0),
                tools=server_config.get("tools", []),
                health_endpoint=server_config.get("health_endpoint", "/health"),
                tools_endpoint=server_config.get("tools_endpoint", "/mcp/tools")
            )
            servers.append(server)
            logger.info(f"Loaded MCP server from JSON: {server.name}")
    
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to load MCP servers from {file_path}: {e}")
    
    return servers

def load_mcp_servers_from_env() -> List[MCPServerConfig]:
    """Load MCP servers from environment variables."""
    servers = []
    
    # Look for AUTOGEN_MCP_SERVER_* environment variables
    for env_var in os.environ:
        if env_var.startswith("AUTOGEN_MCP_SERVER_") and env_var.endswith("_CONFIG"):
            server_name = env_var.replace("AUTOGEN_MCP_SERVER_", "").replace("_CONFIG", "").lower()
            try:
                server_config = json.loads(os.environ[env_var])
                
                server = MCPServerConfig(
                    name=server_name,
                    url=server_config["url"],
                    enabled=server_config.get("enabled", True),
                    timeout_seconds=server_config.get("timeout_seconds", 30),
                    api_key=server_config.get("api_key"),
                    retry_attempts=server_config.get("retry_attempts", 3),
                    retry_delay_seconds=server_config.get("retry_delay_seconds", 1.0),
                    tools=server_config.get("tools", []),
                    health_endpoint=server_config.get("health_endpoint", "/health"),
                    tools_endpoint=server_config.get("tools_endpoint", "/mcp/tools")
                )
                
                servers.append(server)
                logger.info(f"Loaded MCP server from environment: {server_name}")
                
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to parse MCP server config {env_var}: {e}")
    
    return servers


def load_agents_from_json(config_path: str) -> List[AgentDefinition]:
    """Load agent definitions from JSON configuration file."""
    try:
        config_file = Path(config_path)
        if not config_file.exists():
            logger.info(f"Agent config file {config_path} not found, using defaults")
            return []
        
        with open(config_file, 'r') as f:
            agents_data = json.load(f)
        
        agents = []
        for agent_data in agents_data.get('agents', []):
            agent = AgentDefinition(
                name=agent_data['name'],
                agent_type=agent_data.get('agent_type', 'custom'),
                role=agent_data.get('role', agent_data['name']),
                system_message=agent_data['system_message'],
                enabled=agent_data.get('enabled', True),
                capabilities=agent_data.get('capabilities', []),
                order=agent_data.get('order', 99)
            )
            agents.append(agent)
        
        logger.info(f"Loaded {len(agents)} agents from {config_path}")
        return agents
        
    except Exception as e:
        logger.error(f"Error loading agents from {config_path}: {e}")
        return []


def load_agents_from_env() -> List[AgentDefinition]:
    """Load additional agent definitions from environment variables."""
    agents = []
    
    # Support for custom agents via environment variables
    # Format: AUTOGEN_CUSTOM_AGENT_<NAME>_CONFIG={"role": "...", "system_message": "...", ...}
    for key, value in os.environ.items():
        if key.startswith("AUTOGEN_CUSTOM_AGENT_") and key.endswith("_CONFIG"):
            try:
                # Extract agent name from environment variable
                agent_name = key.replace("AUTOGEN_CUSTOM_AGENT_", "").replace("_CONFIG", "").lower()
                
                # Parse JSON configuration
                agent_data = json.loads(value)
                
                agent = AgentDefinition(
                    name=agent_name,
                    agent_type=agent_data.get('agent_type', 'custom'),
                    role=agent_data.get('role', agent_name),
                    system_message=agent_data['system_message'],
                    enabled=agent_data.get('enabled', True),
                    capabilities=agent_data.get('capabilities', []),
                    order=agent_data.get('order', 50)
                )
                agents.append(agent)
                logger.info(f"Loaded custom agent {agent_name} from environment")
                
            except Exception as e:
                logger.error(f"Error loading custom agent from {key}: {e}")
    
    return agents


def load_agent_settings() -> AgentSettings:
    """Load agent configuration from environment variables and agents.json."""
    settings = AgentSettings(
        max_conversation_rounds=_get_env_var("AUTOGEN_MAX_ROUNDS", required=True, var_type=int),
        allowed_namespaces=_get_env_var("AUTOGEN_ALLOWED_NAMESPACES", required=True, var_type=list),
        enable_safety_checks=_get_env_var("AUTOGEN_ENABLE_SAFETY_CHECKS", True, var_type=bool),  # Keep reasonable default
        conversation_timeout_seconds=_get_env_var("AUTOGEN_CONVERSATION_TIMEOUT", required=True, var_type=int)
    )
    
    # Load agents from various sources (no more default hardcoded agents)
    additional_agents = []
    
    # 1. Load from JSON file if specified
    agents_config_file = _get_env_var("AUTOGEN_AGENTS_CONFIG_FILE", "agents.json")
    if agents_config_file:
        additional_agents.extend(load_agents_from_json(agents_config_file))
    
    # 2. Load from environment variables
    additional_agents.extend(load_agents_from_env())
    
    # Add additional agents to settings (these can override defaults if same name)
    for agent in additional_agents:
        # Check if agent with same name exists and replace it
        existing_agent = settings.get_agent_by_name(agent.name)
        if existing_agent:
            settings.agent_definitions.remove(existing_agent)
            logger.info(f"Replacing default agent '{agent.name}' with custom definition")
        settings.add_agent(agent)
    
    # 3. Load custom conversation flow if specified
    custom_flow = _get_env_var("AUTOGEN_CONVERSATION_FLOW", var_type=list)
    if custom_flow:
        settings.conversation_flow = custom_flow
        logger.info(f"Using custom conversation flow: {custom_flow}")
    else:
        # Auto-generate conversation flow from agent order if no custom flow provided
        auto_flow = settings.get_auto_conversation_flow()
        settings.conversation_flow = auto_flow
        logger.info(f"Using auto-generated conversation flow from agent order: {auto_flow}")

    logger.info(f"Loaded {len(settings.agent_definitions)} agents total")
    logger.info(f"Conversation flow: {settings.conversation_flow}")
    
    return settings


def load_logging_settings() -> LoggingSettings:
    """Load logging configuration from environment variables."""
    log_file_path = _get_env_var("AUTOGEN_LOG_FILE")
    return LoggingSettings(
        level=_get_env_var("AUTOGEN_LOG_LEVEL", "INFO"),
        format_string=_get_env_var("AUTOGEN_LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
        enable_file_logging=_get_env_var("AUTOGEN_LOG_TO_FILE", False, var_type=bool),
        log_file_path=Path(log_file_path) if log_file_path else None,
        max_file_size_mb=_get_env_var("AUTOGEN_LOG_MAX_SIZE_MB", 10, var_type=int),
        backup_count=_get_env_var("AUTOGEN_LOG_BACKUP_COUNT", 5, var_type=int)
    )


def load_configuration(env_file_path: Optional[Path] = None) -> AppConfig:
    """Load complete application configuration."""
    # Load environment file first
    load_environment_file(env_file_path)
    
    # Load all settings
    config = AppConfig(
        llm=load_llm_settings(),
        mcp=load_mcp_settings(),
        agents=load_agent_settings(),
        logging=load_logging_settings()
    )
    
    return config


def validate_configuration(config: AppConfig) -> None:
    """Validate configuration and raise exception if invalid."""
    errors = config.validate()
    
    if errors:
        error_message = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
        raise ConfigurationError(error_message) 