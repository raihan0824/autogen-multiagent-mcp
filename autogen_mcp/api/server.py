import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..config import AppConfig
from ..config.loader import load_configuration
from .routes import router, set_config
from .models import ErrorResponse

logger = logging.getLogger(__name__)

app_config: Optional[AppConfig] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global app_config

    try:
        logger.info("Starting AutoGen MCP API server...")

        app_config = load_configuration()

        if not app_config:
            raise RuntimeError("Failed to load configuration")

        validation_errors = app_config.validate()
        if validation_errors:
            logger.error(
                f"Configuration validation failed: {validation_errors}")
            raise RuntimeError(
                f"Configuration validation failed: {', '.join(validation_errors)}")

        set_config(app_config)

        logger.info("AutoGen MCP API server started successfully")

    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise

    yield

    logger.info("Shutting down AutoGen MCP API server...")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AutoGen MCP Multi-Agent API",
        description="REST API for AutoGen MCP Multi-Agent Framework",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Internal server error",
                detail=str(exc)
            ).dict()
        )

    app.include_router(router)

    @app.get("/")
    async def root():
        return {
            "service": "AutoGen MCP Multi-Agent API",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs"
        }

    return app


app = create_app()
