from datetime import datetime, timezone
from typing import Dict, Any

from app.config import settings
from app.inference.state import AgentState

def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """
    Supervisor Node.
    Evaluates workflow execution, enforces PER-RUN token budgets,
    logs per-node token usage, and coordinates multi-agent task execution.
    """
    status = state.get("status", "initialized")
    logs = list(state.get("logs", []))
    token_usage = dict(state.get("token_usage", {"calls": 0, "tokens": 0, "nodes": {}}))

    # Enforce PER-RUN token budget (stored in state.token_usage)
    run_tokens = token_usage.get("tokens", 0)
    run_calls = token_usage.get("calls", 0)
    node_breakdown = token_usage.get("nodes", {})

    if run_tokens > settings.LLM_TOKEN_BUDGET:
        logs.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "node": "Supervisor",
            "message": f"Run token budget exceeded ({run_tokens} > {settings.LLM_TOKEN_BUDGET}). Halting graph."
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
        "message": f"Supervisor step. Status: '{status}'. Run Calls: {run_calls}, Run Tokens: {run_tokens}. Node Breakdown: {node_breakdown}"
    })

    return {
        "current_node": "Supervisor",
        "token_usage": token_usage,
        "logs": logs
    }
