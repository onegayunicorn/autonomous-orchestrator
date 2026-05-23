#!/usr/bin/env python3
"""
J09 Junction Module for Autonomous Orchestrator
Universal bridge between Orchestrator and external systems

J09: Junction Nexus Agent
- Role: junction
- Risk Score: 7
- Purpose: Cross-system integration and protocol translation
"""

__version__ = "1.0.0"
__agent_id__ = "J09"
__agent_name__ = "Junction Nexus"
__agent_role__ = "junction"
__risk_score__ = 7

from .j09_agent import J09Agent
from .bridge import SystemBridge
from .router import RequestRouter
from .translator import ProtocolTranslator

__all__ = [
    "J09Agent",
    "SystemBridge",
    "RequestRouter",
    "ProtocolTranslator",
    "__version__",
    "__agent_id__",
    "__agent_name__",
    "__agent_role__",
    "__risk_score__",
]
