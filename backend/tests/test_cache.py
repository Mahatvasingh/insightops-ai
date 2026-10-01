import pytest
import threading
from app.core.cache import TTLCache

def test_ttl_cache_basic_and_stats():
    cache = TTLCache()
    cache.set("scrape", "http://test.com", {"data": 123}, ttl_seconds=60)
    val = cache.get("scrape", "http://test.com")
    assert val == {"data": 123}

    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 0

    miss = cache.get("scrape", "http://nonexistent.com")
    assert miss is None
    assert cache.stats()["misses"] == 1

def test_ttl_cache_concurrent_access():
    cache = TTLCache()
    threads = []

    def worker():
        for i in range(100):
            cache.set("test", f"key_{i}", f"val_{i}", ttl_seconds=10)
            _ = cache.get("test", f"key_{i}")
            cache.record_llm_call(tokens=10)

    for _ in range(10):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    stats = cache.stats()
    assert stats["hits"] == 1000
    assert stats["llm_calls"] == 1000
    assert stats["llm_tokens_total"] == 10000
