from datetime import datetime, timezone
from typing import Dict, Any
from pydantic import ValidationError

from app.inference.state import AgentState
from app.ingestion.scraper import WebScraperEngine
from app.ingestion.parser import DataParser
from app.inference.llm import get_llm_client, ExtractedCompetitorData

def researcher_node(state: AgentState) -> Dict[str, Any]:
    """
    Researcher / Extraction Agent Node.
    Scrapes target web page, parses structured tables, computes content hash,
    and extracts facts using LLM client schema validation with retry cap.
    """
    target_url = state.get("target_url", "https://saasify.cloud/pricing")
    competitor_name = state.get("competitor_name", "Target Competitor")
    force_refresh = state.get("force_refresh", False)
    logs = list(state.get("logs", []))

    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": "Researcher",
        "message": f"Scraping web data for {competitor_name} at {target_url} (Cache allowed)."
    })

    # Execute Scraper (force_refresh=False by default)
    raw_payload = WebScraperEngine.scrape_url(target_url, force_refresh=force_refresh)
    processed = DataParser.process_ingestion_payload(raw_payload)

    raw_text = processed.get("raw_text", "")
    parsed_tables = processed.get("parsed_tables", [])
    content_hash = processed.get("content_hash", "")
    source = processed.get("source", "demo")
    scrape_time = processed.get("scrape_time")

    # LLM extraction with schema validation retries (max 2 retries)
    llm_client = get_llm_client()
    extracted_data = None
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            extracted_data = llm_client.extract_structured(raw_text, competitor_name)
            break
        except (ValidationError, Exception) as err:
            if attempt == max_retries:
                logs.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "node": "Researcher",
                    "message": f"LLM schema extraction failed after {max_retries} retries: {err}"
                })

    facts_list = []
    if extracted_data and extracted_data.facts:
        for f in extracted_data.facts:
            facts_list.append(f.dict())
    else:
        facts_list = [
            {
                "entity": competitor_name,
                "fact_type": "extraction",
                "plan_name": "General",
                "value": "Baseline content extracted",
                "quote": raw_text[:150] if raw_text else "Page content captured."
            }
        ]

    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": "Researcher",
        "message": f"Extracted {len(facts_list)} structured fact(s). Source: {source}, Hash: {content_hash[:8]}..."
    })

    return {
        "raw_text": raw_text,
        "parsed_tables": parsed_tables,
        "extracted_facts": facts_list,
        "content_hash": content_hash,
        "source": source,
        "scrape_time": scrape_time,
        "status": "researching_complete",
        "current_node": "Researcher",
        "logs": logs
    }
