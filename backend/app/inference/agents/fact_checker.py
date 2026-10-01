import re
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.inference.state import AgentState
from app.inference.llm import get_llm_client

def fact_checker_node(state: AgentState) -> Dict[str, Any]:
    """
    Adversarial Fact-Checker Agent Node.
    - Strict verification: claim verified ONLY if quote is a substring of raw_text AND numbers match table/text.
    - No partial credit, no title-word fallback.
    - Anti-dilution confidence scoring: anomaly confidence computed separately from facts.
    - Preserves unverified claims flagged with explicit reasons instead of silently deleting them.
    - Sets hitl_required based on threat severity of anomalies.
    """
    raw_text = state.get("raw_text", "")
    anomalies = list(state.get("anomaly_flags", []))
    extracted_facts = list(state.get("extracted_facts", []))
    revision_count = state.get("revision_count", 0)
    hitl_approved = state.get("hitl_approved", None)
    hitl_feedback = state.get("hitl_feedback", None)
    logs = list(state.get("logs", []))
    token_usage = dict(state.get("token_usage", {"calls": 0, "tokens": 0, "nodes": {}}))

    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": "Adversarial Fact-Checker",
        "message": f"Evaluating claims against raw extracted corpus (Revision {revision_count})."
    })

    raw_lower = raw_text.lower()
    verified_anomalies_count = 0
    all_processed_anomalies = []

    # 1. Programmatic Evidence & Number Verification for Anomalies (No partial credit, no title fallback)
    for anomaly in anomalies:
        a_copy = dict(anomaly)
        quote = str(a_copy.get("quote", "")).strip().lower()
        new_val = a_copy.get("new_value")

        quote_verified = bool(quote and quote in raw_lower)
        
        # Check if number matches raw_text
        num_verified = True
        if new_val is not None:
            n_str = str(int(new_val)) if isinstance(new_val, (int, float)) and float(new_val).is_integer() else str(new_val).strip()
            if n_str and n_str not in raw_text:
                num_verified = False

        if quote_verified and num_verified:
            verified_anomalies_count += 1
            a_copy["verification_status"] = "verified"
            a_copy["unverified_reason"] = None
        else:
            a_copy["verification_status"] = "unverified"
            reasons = []
            if not quote_verified:
                reasons.append("Supporting quote not found in source text")
            if not num_verified:
                reasons.append("Numerical value mismatch with table/source")
            a_copy["unverified_reason"] = "; ".join(reasons) if reasons else "Unverified claim"

        all_processed_anomalies.append(a_copy)

    # 2. Fact Verification
    verified_facts_count = 0
    for fact in extracted_facts:
        f_quote = str(fact.get("quote", "")).strip().lower()
        if f_quote and f_quote in raw_lower:
            verified_facts_count += 1

    # Anti-dilution Confidence Scoring:
    if len(all_processed_anomalies) > 0:
        confidence_score = round(verified_anomalies_count / len(all_processed_anomalies), 2)
    elif len(extracted_facts) > 0:
        confidence_score = round(verified_facts_count / len(extracted_facts), 2)
    else:
        confidence_score = 1.0

    # 3. Optional Adversarial LLM Refutation Pass
    llm_client = get_llm_client()
    refuted_results = llm_client.refute_claims(all_processed_anomalies, raw_text)

    # Track node token usage per run
    node_tokens = token_usage.get("nodes", {})
    fc_tokens = 200
    token_usage["calls"] = token_usage.get("calls", 0) + 1
    token_usage["tokens"] = token_usage.get("tokens", 0) + fc_tokens
    node_tokens["Adversarial Fact-Checker"] = node_tokens.get("Adversarial Fact-Checker", 0) + fc_tokens
    token_usage["nodes"] = node_tokens

    # 4. HITL condition depends ONLY on threat severity (critical / high)
    hitl_required = any(a.get("severity") in ["critical", "high"] for a in refuted_results)

    if confidence_score < 0.85:
        feedback = f"Confidence score ({confidence_score}) below 0.85 threshold. Triggers self-correction refinement."
    else:
        feedback = f"Claims verified with {confidence_score * 100:.1f}% confidence against primary web sources."

    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": "Adversarial Fact-Checker",
        "message": f"Fact Check Score: {confidence_score}. HITL Required: {hitl_required}. Total Anomalies Flagged: {len(refuted_results)}"
    })

    return {
        "fact_check_score": confidence_score,
        "fact_check_feedback": feedback,
        "hitl_required": hitl_required,
        "hitl_approved": hitl_approved,
        "hitl_feedback": hitl_feedback,
        "anomaly_flags": refuted_results,
        "revision_count": revision_count + 1,
        "status": "fact_checking_complete",
        "current_node": "Adversarial Fact-Checker",
        "token_usage": token_usage,
        "logs": logs
    }
