from datetime import datetime, timezone
from typing import Dict, Any
from app.inference.state import AgentState
from app.ingestion.scraper import WebScraperEngine
from app.ingestion.parser import DataParser

def researcher_node(state: AgentState) -> Dict[str, Any]:
    """
    Researcher / Extraction Agent Node.
    Triggers web scraping pipeline, strips clutter, extracts structured text & tables,
    and logs step telemetry.
    """
    target_url = state.get("target_url", "https://saasify.cloud/pricing")
    competitor_name = state.get("competitor_name", "Target Competitor")
    
    logs = list(state.get("logs", []))
    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": "Researcher",
        "message": f"Scraping & extracting live web data for {competitor_name} from {target_url}"
    })

    # Execute Ingestion pipeline
    raw_payload = WebScraperEngine.scrape_url(target_url, force_refresh=True)
    processed = DataParser.process_ingestion_payload(raw_payload)

    # Extract structured facts from scraped payload
    raw_text = processed.get("raw_text", "")
    parsed_tables = processed.get("parsed_tables", [])

    facts = [
        {"entity": competitor_name, "source": target_url, "fact": f"Title: {processed.get('title')}"},
        {"entity": competitor_name, "source": target_url, "fact": f"Scraped text snippet: {raw_text[:200]}..."}
    ]

    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": "Researcher",
        "message": f"Successfully extracted {len(raw_text)} chars and {len(parsed_tables)} structured table(s)."
    })

    return {
        "raw_text": raw_text,
        "parsed_tables": parsed_tables,
        "extracted_facts": facts,
        "status": "researching_complete",
        "current_node": "Researcher",
        "logs": logs
    }
