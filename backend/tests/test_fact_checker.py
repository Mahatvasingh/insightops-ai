import pytest
from app.inference.agents.fact_checker import fact_checker_node

def test_fact_checker_quote_and_number_verification():
    raw_text = "SaaSify Enterprise Plan lowered to $399/mo (WAS $499/mo)."
    state = {
        "raw_text": raw_text,
        "anomaly_flags": [
            {
                "title": "SaaSify Enterprise Pricing Shift",
                "severity": "critical",
                "quote": "lowered to $399/mo",
                "new_value": 399
            }
        ],
        "extracted_facts": [
            {"quote": "lowered to $399/mo"}
        ],
        "revision_count": 0,
        "hitl_approved": None,
        "logs": []
    }
    result = fact_checker_node(state)
    assert result["fact_check_score"] == 1.0  # 100% verified
    assert result["hitl_required"] is True   # Critical severity requires HITL

def test_fact_checker_does_not_override_confidence_on_human_approval():
    raw_text = "SaaSify Enterprise Plan lowered to $399/mo."
    state = {
        "raw_text": raw_text,
        "anomaly_flags": [
            {
                "title": "Unverified claim",
                "severity": "low",
                "quote": "Nonexistent quote in raw text",
                "new_value": 999
            }
        ],
        "extracted_facts": [],
        "revision_count": 0,
        "hitl_approved": True,  # Human approved
        "logs": []
    }
    result = fact_checker_node(state)
    # Human approval must NOT override confidence score to 0.99
    assert result["fact_check_score"] < 0.85
    assert result["hitl_approved"] is True
