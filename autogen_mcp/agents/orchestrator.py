"""
Agent orchestration workflows with configurable multi-agent systems.
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod

from ..config import AppConfig
from ..mcp import MCPToolsClient, MCPCommand
from .factory import AgentFactory
from .base import AgentBase

logger = logging.getLogger(__name__)


@dataclass
class WorkflowMessage:
    """Message in agent workflow."""
    agent_name: str
    content: str
    mcp_result: Optional[Dict[str, Any]] = None  # Generic MCP result


@dataclass
class WorkflowResult:
    """Result of workflow execution."""
    success: bool
    messages: List[WorkflowMessage]
    error: Optional[str] = None


class Workflow(ABC):
    """Abstract base class for agent workflows."""
    
    @abstractmethod
    async def execute(self, query: str) -> WorkflowResult:
        """Execute the workflow with the given query."""
        pass


class SimpleWorkflow(Workflow):
    """Simple workflow that uses only the first available agent."""
    
    def __init__(self, config: AppConfig, agent_factory: AgentFactory, mcp_client: MCPToolsClient):
        self.config = config
        self.agent_factory = agent_factory
        self.mcp_client = mcp_client
        
        # Get the Kubernetes agent (or first available agent if not found)
        self.kubernetes_agent = self._get_kubernetes_agent()
    
    def _get_kubernetes_agent(self) -> AgentBase:
        """Get the Kubernetes agent or fallback to first available agent."""
        try:
            return self.agent_factory.create_kubernetes_agent()
        except Exception as e:
            logger.warning(f"Failed to create Kubernetes agent, using first available: {e}")
            agents = self.agent_factory.create_all_enabled_agents()
            if agents:
                return list(agents.values())[0]
            else:
                raise RuntimeError("No agents available")
    
    async def execute(self, query: str) -> WorkflowResult:
        """Execute query using the Kubernetes agent."""
        try:
            messages = []
            
            # Get initial agent response
            response = await self.kubernetes_agent.run_task(query)
            agent_message = response.messages[-1].content
            
            message = WorkflowMessage(
                agent_name=self.kubernetes_agent.name,
                content=agent_message
            )
            messages.append(message)
            
            # Process MCP commands if agent supports them
            if hasattr(self.kubernetes_agent, 'parse_mcp_command'):
                mcp_command = self.kubernetes_agent.parse_mcp_command(message.content)
                if mcp_command:
                    logger.info(f"Executing MCP command: {mcp_command}")
                    result = await self.mcp_client.execute_tool(
                        mcp_command.tool_name,
                        mcp_command.server_name,
                        mcp_command.parameters
                    )
                    message.mcp_result = result
                    
                    if result.get("success", False):
                        # Get agent to explain results
                        explanation_task = f"""Here are the real MCP results:

{result.get("content", "No content available")}

