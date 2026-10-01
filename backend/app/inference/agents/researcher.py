from datetime import datetime, timezone
from typing import Dict, Any
from app.config import settings
from app.inference.state import AgentState
from app.ingestion.scraper import WebScraperEngine
from app.ingestion.parser import DataParser
from app.inference.llm import get_llm_client
from app.db.database import SyncSessionLocal
from app.db.models import ScrapingTarget

def researcher_node(state: AgentState) -> Dict[str, Any]:
    """
    Researcher / Extraction Agent Node.
    - Queries ScrapingTarget for previous snapshot_data and content_hash.
    - Handles demo versioning naturally (v1 on baseline run, v2 on subsequent runs).
    - If content_hash is unchanged, short-circuits execution with 0 LLM calls.
    - Updates ScrapingTarget DB record upon successful scrape.
    """
    competitor_id = state.get("competitor_id")
    target_url = state.get("target_url", "https://saasify.cloud/pricing")
    competitor_name = state.get("competitor_name", "Target Competitor")
    force_refresh = state.get("force_refresh", False)
    logs = list(state.get("logs", []))
    token_usage = dict(state.get("token_usage", {"calls": 0, "tokens": 0, "nodes": {}}))

    previous_snapshot = state.get("previous_snapshot")
    previous_content_hash = state.get("previous_content_hash")
    demo_version = "v1"

    # 1. Lookup ScrapingTarget in DB
    if competitor_id:
        db = SyncSessionLocal()
        try:
            target = db.query(ScrapingTarget).filter(
                ScrapingTarget.competitor_id == competitor_id,
                ScrapingTarget.url == target_url
            ).first()

            if not target:
                target = ScrapingTarget(
                    competitor_id=competitor_id,
                    url=target_url,
                    target_type="pricing"
                )
                db.add(target)
                db.commit()

            if target and target.content_hash and target.last_scraped_at:
                previous_snapshot = previous_snapshot or target.snapshot_data
                previous_content_hash = previous_content_hash or target.content_hash
                demo_version = "v2"
        except Exception as e:
            db.rollback()
        finally:
            db.close()

    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": "Researcher",
        "message": f"Scraping web data for {competitor_name} at {target_url} (Demo version: {demo_version})."
    })

    # 2. Scrape payload
    raw_payload = WebScraperEngine.scrape_url(target_url, force_refresh=force_refresh, version=demo_version)
    processed = DataParser.process_ingestion_payload(raw_payload)

    raw_text = processed.get("raw_text", "")
    parsed_tables = processed.get("parsed_tables", [])
    new_content_hash = processed.get("content_hash", "")
    source = processed.get("source", "demo")
    scrape_time = processed.get("scrape_time")
    status_code = processed.get("status_code", 200)

    # Check for scrape failure
    if status_code >= 400 or processed.get("error"):
        error_msg = processed.get("error") or f"HTTP status code {status_code}"
        logs.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "node": "Researcher",
            "message": f"Scrape failed for {target_url}: {error_msg}"
        })
        return {
            "raw_text": raw_text,
            "parsed_tables": parsed_tables,
            "extracted_facts": [],
            "status": "failed",
            "current_node": "Researcher",
            "token_usage": token_usage,
            "logs": logs
        }

    # 3. Change Detection Short-Circuit
    if previous_content_hash and new_content_hash == previous_content_hash and not force_refresh:
        logs.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "node": "Researcher",
            "message": f"Content hash unchanged ({new_content_hash[:8]}...). Short-circuiting pipeline with 0 LLM calls."
        })
        return {
            "raw_text": raw_text,
            "parsed_tables": parsed_tables,
            "extracted_facts": [],
            "content_hash": new_content_hash,
            "previous_content_hash": previous_content_hash,
            "previous_snapshot": previous_snapshot,
            "source": source,
            "scrape_time": scrape_time,
            "anomaly_flags": [],
            "final_report": "Target page content is unchanged. No new anomalies detected.",
            "status": "unchanged",
            "current_node": "Researcher",
            "token_usage": token_usage,
            "logs": logs
        }

    # 4. Structured Extraction
    llm_client = get_llm_client()
    extracted_data = None
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            extracted_data = llm_client.extract_structured(raw_text, competitor_name)
            break
        except Exception as err:
            if attempt == max_retries:
                logs.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "node": "Researcher",
                    "message": f"Schema extraction failed after retries: {err}"
                })

    facts_list = [f.model_dump() if hasattr(f, 'model_dump') else f.dict() for f in (extracted_data.facts if extracted_data else [])]

    # Track node token usage per run
    node_tokens = token_usage.get("nodes", {})
    r_tokens = 320
    token_usage["calls"] = token_usage.get("calls", 0) + 1
    token_usage["tokens"] = token_usage.get("tokens", 0) + r_tokens
    node_tokens["Researcher"] = node_tokens.get("Researcher", 0) + r_tokens
    token_usage["nodes"] = node_tokens

    # 5. Persist updated snapshot_data & content_hash on ScrapingTarget DB row AFTER successful scrape
    if competitor_id:
        db = SyncSessionLocal()
        try:
            t = db.query(ScrapingTarget).filter(
                ScrapingTarget.competitor_id == competitor_id,
                ScrapingTarget.url == target_url
            ).first()
            if t:
                t.content_hash = new_content_hash
                t.snapshot_data = {"raw_text": raw_text, "parsed_tables": parsed_tables}
                t.last_scraped_at = datetime.now(timezone.utc)
                t.status_code = status_code
                db.commit()
        except Exception as e:
            db.rollback()
        finally:
            db.close()

    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": "Researcher",
        "message": f"Extracted {len(facts_list)} structured fact(s). Source: {source}, Hash: {new_content_hash[:8]}..."
    })

    return {
        "raw_text": raw_text,
        "parsed_tables": parsed_tables,
        "extracted_facts": facts_list,
        "content_hash": new_content_hash,
        "previous_content_hash": previous_content_hash,
        "previous_snapshot": previous_snapshot,
        "source": source,
        "scrape_time": scrape_time,
        "status": "researching_complete",
        "current_node": "Researcher",
        "token_usage": token_usage,
        "logs": logs
    }
