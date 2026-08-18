# __init__.py
# Public API for AgentAudit.
# Loads .env automatically so users just set GEMINI_API_KEY in .env

import os
from dotenv import load_dotenv

# Load from home directory first (~/.agentaudit/.env)
# then fall back to current directory .env
_home_env = os.path.expanduser("~/.agentaudit/.env")
_local_env = os.path.join(os.getcwd(), ".env")

if os.path.exists(_home_env):
    load_dotenv(_home_env)
else:
    load_dotenv(_local_env)

from agentaudit.core.wrapper import audit, set_context, set_tokens, AgentTracer
from agentaudit.metrics.hallucination import detect_hallucination
from agentaudit.metrics.faithfulness import detect_faithfulness
from agentaudit.metrics.cost import calculate_cost
from agentaudit.metrics.latency import measure_latency
from agentaudit.core.storage import init_db
from agentaudit.core.regression import compare_runs, get_latest_runs

__version__ = "0.1.0"

__all__ = [
    "audit",
    "set_context",
    "set_tokens",
    "AgentTracer",
    "detect_hallucination",
    "detect_faithfulness",
    "calculate_cost",
    "measure_latency",
    "init_db",
    "compare_runs",
    "get_latest_runs",
]