Please explain these results to the user in a helpful way, including:
1. What each resource is doing
2. The status of each resource
3. Any issues you notice
4. Best practices or recommendations"""

                        explanation_response = await self.kubernetes_agent.run_task(explanation_task)
                        explanation_message = WorkflowMessage(
                            agent_name=self.kubernetes_agent.name,
                            content=explanation_response.messages[-1].content
                        )
                        messages.append(explanation_message)
            
            return WorkflowResult(success=True, messages=messages)
            
        except Exception as e:
            logger.error(f"Error in simple workflow: {e}")
            return WorkflowResult(
                success=False,
                messages=[],
                error=str(e)
            )


class MultiAgentWorkflow(Workflow):
    """Multi-agent workflow with configurable agent team."""
    
    def __init__(self, config: AppConfig, agent_factory: AgentFactory, mcp_client: MCPToolsClient):
        self.config = config
        self.agent_factory = agent_factory
        self.mcp_client = mcp_client
        
        # Create agent team from configuration
        self.agents = self.agent_factory.create_agent_team()
        self.conversation_flow = self.config.agents.conversation_flow
        
        logger.info(f"Initialized multi-agent workflow with {len(self.agents)} agents")
        logger.info(f"Conversation flow: {self.conversation_flow}")
    
    async def execute(self, query: str) -> WorkflowResult:
        """Execute multi-agent workflow."""
        try:
            messages = []
            
            # Use configured conversation flow
            for round_num in range(self.config.agents.max_conversation_rounds):
                for agent_name in self.conversation_flow:
                    # Check if agent exists in our team
                    if agent_name not in self.agents:
                        logger.warning(f"Agent '{agent_name}' in conversation flow not found in team, skipping")
                        continue
                    
                    # Force termination after first complete round
                    if round_num > 0:
                        logger.info(f"Forcing workflow termination after {round_num} rounds")
                        return WorkflowResult(success=True, messages=messages)
                    
                    agent = self.agents[agent_name]
                    
                    # Create context for agent
                    if round_num == 0 and agent_name == self.conversation_flow[0]:
                        context = f"User query: {query}"
                    else:
                        context = self._create_context(messages, max_messages=3)
                    
                    # Get agent response
                    response = await agent.run_task(context)
                    agent_message = response.messages[-1].content
                    
                    message = WorkflowMessage(
                        agent_name=agent_name,
                        content=agent_message
                    )
                    messages.append(message)
                    
                    # Handle MCP execution for agents with mcp capabilities  
                    agent_def = self.config.agents.get_agent_by_name(agent_name)
                    if agent_def and "mcp" in agent_def.capabilities:
                                                 # Check for MCP commands in the response
                         if hasattr(agent, 'parse_mcp_command'):
                             mcp_command = agent.parse_mcp_command(agent_message)
                             if mcp_command:
                                 logger.info(f"Executing MCP command from {agent_name}: {mcp_command}")
                                 # Execute using generic MCP command
                                 result = await self.mcp_client.execute_tool(
                                     mcp_command.tool_name,
                                     mcp_command.server_name,
                                     mcp_command.parameters
                                 )
                                 message.mcp_result = result
                    
                    # Check for workflow termination
                    if self._should_terminate(agent_message, agent_name):
                        logger.info(f"Workflow terminated by agent {agent_name}")
                        return WorkflowResult(success=True, messages=messages)
            
            return WorkflowResult(success=True, messages=messages)
            
        except Exception as e:
            logger.error(f"Error in multi-agent workflow: {e}")
            return WorkflowResult(
                success=False,
                messages=[],
                error=str(e)
            )
    
    def _create_context(self, messages: List[WorkflowMessage], max_messages: int = 3) -> str:
        """Create context string from recent messages."""
        recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
        context_parts = []
        
        for msg in recent_messages:
            context_parts.append(f"{msg.agent_name}: {msg.content}")
            if msg.mcp_result:
                if msg.mcp_result.get("success", False):
                    context_parts.append(f"MCP Result: {msg.mcp_result.get('content', 'No content')}")
                else:
                    context_parts.append(f"MCP Error: {msg.mcp_result.get('error', 'Unknown error')}")
        
        return "\n".join(context_parts)
    
    def _should_terminate(self, message: str, agent_name: str) -> bool:
        """Check if workflow should terminate."""
        termination_phrases = [
            "APPROVED",
            "workflow completed",
            "task finished",
            "query resolved",
            "analysis complete",
            "monitoring complete",
            "recommendations provided"
        ]
        
        # Terminate after reviewer approval, monitoring completion, or if any agent indicates completion
        agent_definition = self.config.agents.get_agent_by_name(agent_name)
        if agent_definition:
            # Check if this is a terminating agent (reviewer, monitoring, or final agent in flow)
            is_terminating_agent = (
                "review" in agent_definition.capabilities or 
                "safety_review" in agent_definition.capabilities or
                "monitoring" in agent_definition.capabilities or
                agent_name == self.conversation_flow[-1]  # Last agent in flow
            )
            
            if is_terminating_agent:
                if any(phrase.lower() in message.lower() for phrase in termination_phrases):
                    return True
        
        return False


# Aliases for backward compatibility
MultiAgentWorkflow = MultiAgentWorkflow


class AgentOrchestrator:
    """Main orchestrator for agent workflows."""
    
    def __init__(self, config: AppConfig, mcp_client: MCPToolsClient):
        self.config = config
        self.mcp_client = mcp_client
        self.agent_factory = AgentFactory(config, mcp_client)
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the orchestrator."""
        try:
            await self.mcp_client.initialize()
            
            # Initialize tools discovery
            await self.agent_factory.initialize_tools()
            
            self._initialized = True
            logger.info("Agent orchestrator initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            return False
    
    async def execute_simple_workflow(self, query: str) -> WorkflowResult:
        """Execute simple Kubernetes workflow."""
        if not self._initialized:
            if not await self.initialize():
                return WorkflowResult(
                    success=False,
                    messages=[],
                    error="Failed to initialize orchestrator"
                )
        
        workflow = SimpleWorkflow(self.config, self.agent_factory, self.mcp_client)
        return await workflow.execute(query)
    
    async def execute_multi_agent_workflow(self, query: str) -> WorkflowResult:
        """Execute multi-agent workflow."""
        if not self._initialized:
            if not await self.initialize():
                return WorkflowResult(
                    success=False,
                    messages=[],
                    error="Failed to initialize orchestrator"
                )
        
        workflow = MultiAgentWorkflow(self.config, self.agent_factory, self.mcp_client)
        return await workflow.execute(query)
    
    async def close(self) -> None:
        """Close orchestrator and cleanup resources."""
        try:
            await self.mcp_client.close()
            self._initialized = False
            logger.info("Agent orchestrator closed")
        except Exception as e:
            logger.error(f"Error closing orchestrator: {e}") 