from datetime import datetime, timezone
from typing import Dict, Any
from app.inference.state import AgentState

def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """
    Stateful Agent Supervisor Node.
    Reads the shared AgentState, evaluates execution step completion,
    logs telemetry, and coordinates task delegation across specialized sub-agents.
    """
    status = state.get("status", "initialized")
    logs = list(state.get("logs", []))
    
    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": "Supervisor",
        "message": f"Supervisor evaluating StateGraph. Current status: '{status}'"
    })

    return {
        "current_node": "Supervisor",
        "logs": logs
    }
