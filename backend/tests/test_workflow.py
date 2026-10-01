import pytest
from langgraph.graph import END
from langgraph.types import Command
from app.inference.workflow import route_fact_checker, route_human_review, agent_graph

def test_route_fact_checker_order():
    # 1. Low confidence score (< 0.85) triggers self-correction loop back to researcher when revisions < 2
    state_low_conf = {
        "fact_check_score": 0.70,
        "revision_count": 0,
        "hitl_required": True
    }
    assert route_fact_checker(state_low_conf) == "researcher"

    # 2. Elif hitl_required is True (revisions >= 2 or high severity) -> human_review
    state_hitl = {
        "fact_check_score": 0.95,
        "revision_count": 0,
        "hitl_required": True
    }
    assert route_fact_checker(state_hitl) == "human_review"

    # 3. Else -> writer
    state_writer = {
        "fact_check_score": 0.95,
        "revision_count": 0,
        "hitl_required": False
    }
    assert route_fact_checker(state_writer) == "writer"

def test_route_human_review():
    assert route_human_review({"hitl_approved": True}) == "writer"
    assert route_human_review({"hitl_approved": False}) == END
    assert route_human_review({"hitl_approved": None}) == END

def test_end_to_end_interrupt_and_resume_approval():
    thread_id = "test_thread_approve_123"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "thread_id": thread_id,
        "competitor_id": "c1",
        "competitor_name": "SaaSify Cloud",
        "target_url": "https://saasify.cloud/pricing",
        "user_query": "Test run",
        "raw_text": "SaaSify Enterprise Plan $399/mo (WAS $499/mo)",
        "parsed_tables": [[{"tier": "Enterprise", "rate": "$399"}]],
        "previous_snapshot": {"raw_text": "SaaSify Enterprise Plan $499/mo"},
        "extracted_facts": [],
        "quantitative_metrics": {},
        "anomaly_flags": [],
        "plotly_spec": {},
        "fact_check_score": 1.0,
        "fact_check_feedback": "",
        "revision_count": 0,
        "hitl_required": False,
        "hitl_approved": None,
        "hitl_feedback": None,
        "writer_draft": "",
        "final_report": "",
        "citations": [],
        "status": "running",
        "current_node": "Supervisor",
        "logs": []
    }

    # Run graph until interrupt at human_review
    for event in agent_graph.stream(initial_state, config=config):
        pass

    state_post_stream = agent_graph.get_state(config)
    assert len(state_post_stream.next) > 0  # Graph is paused at human_review interrupt

    # Resume graph with Command(resume={"approved": True, "feedback": "Approved"})
    command = Command(resume={"approved": True, "feedback": "Approved by test analyst"})
    for event in agent_graph.stream(command, config=config):
        pass

    final_state = agent_graph.get_state(config)
    assert len(final_state.next) == 0  # Execution finished
    assert final_state.values["status"] == "completed"
    assert "Executive Market Intelligence Brief" in final_state.values["final_report"]

def test_end_to_end_interrupt_and_resume_rejection():
    thread_id = "test_thread_reject_456"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "thread_id": thread_id,
        "competitor_id": "c1",
        "competitor_name": "SaaSify Cloud",
        "target_url": "https://saasify.cloud/pricing",
        "user_query": "Test run",
        "raw_text": "SaaSify Enterprise Plan $399/mo (WAS $499/mo)",
        "parsed_tables": [[{"tier": "Enterprise", "rate": "$399"}]],
        "previous_snapshot": {"raw_text": "SaaSify Enterprise Plan $499/mo"},
        "extracted_facts": [],
        "quantitative_metrics": {},
        "anomaly_flags": [],
        "plotly_spec": {},
        "fact_check_score": 1.0,
        "fact_check_feedback": "",
        "revision_count": 0,
        "hitl_required": False,
        "hitl_approved": None,
        "hitl_feedback": None,
        "writer_draft": "",
        "final_report": "",
        "citations": [],
        "status": "running",
        "current_node": "Supervisor",
        "logs": []
    }

    # Run graph until interrupt at human_review
    for event in agent_graph.stream(initial_state, config=config):
        pass

    state_post_stream = agent_graph.get_state(config)
    assert len(state_post_stream.next) > 0

    # Resume graph with Command(resume={"approved": False, "feedback": "Rejected"})
    command = Command(resume={"approved": False, "feedback": "Rejected finding"})
    for event in agent_graph.stream(command, config=config):
        pass

    final_state = agent_graph.get_state(config)
    assert len(final_state.next) == 0
    assert final_state.values["status"] == "rejected"
    assert final_state.values["final_report"] == ""  # No report generated on rejection
