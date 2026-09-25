import time
import json
import hashlib
from typing import Any, Optional, Dict

class TTLCache:
    """In-memory key-value cache with automatic TTL expiration."""
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    def _generate_key(self, prefix: str, raw_key: str) -> str:
        hashed = hashlib.sha256(raw_key.encode('utf-8')).hexdigest()
        return f"{prefix}:{hashed}"

    def get(self, prefix: str, key: str) -> Optional[Any]:
        cache_key = self._generate_key(prefix, key)
        entry = self._store.get(cache_key)
        if not entry:
            return None
        
        if time.time() > entry["expires_at"]:
            del self._store[cache_key]
            return None
        
        return entry["value"]

    def set(self, prefix: str, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        cache_key = self._generate_key(prefix, key)
        self._store[cache_key] = {
            "value": value,
            "expires_at": time.time() + ttl_seconds
        }

    def clear(self) -> None:
        self._store.clear()

    def stats(self) -> Dict[str, Any]:
        now = time.time()
        active = sum(1 for e in self._store.values() if e["expires_at"] > now)
        return {
            "total_keys": len(self._store),
            "active_keys": active,
            "expired_keys": len(self._store) - active
        }

cache_manager = TTLCache()
