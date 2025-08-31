import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    try:
        import uvicorn
        from autogen_mcp.api.server import app

        logger.info("Starting AutoGen MCP API server...")

        # Start the server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=True
        )

    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
