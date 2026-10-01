import pytest
from app.inference.agents.fact_checker import fact_checker_node

def test_fact_checker_positive_verification():
    state = {
        "raw_text": "Enterprise Plan $399/mo annual billing",
        "anomaly_flags": [{
            "type": "price_shift",
            "title": "SaaSify Cloud Enterprise 20.0% Price Cut",
            "quote": "Enterprise Plan $399/mo",
            "new_value": 399.0,
            "severity": "critical"
        }],
        "extracted_facts": [],
        "revision_count": 0,
        "logs": []
    }
    result = fact_checker_node(state)
    assert result["fact_check_score"] == 1.0
    assert result["hitl_required"] is True
    assert result["anomaly_flags"][0]["verification_status"] == "verified"

def test_fact_checker_negative_wrong_quote():
    state = {
        "raw_text": "Starter $29/mo, Pro $99/mo",
        "anomaly_flags": [{
            "type": "price_shift",
            "title": "Enterprise 20% Cut",
            "quote": "Enterprise Plan $399/mo",
            "new_value": 399.0,
            "severity": "critical"
        }],
        "extracted_facts": [],
        "revision_count": 0,
        "logs": []
    }
    result = fact_checker_node(state)
    assert result["fact_check_score"] == 0.0
    assert result["anomaly_flags"][0]["verification_status"] == "unverified"
    assert "Supporting quote not found" in result["anomaly_flags"][0]["unverified_reason"]

def test_fact_checker_negative_number_mismatch():
    state = {
        "raw_text": "Enterprise Plan $499/mo quote text present",
        "anomaly_flags": [{
            "type": "price_shift",
            "title": "Enterprise 20% Cut",
            "quote": "Enterprise Plan $499/mo quote text present",
            "new_value": 399.0,
            "severity": "high"
        }],
        "extracted_facts": [],
        "revision_count": 0,
        "logs": []
    }
    result = fact_checker_node(state)
    assert result["fact_check_score"] == 0.0
    assert result["anomaly_flags"][0]["verification_status"] == "unverified"

def test_fact_checker_anti_dilution_scoring():
    # 1 bad anomaly + 10 verified facts -> score must be 0.0, NOT 10/11 = 0.90!
    state = {
        "raw_text": "Fact 1, Fact 2, Fact 3",
        "anomaly_flags": [{
            "type": "price_shift",
            "title": "Bad Anomaly",
            "quote": "Nonexistent quote",
            "new_value": 999.0,
            "severity": "high"
        }],
        "extracted_facts": [
            {"quote": "Fact 1"}, {"quote": "Fact 2"}
        ],
        "revision_count": 0,
        "logs": []
    }
    result = fact_checker_node(state)
    # Anomaly verification rate is 0/1 = 0.0
    assert result["fact_check_score"] == 0.0
