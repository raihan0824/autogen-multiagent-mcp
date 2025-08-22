"""
Agent orchestration workflows with configurable multi-agent systems.
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod

from ..config import AppConfig
# No longer need custom MCP classes - using AutoGen native MCP
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
    """Simple workflow that uses only the first available agent with native AutoGen tool execution."""
    
    def __init__(self, config: AppConfig, agent_factory: AgentFactory):
        self.config = config
        self.agent_factory = agent_factory
        self.primary_agent = None
    
    async def _get_primary_agent(self) -> AgentBase:
        """Get the first available agent asynchronously."""
        if self.primary_agent is None:
            enabled_agents = self.config.agents.get_enabled_agents()
            if enabled_agents:
                try:
                    self.primary_agent = await self.agent_factory.create_agent(enabled_agents[0])
                    if self.primary_agent:
                        logger.info(f"Created primary agent: {self.primary_agent.name}")
                        return self.primary_agent
                except Exception as e:
                    logger.error(f"Failed to create primary agent: {e}")
            
            raise RuntimeError("No agents available")
        
        return self.primary_agent
    
    async def execute(self, query: str) -> WorkflowResult:
        """Execute query using native AutoGen multi-turn conversation."""
        try:
            messages = []
            
            # Get the primary agent
            primary_agent = await self._get_primary_agent()
            
            # Single call to agent.run() - AutoGen handles all tool iterations internally
            from autogen_core import CancellationToken
            logger.info(f"Starting native AutoGen conversation with agent: {primary_agent.name}")
            
            result = await primary_agent.run(task=query, cancellation_token=CancellationToken())
            
            # Extract all messages from the result (includes tool calls, executions, and responses)
            for msg in result.messages:
                message = WorkflowMessage(
                    agent_name=primary_agent.name,
                    content=str(msg.content) if hasattr(msg, 'content') else str(msg)
                )
                messages.append(message)
            
            logger.info(f"Native AutoGen conversation completed with {len(messages)} messages")
            return WorkflowResult(success=True, messages=messages)
            
        except Exception as e:
            logger.error(f"Error in simple workflow: {e}")
            return WorkflowResult(
                success=False,
                messages=[],
                error=str(e)
            )


class MultiAgentWorkflow(Workflow):
    """Multi-agent workflow with native AutoGen tool execution."""
    
    def __init__(self, config: AppConfig, agent_factory: AgentFactory):
        self.config = config
        self.agent_factory = agent_factory
        self.agents = {}
        self.conversation_flow = []
    
    async def _ensure_agents_initialized(self):
        """Asynchronously initialize agents and conversation flow."""
        if not self.agents:
            # Create all enabled agents asynchronously
            enabled_agents = self.config.agents.get_enabled_agents()
            
            for agent_def in enabled_agents:
                try:
                    agent = await self.agent_factory.create_agent(agent_def)
                    if agent:
                        self.agents[agent_def.name] = agent
                        logger.info(f"Created agent: {agent_def.name}")
                except Exception as e:
                    logger.error(f"Failed to create agent {agent_def.name}: {e}")
            
            # Get conversation flow from configuration
            enabled_agent_names = [agent_def.name for agent_def in enabled_agents]
            
            # Use configured flow or default to enabled agents
            if self.config.agents.conversation_flow:
                self.conversation_flow = [name for name in self.config.agents.conversation_flow 
                                        if name in enabled_agent_names]
            else:
                self.conversation_flow = enabled_agent_names
            
            logger.info(f"Initialized multi-agent workflow with {len(self.agents)} agents")
    
    async def execute(self, query: str) -> WorkflowResult:
        """Execute multi-agent workflow with native AutoGen tool execution."""
        try:
            # Ensure agents are initialized
            await self._ensure_agents_initialized()
            messages = []
            
            # Use AutoGen's native conversation pattern
            context = query
            
            # Let each agent in the flow handle the task with full tool capabilities
            for agent_name in self.conversation_flow:
                # Check if agent exists in our team
                if agent_name not in self.agents:
                    logger.warning(f"Agent '{agent_name}' in conversation flow not found in team, skipping")
                    continue
                
                agent = self.agents[agent_name]
                logger.info(f"Starting conversation with agent: {agent_name}")
                
                # Create enriched context with conversation history
                if messages:
                    context_parts = [f"Original query: {query}", ""]
                    context_parts.append("Previous conversation:")
                    for msg in messages[-3:]:  # Last 3 messages for context
                        context_parts.append(f"{msg.agent_name}: {msg.content}")
                    context_parts.append("")
                    context_parts.append(f"Please continue the conversation as {agent_name}:")
                    enriched_context = "\n".join(context_parts)
                else:
                    enriched_context = f"Query: {query}"
                
                # Single call to agent - AutoGen handles all tool iterations internally
                from autogen_core import CancellationToken
                result = await agent.run(task=enriched_context, cancellation_token=CancellationToken())
                
                # Extract all messages from this agent's conversation
                agent_messages = []
                for msg in result.messages:
                    message = WorkflowMessage(
                        agent_name=agent_name,
                        content=str(msg.content) if hasattr(msg, 'content') else str(msg)
                    )
                    agent_messages.append(message)
                    messages.append(message)
                
                logger.info(f"Agent {agent_name} completed with {len(agent_messages)} messages")
                
                # Check for natural termination
                if agent_messages and self._should_terminate(agent_messages[-1].content, agent_name):
                    logger.info(f"Workflow naturally terminated by agent {agent_name}")
                    break
            
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
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.agent_factory = AgentFactory(config.mcp, config.agents)
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the orchestrator."""
        try:
            # No need to initialize tools separately - AutoGen handles this
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
        
        workflow = SimpleWorkflow(self.config, self.agent_factory)
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
        
        workflow = MultiAgentWorkflow(self.config, self.agent_factory)
        return await workflow.execute(query)
    
    async def close(self) -> None:
        """Close orchestrator and cleanup resources."""
        try:
            self._initialized = False
            logger.info("Agent orchestrator closed")
        except Exception as e:
            logger.error(f"Error closing orchestrator: {e}") 