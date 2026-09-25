from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    """
    LangGraph AgentState schema for InsightOps AI multi-agent market intelligence workflow.
    Stores shared execution state passed cyclically between Supervisor, Researcher,
    Quantitative Analyst, Adversarial Fact-Checker, and Executive Writer nodes.
    """
    thread_id: str
    competitor_id: str
    competitor_name: str
    target_url: str
    user_query: str
    
    # Ingestion & Scraped Data
    raw_text: str
    parsed_tables: List[List[Dict[str, Any]]]
    extracted_facts: List[Dict[str, Any]]

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

    # Pipeline Metadata & Streaming Telemetry Logs
    status: str  # initialized, researching, analyzing, fact_checking, writing, awaiting_hitl, completed, failed
    current_node: str
    logs: List[Dict[str, Any]]
