import pytest
from app.inference.agents.analyst import extract_numeric_price, analyst_node

def test_extract_numeric_price():
    assert extract_numeric_price("$499/mo") == 499.0
    assert extract_numeric_price("$399") == 399.0
    assert extract_numeric_price("29") == 29.0
    assert extract_numeric_price("No price") is None

def test_analyst_node_baseline_no_previous_snapshot():
    state = {
        "competitor_name": "TestCorp",
        "raw_text": "Starter $29/mo, Pro $99/mo",
        "parsed_tables": [],
        "previous_snapshot": None,
        "logs": []
    }
    result = analyst_node(state)
    assert len(result["anomaly_flags"]) == 0
    assert result["quantitative_metrics"].get("status") == "baseline_captured"

def test_analyst_node_duckdb_snapshot_diff():
    state = {
        "competitor_name": "SaaSify Cloud",
        "raw_text": "Enterprise Plan $399/mo",
        "parsed_tables": [[{"tier": "Enterprise", "rate": "$399"}]],
        "previous_snapshot": {"raw_text": "Enterprise Plan $499/mo"},
        "logs": []
    }
    result = analyst_node(state)
    assert len(result["anomaly_flags"]) == 1
    anomaly = result["anomaly_flags"][0]
    assert anomaly["pct_change"] == -20.04 or abs(anomaly["pct_change"] - (-20.04)) < 0.2
    assert anomaly["severity"] == "critical"
