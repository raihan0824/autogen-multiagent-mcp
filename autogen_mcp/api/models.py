from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class QueryRequest(BaseModel):
    query: str = Field(..., description="The query to execute")
    agent_type: Optional[str] = Field(
        None, description="Specific agent type to use")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Additional parameters")
    workflow_id: Optional[str] = Field(
        None, description="Optional workflow ID for tracking")


class WorkflowRequest(BaseModel):
    query: str = Field(..., description="The query to execute")
    workflow_type: Literal["simple",
                           "multi-agent"] = Field("simple", description="Type of workflow")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Additional parameters")
    workflow_id: Optional[str] = Field(
        None, description="Optional workflow ID for tracking")


class MessageResponse(BaseModel):
    agent_name: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WorkflowResponse(BaseModel):
    status: Literal["success", "error",
                    "processing"] = Field(..., description="Execution status")
    data: Dict[str, Any] = Field(
        default_factory=dict, description="Response data")
    messages: List[MessageResponse] = Field(
        default_factory=list, description="Workflow messages")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Execution metadata")
    errors: List[str] = Field(default_factory=list,
                              description="Error messages if any")


class HealthResponse(BaseModel):
    status: Literal["healthy",
                    "unhealthy"] = Field(..., description="Service health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field("1.0.0", description="API version")
    dependencies: Dict[str, str] = Field(
        default_factory=dict, description="Dependency status")


class AgentInfo(BaseModel):
    name: str
    type: str
    capabilities: List[str]
    status: Literal["enabled", "disabled", "error"]
    description: Optional[str] = None


class AgentsResponse(BaseModel):
    agents: List[AgentInfo]
    total_count: int
    enabled_count: int


class ConfigResponse(BaseModel):
    agents_count: int
    enabled_agents: List[str]
    mcp_servers: List[str]
    api_version: str = "1.0.0"


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
