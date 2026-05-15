import time

import pytest

from hyper3.cache import LazyCache


class TestContextAwareCache:
    def test_context_aware_construction(self):
        cache = LazyCache(context_aware=True)
        assert cache._context_aware is True
        assert cache._context_tags == {}
        assert cache._active_context == set()

    def test_set_with_context_tags(self):
        cache = LazyCache(context_aware=True)
        cache.set("k1", "v1", context_tags={"causal", "retrieval"})
        assert cache._context_tags["k1"] == {"causal", "retrieval"}
        assert cache.get("k1") == "v1"

    def test_set_without_context_tags(self):
        cache = LazyCache(context_aware=True)
        cache.set("k1", "v1")
        assert "k1" not in cache._context_tags
        assert cache.get("k1") == "v1"

    def test_set_active_context(self):
        cache = LazyCache(context_aware=True)
        cache.set_active_context({"temporal", "causal"})
        assert cache._active_context == {"temporal", "causal"}

    def test_eviction_prefers_out_of_context(self):
        cache = LazyCache(max_size=3, context_aware=True)
        cache.set_active_context({"causal"})
        cache.set("a", 1, context_tags={"causal"})
        cache.set("b", 2, context_tags={"temporal"})
        cache.set("c", 3, context_tags={"temporal"})
        cache.set("d", 4, context_tags={"causal"})
        assert cache.size == 3
        assert cache.get("a") is not None
        assert cache.get("d") is not None
        assert cache.get("b") is None or cache.get("c") is None

    def test_eviction_preserves_in_context(self):
        cache = LazyCache(max_size=3, context_aware=True)
        cache.set_active_context({"causal"})
        cache.set("in1", 1, context_tags={"causal"})
        cache.set("out1", 2, context_tags={"temporal"})
        cache.set("in2", 3, context_tags={"causal"})
        cache.set("out2", 4, context_tags={"temporal"})
        assert cache.size == 3
        assert cache.get("in1") is not None
        assert cache.get("in2") is not None
        remaining = [k for k in ["in1", "in2", "out1", "out2"] if cache.get(k) is not None]
        in_ctx = [k for k in remaining if k.startswith("in")]
        assert len(in_ctx) == 2

    def test_eviction_all_in_context_fallback(self):
        cache = LazyCache(max_size=2, context_aware=True)
        cache.set_active_context({"causal"})
        cache.set("a", 1, context_tags={"causal"})
        cache.set("b", 2, context_tags={"causal"})
        cache.set("c", 3, context_tags={"causal"})
        assert cache.size == 2
        assert cache.get("c") is not None
        assert cache.get("a") is None

    def test_eviction_no_active_context_lru(self):
        cache = LazyCache(max_size=2, context_aware=True)
        cache.set("a", 1, context_tags={"causal"})
        cache.set("b", 2, context_tags={"temporal"})
        cache.get("a")
        cache.set("c", 3, context_tags={"other"})
        assert cache.size == 2
        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3

    def test_ttl_boost_for_in_context(self):
        cache = LazyCache(ttl=0.1, context_aware=True)
        cache.set_active_context({"causal"})
        cache.set("k1", "v1", context_tags={"causal"})
        time.sleep(0.06)
        _ = cache.get("k1")
        time.sleep(0.06)
        assert cache.get("k1") is not None

    def test_ttl_normal_for_out_of_context(self):
        cache = LazyCache(ttl=0.1, context_aware=True)
        cache.set_active_context({"causal"})
        cache.set("k1", "v1", context_tags={"temporal"})
        time.sleep(0.12)
        assert cache.get("k1") is None

    def test_context_aware_false_no_behavior(self):
        cache = LazyCache(context_aware=False)
        cache.set("k1", "v1", context_tags={"causal"})
        assert "k1" not in cache._context_tags
        assert cache.get("k1") == "v1"

    def test_remove_cleans_context_tags(self):
        cache = LazyCache(context_aware=True)
        cache.set("k1", "v1", context_tags={"causal"})
        assert "k1" in cache._context_tags
        cache.invalidate("k1")
        assert "k1" not in cache._context_tags
        assert cache.get("k1") is None

    def test_empty_cache_no_eviction(self):
        cache = LazyCache(max_size=3, context_aware=True)
        cache._evict_for_capacity()
        assert cache.size == 0

    def test_put_delegates_to_set(self):
        cache = LazyCache(max_size=3, context_aware=True)
        cache.put("k1", "v1")
        assert cache.get("k1") == "v1"
        assert cache.size == 1

    def test_clear_clears_context_tags(self):
        cache = LazyCache(context_aware=True)
        cache.set("k1", "v1", context_tags={"causal"})
        cache.set("k2", "v2", context_tags={"temporal"})
        cache.clear()
        assert cache._context_tags == {}
        assert cache.size == 0

    def test_eviction_entries_without_tags_treated_as_in_context(self):
        cache = LazyCache(max_size=2, context_aware=True)
        cache.set_active_context({"causal"})
        cache.set("tagged", 1, context_tags={"temporal"})
        cache.set("untagged", 2)
        cache.set("also_tagged", 3, context_tags={"temporal"})
        assert cache.size == 2
        assert cache.get("untagged") is not None
