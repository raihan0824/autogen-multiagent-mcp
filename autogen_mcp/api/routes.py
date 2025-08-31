import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse

from ..config import AppConfig
from ..agents.orchestrator import AgentOrchestrator, WorkflowResult
from .models import (
    QueryRequest, WorkflowRequest, WorkflowResponse, MessageResponse,
    HealthResponse, AgentsResponse, AgentInfo, ConfigResponse, ErrorResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["autogen-mcp"])

_orchestrator: Optional[AgentOrchestrator] = None
_config: Optional[AppConfig] = None


async def get_orchestrator() -> AgentOrchestrator:
    global _orchestrator, _config
    if _orchestrator is None:
        if _config is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not initialized"
            )
        _orchestrator = AgentOrchestrator(_config)
        await _orchestrator.initialize()
    return _orchestrator


def set_config(config: AppConfig) -> None:
    global _config
    _config = config


@router.get("/health", response_model=HealthResponse)
async def health_check():
    try:
        dependencies = {}

        if _config:
            dependencies["config"] = "loaded"
            dependencies["agents"] = f"{len(_config.agents.get_enabled_agents())} enabled"
        else:
            dependencies["config"] = "not_loaded"

        return HealthResponse(
            status="healthy",
            dependencies=dependencies,
            version="1.0.0"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            dependencies={"error": str(e)},
            version="1.0.0"
        )


@router.post("/query", response_model=WorkflowResponse)
async def execute_query(
    request: QueryRequest,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator)
):
    try:
        logger.info(f"Executing query: {request.query[:100]}...")

        workflow_id = request.workflow_id or str(uuid.uuid4())

        result = await orchestrator.execute_simple_workflow(request.query)

        messages = [
            MessageResponse(
                agent_name=msg.agent_name,
                content=msg.content
            )
            for msg in result.messages
        ]

        metadata = {
            "workflow_id": workflow_id,
            "execution_time": datetime.utcnow().isoformat(),
            "message_count": len(messages),
            "agent_type": request.agent_type or "auto"
        }

        if result.success:
            return WorkflowResponse(
                status="success",
                data={"result": "Query executed successfully"},
                messages=messages,
                metadata=metadata
            )
        else:
            return WorkflowResponse(
                status="error",
                data={},
                messages=messages,
                metadata=metadata,
                errors=[result.error] if result.error else ["Unknown error"]
            )

    except Exception as e:
        logger.error(f"Error executing query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute query: {str(e)}"
        )


@router.post("/workflows", response_model=WorkflowResponse)
async def execute_workflow(
    request: WorkflowRequest,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator)
):
    try:
        logger.info(
            f"Executing {request.workflow_type} workflow: {request.query[:100]}...")

        workflow_id = request.workflow_id or str(uuid.uuid4())

        if request.workflow_type == "simple":
            result = await orchestrator.execute_simple_workflow(request.query)
        elif request.workflow_type == "multi-agent":
            result = await orchestrator.execute_multi_agent_workflow(request.query)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid workflow type: {request.workflow_type}"
            )

        messages = [
            MessageResponse(
                agent_name=msg.agent_name,
                content=msg.content
            )
            for msg in result.messages
        ]

        metadata = {
            "workflow_id": workflow_id,
            "workflow_type": request.workflow_type,
            "execution_time": datetime.utcnow().isoformat(),
            "message_count": len(messages)
        }

        if result.success:
            return WorkflowResponse(
                status="success",
                data={"result": "Workflow executed successfully"},
                messages=messages,
                metadata=metadata
            )
        else:
            return WorkflowResponse(
                status="error",
                data={},
                messages=messages,
                metadata=metadata,
                errors=[result.error] if result.error else ["Unknown error"]
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute workflow: {str(e)}"
        )


@router.get("/agents", response_model=AgentsResponse)
async def list_agents():
    try:
        if not _config:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not initialized"
            )

        enabled_agents = _config.agents.get_enabled_agents()
        agents = []

        for agent_def in enabled_agents:
            agent_info = AgentInfo(
                name=agent_def.name,
                type=agent_def.agent_type,
                capabilities=agent_def.capabilities,
                status="enabled",
                description=getattr(agent_def, 'role', None)
            )
            agents.append(agent_info)

        return AgentsResponse(
            agents=agents,
            total_count=len(agents),
            enabled_count=len(agents)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list agents: {str(e)}"
        )


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    try:
        if not _config:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not initialized"
            )

        enabled_agents = _config.agents.get_enabled_agents()

        return ConfigResponse(
            agents_count=len(enabled_agents),
            enabled_agents=[agent.name for agent in enabled_agents],
            mcp_servers=[
                server.name for server in _config.mcp.servers] if _config.mcp.servers else []
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get config: {str(e)}"
        )
