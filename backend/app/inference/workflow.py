import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt

from app.config import settings
from app.inference.state import AgentState
from app.inference.agents.supervisor import supervisor_node
from app.inference.agents.researcher import researcher_node
from app.inference.agents.analyst import analyst_node
from app.inference.agents.fact_checker import fact_checker_node
from app.inference.agents.writer import writer_node

# Persistent Checkpointer using SqliteSaver for thread state and interrupt persistence
conn = sqlite3.connect(settings.SQLITE_CHECKPOINT_DB, check_same_thread=False)
checkpointer = SqliteSaver(conn)

def route_researcher(state: AgentState) -> str:
    """
    Routing from Researcher node:
    - If status is 'unchanged' or 'failed', short-circuit execution directly to END.
    - Otherwise proceed to Quantitative Analyst.
    """
    status = state.get("status", "")
    if status in ("unchanged", "failed"):
        return END
    return "analyst"

def route_fact_checker(state: AgentState) -> str:
    """
    Conditional Edge Routing Order:
    (a) If score < 0.85 and revision_count < 2 -> trigger Self-Correction loop back to Researcher.
    (b) Elif hitl_required (critical/high severity) -> route to human_review node.
    (c) Else -> proceed directly to Executive Writer.
    """
    confidence = state.get("fact_check_score", 1.0)
    revisions = state.get("revision_count", 0)
    hitl_required = state.get("hitl_required", False)

    # (a) Self-correction cyclical loop
    if confidence < 0.85 and revisions < 2:
        return "researcher"

    # (b) Human-in-the-Loop breakpoint
    if hitl_required:
        return "human_review"

    # (c) Proceed to writer
    return "writer"

def route_human_review(state: AgentState) -> str:
    """
    Post Human Review Routing:
    - Approved -> proceed to Executive Writer.
    - Rejected / Cancelled -> terminate to END with status 'rejected' (no report or alerts).
    """
    hitl_approved = state.get("hitl_approved", None)
    if hitl_approved is True:
        return "writer"
    return END

def human_review_node(state: AgentState) -> Dict[str, Any]:
    """
    Human Review interrupt node.
    Pauses execution via langgraph.types.interrupt() and waits for Command(resume={"approved": ..., "feedback": ...}).
    """
    logs = list(state.get("logs", []))
    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": "Human Review",
        "message": "Graph execution paused for Human-in-the-Loop review."
    })

    # Interrupt execution and wait for analyst decision
    resume_data = interrupt({
        "type": "human_review",
        "thread_id": state.get("thread_id"),
        "competitor_name": state.get("competitor_name"),
        "confidence_score": state.get("fact_check_score", 1.0),
        "anomalies": state.get("anomaly_flags", [])
    })

    approved = False
    feedback = "Reviewed by analyst"

    if isinstance(resume_data, dict):
        approved = bool(resume_data.get("approved", False))
        feedback = str(resume_data.get("feedback", feedback))
    elif isinstance(resume_data, bool):
        approved = resume_data

    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": "Human Review",
        "message": f"Graph resumed from interrupt. Approved: {approved}. Feedback: {feedback}"
    })

    if approved:
        return {
            "hitl_approved": True,
            "hitl_feedback": feedback,
            "hitl_required": False,
            "status": "approved",
            "current_node": "Human Review",
            "logs": logs
        }
    else:
        return {
            "hitl_approved": False,
            "hitl_feedback": feedback,
            "hitl_required": False,
            "status": "rejected",
            "current_node": "Human Review",
            "logs": logs
        }

def create_market_intelligence_graph():
    """Builds stateful LangGraph workflow with interrupts and persistent sqlite checkpointer."""
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("fact_checker", fact_checker_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("writer", writer_node)

    # Define Execution Edges
    workflow.set_entry_point("supervisor")
    workflow.add_edge("supervisor", "researcher")

    # Conditional Edges from Researcher (Short-circuit on unchanged / failed)
    workflow.add_conditional_edges(
        "researcher",
        route_researcher,
        {
            "analyst": "analyst",
            END: END
        }
    )

    workflow.add_edge("analyst", "fact_checker")

    # Conditional Edges from Fact-Checker
    workflow.add_conditional_edges(
        "fact_checker",
        route_fact_checker,
        {
            "researcher": "researcher",
            "human_review": "human_review",
            "writer": "writer"
        }
    )

    # Conditional Edges from Human Review Interrupt
    workflow.add_conditional_edges(
        "human_review",
        route_human_review,
        {
            "writer": "writer",
            END: END
        }
    )

    workflow.add_edge("writer", END)

    # Compile with persistent SqliteSaver
    app = workflow.compile(checkpointer=checkpointer)
    return app

# Singleton compiled graph instance
agent_graph = create_market_intelligence_graph()
