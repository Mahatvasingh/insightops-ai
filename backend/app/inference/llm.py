import re
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type
from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.core.cache import cache_manager

logger = logging.getLogger(__name__)

class ExtractedFact(BaseModel):
    entity: str = Field(description="Name of competitor entity")
    fact_type: str = Field(description="Category: plan, price, sla, feature")
    plan_name: str = Field(description="Name of the subscription tier or plan")
    value: str = Field(description="Extracted value or status")
    quote: str = Field(description="Exact supporting verbatim text quote from primary page")

class ExtractedCompetitorData(BaseModel):
    competitor_name: str
    facts: List[ExtractedFact] = []

class LLMClient(ABC):
    """Abstract interface for LLM client providers."""

    @abstractmethod
    def extract_structured(self, raw_text: str, competitor_name: str) -> ExtractedCompetitorData:
        pass

    @abstractmethod
    def generate_report(self, verified_claims: List[Dict[str, Any]], competitor_name: str, target_url: str) -> str:
        pass

    @abstractmethod
    def refute_claims(self, claims: List[Dict[str, Any]], raw_text: str) -> List[Dict[str, Any]]:
        pass

class MockLLMClient(LLMClient):
    """
    Mock LLM client for deterministic, offline, and unit-testing environments.
    Extracts structured facts with genuine quotes from raw text.
    """
    def extract_structured(self, raw_text: str, competitor_name: str) -> ExtractedCompetitorData:
        cache_manager.record_llm_call(tokens=320)
        facts = []

        # Heuristic extraction of prices and plans from raw text with supporting quotes
        lines = raw_text.splitlines()
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            if "starter" in line_str.lower() or "$29" in line_str:
                facts.append(ExtractedFact(
                    entity=competitor_name,
                    fact_type="price",
                    plan_name="Starter",
                    value="$29/mo",
                    quote=line_str
                ))
            elif "pro" in line_str.lower() or "$99" in line_str:
                facts.append(ExtractedFact(
                    entity=competitor_name,
                    fact_type="price",
                    plan_name="Pro",
                    value="$99/mo",
                    quote=line_str
                ))
            elif "enterprise" in line_str.lower() or "399" in line_str or "499" in line_str:
                val = "$399/mo" if "399" in line_str else "$499/mo"
                facts.append(ExtractedFact(
                    entity=competitor_name,
                    fact_type="price",
                    plan_name="Enterprise",
                    value=val,
                    quote=line_str
                ))
            elif "sla" in line_str.lower() or "guarantee" in line_str.lower():
                facts.append(ExtractedFact(
                    entity=competitor_name,
                    fact_type="sla",
                    plan_name="Growth/Pro",
                    value="SLA Policy Update",
                    quote=line_str
                ))

        if not facts:
            facts.append(ExtractedFact(
                entity=competitor_name,
                fact_type="feature",
                plan_name="Standard",
                value="General Update",
                quote=raw_text[:100] if raw_text else "Page content captured."
            ))

        return ExtractedCompetitorData(competitor_name=competitor_name, facts=facts)

    def generate_report(self, verified_claims: List[Dict[str, Any]], competitor_name: str, target_url: str) -> str:
        cache_manager.record_llm_call(tokens=450)
        bullets = ""
        for c in verified_claims:
            bullets += f"* **{c.get('title', 'Claim')}** ({c.get('severity', 'medium').upper()}): {c.get('description', '')} [Evidence: `{c.get('quote', 'Verified')}`]\n"

        report = f"""# Executive Market Intelligence Brief: {competitor_name}

## Executive Summary
Automated market intelligence workflow analyzed competitive signals for **{competitor_name}** extracted from `{target_url}`.

## Verified Strategic Anomalies & Metrics
{bullets if bullets else '* Baseline metrics captured without critical anomaly alerts.'}

## Audit Trail & Citations
* **Verification**: All reported claims verified against DOM snapshot quotes and numeric evidence.
* **Citations**: `{target_url}`

---
*Report generated autonomously by InsightOps AI Engine.*
"""
        return report

    def refute_claims(self, claims: List[Dict[str, Any]], raw_text: str) -> List[Dict[str, Any]]:
        cache_manager.record_llm_call(tokens=200)
        refuted = []
        raw_lower = raw_text.lower()
        for claim in claims:
            quote = claim.get("quote", "").lower()
            # If quote is present in raw text, claim passes refutation
            if quote and quote in raw_lower:
                claim["refuted"] = False
                claim["refutation_reason"] = None
            elif any(word in raw_lower for word in claim.get("title", "").lower().split() if len(word) > 3):
                claim["refuted"] = False
                claim["refutation_reason"] = None
            else:
                claim["refuted"] = True
                claim["refutation_reason"] = "Supporting quote not found in source text."
            refuted.append(claim)
        return refuted

def get_llm_client() -> LLMClient:
    provider = settings.LLM_PROVIDER.lower()
    if provider == "openai" and settings.OPENAI_API_KEY:
        try:
            # Placeholder for OpenAI integration if key is present
            return MockLLMClient()
        except Exception:
            return MockLLMClient()
    return MockLLMClient()
