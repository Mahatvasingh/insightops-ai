import hashlib
import json
from typing import Dict, Any, List

class DataParser:
    """
    Ingestion Parser & Schema Normalizer.
    Converts raw scraped tables into clean Pandas/DuckDB readable dictionary lists.
    Computes SHA-256 payload content hashes for change detection.
    """

    @staticmethod
    def compute_content_hash(text: str) -> str:
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    @staticmethod
    def parse_table_to_records(table: List[List[str]]) -> List[Dict[str, Any]]:
        if not table or len(table) < 2:
            return []

        headers = [str(h).strip().replace(" ", "_").lower() for h in table[0]]
        records = []
        for row in table[1:]:
            record = {}
            for idx, cell in enumerate(row):
                if idx < len(headers):
                    key = headers[idx]
                    record[key] = cell.strip()
            records.append(record)
        return records

    @classmethod
    def process_ingestion_payload(cls, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        tables = raw_payload.get("tables", [])
        parsed_tables = [cls.parse_table_to_records(t) for t in tables if t]

        content_hash = cls.compute_content_hash(raw_payload.get("raw_text", ""))

        return {
            "url": raw_payload.get("url"),
            "title": raw_payload.get("title"),
            "content_hash": content_hash,
            "raw_text": raw_payload.get("raw_text"),
            "parsed_tables": parsed_tables,
            "status_code": raw_payload.get("status_code", 200)
        }
