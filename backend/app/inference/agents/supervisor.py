from datetime import datetime, timezone
from typing import Dict, Any

from app.config import settings
from app.inference.state import AgentState
from app.core.cache import cache_manager

def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """
    Supervisor Node.
    Evaluates workflow execution, enforces token budgets, logs node transitions,
    and coordinates task execution.
    """
    status = state.get("status", "initialized")
    logs = list(state.get("logs", []))
    token_usage = dict(state.get("token_usage", {"calls": 0, "tokens": 0}))

    # Enforce token budget
    stats = cache_manager.stats()
    current_tokens = stats.get("llm_tokens_total", 0)
    token_usage["tokens"] = current_tokens
    token_usage["calls"] = stats.get("llm_calls", 0)

    if current_tokens > settings.LLM_TOKEN_BUDGET:
        logs.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "node": "Supervisor",
            "message": f"Token budget exceeded ({current_tokens} > {settings.LLM_TOKEN_BUDGET}). Halting graph."
        })
        return {
            "status": "failed",
            "current_node": "Supervisor",
            "logs": logs,
            "token_usage": token_usage
        }

    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": "Supervisor",
        "message": f"Supervisor evaluating step. Status: '{status}'. LLM Calls: {token_usage['calls']}, Tokens: {token_usage['tokens']}"
    })

    return {
        "current_node": "Supervisor",
        "token_usage": token_usage,
        "logs": logs
    }
