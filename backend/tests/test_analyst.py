import pytest
from app.inference.agents.analyst import extract_numeric_price, analyst_node

def test_extract_numeric_price():
    assert extract_numeric_price("$499") == 499.0
    assert extract_numeric_price("$49/mo") == 49.0
    assert extract_numeric_price("$0.04/hr") == 0.04
    assert extract_numeric_price("$0") == 0.0
    assert extract_numeric_price("Contact Sales") is None
    assert extract_numeric_price("Custom Enterprise") is None

def test_analyst_node_no_previous_snapshot():
    state = {
        "competitor_name": "TestCorp",
        "raw_text": "Starter $29/mo, Pro $99/mo",
        "parsed_tables": [[{"tier": "Starter", "rate": "$29"}]],
        "previous_snapshot": None,
        "logs": []
    }
    result = analyst_node(state)
    assert len(result["anomaly_flags"]) == 0
    assert result["quantitative_metrics"].get("status") == "baseline_captured"

def test_analyst_node_unchanged_data():
    curr_tables = [[{"tier": "Pro", "rate": "$99"}]]
    prev_tables = [[{"tier": "Pro", "rate": "$99"}]]
    state = {
        "competitor_name": "TestCorp",
        "raw_text": "Pro Plan $99/mo",
        "parsed_tables": curr_tables,
        "previous_snapshot": {"parsed_tables": prev_tables},
        "logs": []
    }
    result = analyst_node(state)
    assert len(result["anomaly_flags"]) == 0

def test_analyst_node_duckdb_price_cut():
    curr_tables = [[{"tier": "Enterprise", "rate": "$399"}]]
    prev_tables = [[{"tier": "Enterprise", "rate": "$499"}]]
    state = {
        "competitor_name": "SaaSify Cloud",
        "raw_text": "Enterprise Plan now $399/mo",
        "parsed_tables": curr_tables,
        "previous_snapshot": {"parsed_tables": prev_tables, "raw_text": "Enterprise Plan $499/mo"},
        "logs": []
    }
    result = analyst_node(state)
    assert len(result["anomaly_flags"]) == 1
    anomaly = result["anomaly_flags"][0]
    assert anomaly["type"] == "price_shift"
    assert abs(anomaly["pct_change"] - (-20.04)) < 0.2
    assert anomaly["severity"] == "critical"

def test_analyst_node_duckdb_price_increase():
    curr_tables = [[{"tier": "Pro", "rate": "$149"}]]
    prev_tables = [[{"tier": "Pro", "rate": "$99"}]]
    state = {
        "competitor_name": "SaaSify Cloud",
        "raw_text": "Pro Plan increased to $149/mo",
        "parsed_tables": curr_tables,
        "previous_snapshot": {"parsed_tables": prev_tables},
        "logs": []
    }
    result = analyst_node(state)
    assert len(result["anomaly_flags"]) == 1
    anomaly = result["anomaly_flags"][0]
    assert anomaly["pct_change"] > 0

def test_analyst_node_text_sla_change():
    curr_tables = [[{"tier": "Growth", "sla_guarantee": "Removed"}]]
    prev_tables = [[{"tier": "Growth", "sla_guarantee": "10,000 req/min"}]]
    state = {
        "competitor_name": "DataPulse AI",
        "raw_text": "Growth tier SLA Removed",
        "parsed_tables": curr_tables,
        "previous_snapshot": {"parsed_tables": prev_tables},
        "logs": []
    }
    result = analyst_node(state)
    assert len(result["anomaly_flags"]) == 1
    anomaly = result["anomaly_flags"][0]
    assert anomaly["type"] == "feature_removal"
    assert anomaly["severity"] == "high"

def test_analyst_node_added_and_removed_plans():
    curr_tables = [[{"tier": "Enterprise", "rate": "$399"}, {"tier": "Ultra", "rate": "$999"}]]
    prev_tables = [[{"tier": "Enterprise", "rate": "$399"}, {"tier": "Starter", "rate": "$29"}]]
    state = {
        "competitor_name": "ApexScale",
        "raw_text": "Enterprise $399, Ultra $999",
        "parsed_tables": curr_tables,
        "previous_snapshot": {"parsed_tables": prev_tables},
        "logs": []
    }
    result = analyst_node(state)
    types = [a["type"] for a in result["anomaly_flags"]]
    assert "plan_added" in types
    assert "plan_removed" in types
