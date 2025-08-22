"""
Setup script for AutoGen MCP Framework.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = requirements_path.read_text().strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="autogen-mcp",
    version="0.1.0",
    description="AutoGen agents with MCP integration for Kubernetes operations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="AutoGen MCP Team",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "autogen-mcp=autogen_mcp.cli:run_cli",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="autogen mcp kubernetes agents ai",
    project_urls={
        "Bug Reports": "https://github.com/autogen-mcp/autogen-mcp/issues",
        "Source": "https://github.com/autogen-mcp/autogen-mcp",
    },
) 