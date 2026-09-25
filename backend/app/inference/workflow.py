from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.inference.state import AgentState
from app.inference.agents.supervisor import supervisor_node
from app.inference.agents.researcher import researcher_node
from app.inference.agents.analyst import analyst_node
from app.inference.agents.fact_checker import fact_checker_node
from app.inference.agents.writer import writer_node

# Persistent Checkpointer for thread state & HITL breakpoints
checkpointer = MemorySaver()

def route_fact_checker(state: AgentState) -> str:
    """
    Conditional Routing Edge:
    1. If HITL pause is required and human approval has not been received yet, route to awaiting_hitl state.
    2. If confidence score < 0.85 and revision_count < 2, trigger Self-Correction loop back to Researcher.
    3. If approved or confidence >= 0.85, proceed to Executive Writer.
    """
    hitl_required = state.get("hitl_required", False)
    hitl_approved = state.get("hitl_approved", None)
    confidence = state.get("fact_check_score", 1.0)
    revisions = state.get("revision_count", 0)

    # Check Human-in-the-Loop breakpoint condition
    if hitl_required and hitl_approved is None:
        return "hitl_breakpoint"
    
    # If rejected by human analyst, route back to researcher for query refinement
    if hitl_approved is False and revisions < 3:
        return "researcher"

    # Self-Correction cyclical feedback loop
    if confidence < 0.85 and revisions < 2:
        return "researcher"

    # Proceed to writer
    return "writer"

def hitl_breakpoint_node(state: AgentState) -> Dict[str, Any]:
    """
    Pause state node for Human-in-the-Loop approval.
    """
    logs = list(state.get("logs", []))
    logs.append({
        "timestamp": "HITL Breakpoint",
        "node": "HITL Checkpointer",
        "message": "Graph paused for Human-in-the-Loop review. Awaiting API approval/rejection endpoint call."
    })
    return {
        "status": "awaiting_hitl",
        "current_node": "HITL Checkpointer",
        "logs": logs
    }

def create_market_intelligence_graph():
    """
    Builds cyclical stateful LangGraph multi-agent architecture.
    """
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("fact_checker", fact_checker_node)
    workflow.add_node("hitl_breakpoint", hitl_breakpoint_node)
    workflow.add_node("writer", writer_node)

    # Define Graph Execution Edges
    workflow.set_entry_point("supervisor")
    workflow.add_edge("supervisor", "researcher")
    workflow.add_edge("researcher", "analyst")
    workflow.add_edge("analyst", "fact_checker")

    # Add Conditional Edge from Fact-Checker
    workflow.add_conditional_edges(
        "fact_checker",
        route_fact_checker,
        {
            "hitl_breakpoint": "hitl_breakpoint",
            "researcher": "researcher",
            "writer": "writer"
        }
    )

    workflow.add_edge("hitl_breakpoint", END)
    workflow.add_edge("writer", END)

    # Compile with checkpointer
    app = workflow.compile(checkpointer=checkpointer)
    return app

# Singleton compiled graph instance
agent_graph = create_market_intelligence_graph()
