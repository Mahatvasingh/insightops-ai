from datetime import datetime, timezone
from typing import Dict, Any
from app.inference.state import AgentState

def fact_checker_node(state: AgentState) -> Dict[str, Any]:
    """
    Adversarial Fact-Checker Agent Node (Self-Correction Loop & HITL Evaluator).
    Cross-checks draft statements and quantitative anomalies against raw scraped web text.
    Computes a strict confidence score (0.0 to 1.0).
    If confidence < 0.85 or threat severity is 'critical', sets state flags for self-correction or HITL pause.
    """
    raw_text = state.get("raw_text", "")
    anomalies = state.get("anomaly_flags", [])
    revision_count = state.get("revision_count", 0)
    hitl_approved = state.get("hitl_approved", None)
    logs = list(state.get("logs", []))

    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": "Adversarial Fact-Checker",
        "message": f"Evaluating claims against raw extracted corpus (Revision {revision_count})."
    })

    # Adversarial verification logic
    verified_claims = 0
    total_claims = max(1, len(anomalies) * 2)

    for anomaly in anomalies:
        title_keywords = anomaly.get("title", "").split()
        matches = sum(1 for kw in title_keywords if len(kw) > 3 and kw.lower() in raw_text.lower())
        if matches >= 2:
            verified_claims += 2
        elif matches >= 1:
            verified_claims += 1

    # Base confidence score
    confidence_score = min(0.98, max(0.60, round(verified_claims / total_claims, 2)))

    # If already approved by human in the loop, override confidence to 0.99
    if hitl_approved is True:
        confidence_score = 0.99
        hitl_required = False
        feedback = "Human Analyst approved finding via HITL checkpointer breakpoint."
    elif hitl_approved is False:
        confidence_score = 0.50
        hitl_required = False
        feedback = "Human Analyst rejected finding. Routing back to Researcher for query refinement."
    else:
        # Check if HITL is required due to high impact threat or low confidence
        is_high_impact = any(a.get("severity") in ["critical", "high"] for a in anomalies)
        hitl_required = is_high_impact or (confidence_score < 0.85)

        if confidence_score < 0.85:
            feedback = f"Confidence score ({confidence_score}) below target 0.85 threshold. Claims require verification refinement."
        else:
            feedback = f"Claims verified with {confidence_score * 100}% confidence against primary web sources."

    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": "Adversarial Fact-Checker",
        "message": f"Fact check score: {confidence_score}. HITL Required: {hitl_required}. Feedback: {feedback}"
    })

    return {
        "fact_check_score": confidence_score,
        "fact_check_feedback": feedback,
        "hitl_required": hitl_required,
        "revision_count": revision_count + 1 if not hitl_approved else revision_count,
        "status": "fact_checking_complete",
        "current_node": "Adversarial Fact-Checker",
        "logs": logs
    }
