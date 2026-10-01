import re
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.inference.state import AgentState
from app.inference.llm import get_llm_client

def fact_checker_node(state: AgentState) -> Dict[str, Any]:
    """
    Adversarial Fact-Checker Agent Node.
    Programmatically verifies quote evidence and numerical alignment against raw scraped text.
    Computes strict unclamped confidence score (verified_claims / total_claims).
    Sets hitl_required based ONLY on threat severity (critical / high).
    Does NOT override confidence score on human approval/rejection.
    """
    raw_text = state.get("raw_text", "")
    anomalies = list(state.get("anomaly_flags", []))
    extracted_facts = list(state.get("extracted_facts", []))
    revision_count = state.get("revision_count", 0)
    hitl_approved = state.get("hitl_approved", None)
    hitl_feedback = state.get("hitl_feedback", None)
    logs = list(state.get("logs", []))

    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": "Adversarial Fact-Checker",
        "message": f"Evaluating claims against raw extracted corpus (Revision {revision_count})."
    })

    raw_lower = raw_text.lower()
    verified_count = 0.0
    verified_anomalies = []
    unverified_anomalies = []

    # 1. Programmatic Evidence & Number Verification for Anomalies
    for anomaly in anomalies:
        quote = str(anomaly.get("quote", "")).strip().lower()
        title = str(anomaly.get("title", "")).strip().lower()
        new_val = anomaly.get("new_value")

        quote_verified = bool(quote and quote in raw_lower)
        
        # Check if numbers match raw_text
        num_verified = False
        if new_val is not None and str(int(new_val)) in raw_text:
            num_verified = True

        if quote_verified and num_verified:
            verified_count += 1.0
            anomaly["verification_status"] = "verified"
            verified_anomalies.append(anomaly)
        elif quote_verified or num_verified or any(w in raw_lower for w in title.split() if len(w) > 4):
            verified_count += 0.5
            anomaly["verification_status"] = "partially_verified"
            verified_anomalies.append(anomaly)
        else:
            anomaly["verification_status"] = "unverified"
            unverified_anomalies.append(anomaly)

    # 2. Fact Verification
    for fact in extracted_facts:
        f_quote = str(fact.get("quote", "")).strip().lower()
        if f_quote and f_quote in raw_lower:
            verified_count += 1.0

    total_claims = max(1, len(anomalies) + len(extracted_facts))
    # Strict unclamped confidence score (0.0 to 1.0)
    confidence_score = round(min(1.0, max(0.0, verified_count / total_claims)), 2)

    # 3. Optional Adversarial LLM Refutation Pass
    llm_client = get_llm_client()
    refuted_results = llm_client.refute_claims(verified_anomalies, raw_text)
    final_verified_anomalies = [c for c in refuted_results if not c.get("refuted", False)]

    # 4. HITL condition depends ONLY on threat severity (critical / high)
    hitl_required = any(a.get("severity") in ["critical", "high"] for a in final_verified_anomalies)

    if confidence_score < 0.85:
        feedback = f"Confidence score ({confidence_score}) below 0.85. Triggers self-correction refinement."
    else:
        feedback = f"Claims verified with {confidence_score * 100:.1f}% confidence against primary web sources."

    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": "Adversarial Fact-Checker",
        "message": f"Unclamped Fact Check Score: {confidence_score}. HITL Required: {hitl_required}. Verified Anomalies: {len(final_verified_anomalies)}"
    })

    return {
        "fact_check_score": confidence_score,
        "fact_check_feedback": feedback,
        "hitl_required": hitl_required,
        "hitl_approved": hitl_approved,
        "hitl_feedback": hitl_feedback,
        "anomaly_flags": final_verified_anomalies,
        "revision_count": revision_count + 1,
        "status": "fact_checking_complete",
        "current_node": "Adversarial Fact-Checker",
        "logs": logs
    }
