"""
Environment setup utilities.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


def setup_environment_variables() -> Dict[str, Any]:
    """Setup and validate environment variables."""
    env_vars = {}
    
    # Check if .env file exists and suggest loading it
    env_file = Path(".env")
    if env_file.exists():
        logger.info("Found .env file - make sure to load it with load_dotenv()")
    else:
        logger.warning("No .env file found - using system environment variables only")
    
    # Required environment variables
    required_vars = [
        "AUTOGEN_LLM_API_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value or value == "your-api-key-here":
            missing_vars.append(var)
        else:
            env_vars[var] = value
    
    if missing_vars:
        logger.warning(f"Missing required environment variables: {missing_vars}")
        logger.info("Please set these variables in your .env file or system environment")
    
    return env_vars


def get_environment_info() -> Dict[str, Any]:
    """Get information about the current environment setup."""
    return {
        "env_file_exists": Path(".env").exists(),
        "example_file_exists": Path(".env.example").exists(),
        "required_vars_set": len(setup_environment_variables()) > 0,
        "python_version": os.sys.version,
        "working_directory": str(Path.cwd())
    } 