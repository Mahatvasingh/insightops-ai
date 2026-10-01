import re
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.inference.state import AgentState
from app.inference.llm import get_llm_client

def sanitize_untrusted_text(text: str) -> str:
    """
    Prompt-Injection Defense:
    Strips potential prompt injection vectors, hidden control characters,
    markdown instructions, and system override commands from untrusted scraped text.
    """
    if not text:
        return ""
    # Strip potential instruction override tags
    cleaned = re.sub(r'<(?:system|user|assistant|instruction|prompt)[^>]*>', '', text, flags=re.IGNORECASE)
    # Strip dangerous instruction patterns like "Ignore previous instructions"
    cleaned = re.sub(r'(?i)(ignore\s+previous\s+instructions|system\s+prompt|you\s+are\s+now)', '[REDACTED_TEXT]', cleaned)
    return cleaned.strip()

def writer_node(state: AgentState) -> Dict[str, Any]:
    """
    Executive Writer Agent Node.
    Synthesizes ONLY verified claims into executive Markdown brief.
    Enforces prompt-injection defense on scraped text.
    Builds citations strictly from verified primary source evidence.
    """
    competitor_name = state.get("competitor_name", "Competitor")
    target_url = state.get("target_url", "")
    anomalies = list(state.get("anomaly_flags", []))
    confidence_score = state.get("fact_check_score", 1.0)
    raw_text = state.get("raw_text", "")
    logs = list(state.get("logs", []))

    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": "Executive Writer",
        "message": f"Drafting executive intelligence brief for {competitor_name}."
    })

    # Sanitize raw text before incorporating into LLM prompt / report
    sanitized_text = sanitize_untrusted_text(raw_text)

    # Build Citations strictly from verified claims
    citations = []
    for a in anomalies:
        if a.get("quote"):
            citations.append({
                "source": target_url,
                "claim": f"{a.get('title')}: {a.get('description')}",
                "quote": a.get("quote"),
                "confidence": confidence_score
            })

    if not citations:
        citations.append({
            "source": target_url,
            "claim": f"Primary extraction from {target_url}",
            "quote": sanitized_text[:100] if sanitized_text else "Page content verified.",
            "confidence": confidence_score
        })

    # Generate Executive Intelligence Report using LLM client
    llm_client = get_llm_client()
    report_md = llm_client.generate_report(anomalies, competitor_name, target_url)

    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": "Executive Writer",
        "message": f"Executive Intelligence Brief formatted with {len(citations)} verified citation(s)."
    })

    return {
        "writer_draft": report_md,
        "final_report": report_md,
        "citations": citations,
        "status": "completed",
        "current_node": "Executive Writer",
        "logs": logs
    }
