from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    """AgentState schema for LangGraph workflow execution."""
    thread_id: str
    competitor_id: str
    competitor_name: str
    target_url: str
    user_query: str
    force_refresh: bool
    
    # Ingestion & Scraped Data
    raw_text: str
    parsed_tables: List[List[Dict[str, Any]]]
    extracted_facts: List[Dict[str, Any]]
    content_hash: str
    source: str
    scrape_time: Optional[str]
    previous_snapshot: Optional[Any]
    previous_content_hash: Optional[str]

    # Quantitative Analysis & Plotly Specs
    quantitative_metrics: Dict[str, Any]
    anomaly_flags: List[Dict[str, Any]]
    plotly_spec: Dict[str, Any]

    # Adversarial Fact-Checking & Self-Correction
    fact_check_score: float
    fact_check_feedback: str
    revision_count: int

    # Human-in-the-Loop (HITL) Controls
    hitl_required: bool
    hitl_approved: Optional[bool]
    hitl_feedback: Optional[str]

    # Writer Output & Final Report
    writer_draft: str
    final_report: str
    citations: List[Dict[str, Any]]

    # Pipeline Metadata & Telemetry Logs
    status: str  # initialized, researching, analyzing, fact_checking, writing, awaiting_hitl, completed, failed, rejected, unchanged
    current_node: str
    token_usage: Dict[str, Any]
    logs: List[Dict[str, Any]]
