import pytest
from app.core.cache import TTLCache

def test_ttl_cache_counters_and_hit_rate():
    cache = TTLCache()
    cache.set("test", "key1", "val1", ttl_seconds=3600)

    # Miss before entry exists
    assert cache.get("test", "nonexistent") is None
    assert cache.misses == 1

    # Hit for existing key
    assert cache.get("test", "key1") == "val1"
    assert cache.hits == 1

    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate_pct"] == 50.0

def test_ttl_cache_expired_key():
    cache = TTLCache()
    cache.set("test", "exp_key", "val", ttl_seconds=-10)  # Already expired
    assert cache.get("test", "exp_key") is None
    assert cache.misses == 1
