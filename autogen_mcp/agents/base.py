"""
Base agent functionality and common utilities.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelInfo

from ..config import LLMSettings

logger = logging.getLogger(__name__)


class AgentBase(ABC):
    """Base class for all AutoGen agents."""
    
    def __init__(self, name: str, llm_settings: LLMSettings):
        self.name = name
        self.llm_settings = llm_settings
        self._agent: Optional[AssistantAgent] = None
        self._model_client: Optional[OpenAIChatCompletionClient] = None
    
    @property
    def agent(self) -> AssistantAgent:
        """Get the underlying AutoGen agent."""
        if self._agent is None:
            self._agent = self._create_agent()
        return self._agent
    
    @property
    def model_client(self) -> OpenAIChatCompletionClient:
        """Get the LLM model client."""
        if self._model_client is None:
            self._model_client = self._create_model_client()
        return self._model_client
    
    def _create_model_client(self) -> OpenAIChatCompletionClient:
        """Create the LLM model client."""
        return OpenAIChatCompletionClient(
            model=self.llm_settings.model_name,
            base_url=self.llm_settings.api_base_url,
            api_key=self.llm_settings.api_key,
            model_info=ModelInfo(
                vision=self.llm_settings.supports_vision,
                function_calling=self.llm_settings.supports_function_calling,
                json_output=self.llm_settings.supports_json_output,
                family=self.llm_settings.model_family,
                structured_output=self.llm_settings.supports_json_output
            ),
            timeout=self.llm_settings.timeout_seconds
        )
    
    @abstractmethod
    def _create_agent(self) -> AssistantAgent:
        """Create the underlying AutoGen agent."""
        pass
    
    @abstractmethod
    def get_system_message(self) -> str:
        """Get the system message for this agent."""
        pass
    
    async def run_task(self, task: str) -> Any:
        """Run a task with this agent."""
        return await self.agent.run(task=task) 