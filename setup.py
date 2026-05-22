#!/usr/bin/env python3
"""
Setup script for Autonomous Orchestrator
Allows installation via: pip install -e .
"""

from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="autonomous-orchestrator",
    version="7.0.0",
    description="Autonomous Orchestrator for Aether Grid - Self-governing command execution engine",
    author="Tyrone J Power Ω",
    author_email="tyrone@onegayunicorn.foundation",
    url="https://github.com/onegayunicorn/autonomous-orchestrator",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.5.0",
        "yarl>=1.9.0",
        "aiohttp>=3.8.0",
        "orjson>=3.9.0",
        "click>=8.1.0",
        "rich>=13.7.0",
        "structlog>=23.2.0",
        "prometheus-client>=0.17.0",
        "cryptography>=41.0.0",
        "pyjwt>=2.8.0",
        "python-jose[cryptography]>=3.3.0",
        "psutil>=5.9.0",
        "platformdirs>=3.10.0",
    ],
    entry_points={
        "console_scripts": [
            "aether-orchestrator=orchestrator:main",
            "ao=orchestrator:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
    keywords=[
        "aether",
        "orchestrator",
        "autonomous",
        "quantum",
        "coherence",
        "entanglement",
        "automation",
        "command-execution",
    ],
    project_urls={
        "Bug Reports": "https://github.com/onegayunicorn/autonomous-orchestrator/issues",
        "Source": "https://github.com/onegayunicorn/autonomous-orchestrator",
    },
)
