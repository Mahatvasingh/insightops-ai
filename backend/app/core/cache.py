import time
import json
import hashlib
import threading
from typing import Any, Optional, Dict

class TTLCache:
    """In-memory key-value cache with automatic TTL expiration, thread safety, and telemetry metrics."""
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self.hits: int = 0
        self.misses: int = 0
        self.llm_calls: int = 0
        self.llm_tokens_total: int = 0

    def _generate_key(self, prefix: str, raw_key: str) -> str:
        hashed = hashlib.sha256(raw_key.encode('utf-8')).hexdigest()
        return f"{prefix}:{hashed}"

    def get(self, prefix: str, key: str) -> Optional[Any]:
        cache_key = self._generate_key(prefix, key)
        with self._lock:
            entry = self._store.get(cache_key)
            if not entry:
                self.misses += 1
                return None
            
            if time.time() > entry["expires_at"]:
                del self._store[cache_key]
                self.misses += 1
                return None
            
            self.hits += 1
            return entry["value"]

    def set(self, prefix: str, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        cache_key = self._generate_key(prefix, key)
        with self._lock:
            self._store[cache_key] = {
                "value": value,
                "expires_at": time.time() + ttl_seconds
            }

    def record_llm_call(self, tokens: int = 0) -> None:
        with self._lock:
            self.llm_calls += 1
            self.llm_tokens_total += tokens

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self.hits = 0
            self.misses = 0
            self.llm_calls = 0
            self.llm_tokens_total = 0

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            active = sum(1 for e in self._store.values() if e["expires_at"] > now)
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100.0) if total_requests > 0 else 0.0

            return {
                "total_keys": len(self._store),
                "active_keys": active,
                "expired_keys": len(self._store) - active,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate_pct": round(hit_rate, 2),
                "llm_calls": self.llm_calls,
                "llm_tokens_total": self.llm_tokens_total
            }

cache_manager = TTLCache()
