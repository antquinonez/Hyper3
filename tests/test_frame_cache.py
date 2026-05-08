from hyper3.frame_cache import FrameCache, FrameCacheStats


class TestFrameCachePutGet:
    def test_put_get_same_frame(self):
        fc = FrameCache(max_total_size=100, frame_quota=20)
        fc.put("k1", "v1", frame="classical")
        assert fc.get("k1", frame="classical") == "v1"

    def test_put_get_general(self):
        fc = FrameCache(max_total_size=100, frame_quota=20)
        fc.put("k1", "v1")
        assert fc.get("k1") == "v1"

    def test_get_missing_returns_none(self):
        fc = FrameCache()
        assert fc.get("missing") is None
        assert fc.get("missing", frame="classical") is None

    def test_put_overwrites(self):
        fc = FrameCache(max_total_size=100, frame_quota=20)
        fc.put("k1", "old", frame="quantum")
        fc.put("k1", "new", frame="quantum")
        assert fc.get("k1", frame="quantum") == "new"


class TestFrameIsolation:
    def test_different_frames_isolated(self):
        fc = FrameCache(max_total_size=100, frame_quota=20)
        fc.put("k1", "classical_val", frame="classical")
        fc.put("k1", "quantum_val", frame="quantum")
        assert fc.get("k1", frame="classical") == "classical_val"
        assert fc.get("k1", frame="quantum") == "quantum_val"

    def test_get_falls_through_to_general(self):
        fc = FrameCache(max_total_size=100, frame_quota=20)
        fc.put("k1", "v1")
        assert fc.get("k1", frame="classical") == "v1"

    def test_frame_put_also_in_general(self):
        fc = FrameCache(max_total_size=100, frame_quota=20)
        fc.put("k1", "v1", frame="hypergraph")
        assert fc.get("k1") == "v1"

    def test_frame_preferred_over_general(self):
        fc = FrameCache(max_total_size=100, frame_quota=20)
        fc.put("k1", "general_val")
        fc.put("k1", "frame_val", frame="classical")
        assert fc.get("k1", frame="classical") == "frame_val"

    def test_cross_frame_no_eviction(self):
        fc = FrameCache(max_total_size=100, frame_quota=20)
        for i in range(15):
            fc.put(f"ck_{i}", f"cv_{i}", frame="classical")
        for i in range(15):
            fc.put(f"qk_{i}", f"qv_{i}", frame="quantum")
        for i in range(15):
            assert fc.get(f"ck_{i}", frame="classical") == f"cv_{i}"
        for i in range(15):
            assert fc.get(f"qk_{i}", frame="quantum") == f"qv_{i}"


class TestEnsureFrame:
    def test_ensure_frame_borrows_from_general(self):
        fc = FrameCache(max_total_size=100, frame_quota=20)
        assert fc._general._max_size == 100
        fc.put("k", "v", frame="new_frame")
        assert fc._general._max_size == 80
        assert "new_frame" in fc._frames

    def test_ensure_frame_minimum_general_preserved(self):
        fc = FrameCache(max_total_size=60, frame_quota=30)
        fc.put("k1", "v1", frame="frame_a")
        assert fc._general._max_size == 30
        fc.put("k2", "v2", frame="frame_b")
        assert fc._general._max_size == 30

    def test_ensure_frame_idempotent(self):
        fc = FrameCache(max_total_size=100, frame_quota=20)
        fc.put("k1", "v1", frame="x")
        size_after_first = fc._general._max_size
        fc.put("k2", "v2", frame="x")
        assert fc._general._max_size == size_after_first


class TestInvalidation:
    def test_invalidate_frame_clears_only_target(self):
        fc = FrameCache(max_total_size=100, frame_quota=20)
        fc.put("k1", "v1", frame="classical")
        fc.put("k2", "v2", frame="quantum")
        count = fc.invalidate_frame("classical")
        assert count == 1
        assert fc.get("k1", frame="classical") is None
        assert fc.get("k2", frame="quantum") == "v2"

    def test_invalidate_frame_nonexistent(self):
        fc = FrameCache()
        assert fc.invalidate_frame("nope") == 0

    def test_invalidate_key_from_frame(self):
        fc = FrameCache(max_total_size=100, frame_quota=20)
        fc.put("k1", "v1", frame="classical")
        fc.put("k2", "v2", frame="classical")
        assert fc.invalidate("k1", frame="classical")
        assert fc.get("k1", frame="classical") is None
        assert fc.get("k2", frame="classical") == "v2"

    def test_invalidate_key_from_general(self):
        fc = FrameCache()
        fc.put("k1", "v1")
        assert fc.invalidate("k1")
        assert fc.get("k1") is None

    def test_invalidate_missing_returns_false(self):
        fc = FrameCache()
        assert not fc.invalidate("missing")

    def test_clear_removes_everything(self):
        fc = FrameCache(max_total_size=100, frame_quota=20)
        fc.put("k1", "v1", frame="classical")
        fc.put("k2", "v2", frame="quantum")
        fc.put("k3", "v3")
        fc.clear()
        assert fc.get("k1", frame="classical") is None
        assert fc.get("k2", frame="quantum") is None
        assert fc.get("k3") is None


class TestEviction:
    def test_evict_expired_all_partitions(self):
        fc = FrameCache(max_total_size=100, frame_quota=20, default_ttl=0.01)
        fc.put("k1", "v1", frame="classical")
        fc.put("k2", "v2")
        import time
        time.sleep(0.02)
        evicted = fc.evict_expired()
        assert evicted >= 2
        assert fc.get("k1", frame="classical") is None
        assert fc.get("k2") is None

    def test_frame_quota_eviction(self):
        fc = FrameCache(max_total_size=100, frame_quota=5)
        for i in range(10):
            fc.put(f"k_{i}", f"v_{i}", frame="classical")
        assert fc._frames["classical"].size <= 5


class TestStats:
    def test_stats_empty(self):
        fc = FrameCache()
        s = fc.stats()
        assert isinstance(s, FrameCacheStats)
        assert s.total_entries == 0
        assert s.general_size == 0

    def test_stats_reflects_partition_usage(self):
        fc = FrameCache(max_total_size=100, frame_quota=20)
        fc.put("k1", "v1", frame="classical")
        fc.put("k2", "v2", frame="quantum")
        fc.put("k3", "v3")
        s = fc.stats()
        assert s.total_entries >= 3
        assert len(s.frame_partitions) == 2
        classical = [p for p in s.frame_partitions if p.frame == "classical"][0]
        assert classical.size == 1

    def test_stats_utilization(self):
        fc = FrameCache(max_total_size=100, frame_quota=20)
        fc.put("k1", "v1", frame="classical")
        s = fc.stats()
        assert 0.0 < s.total_utilization < 1.0


class TestRebalance:
    def test_rebalance_proportional_to_usage(self):
        fc = FrameCache(max_total_size=200, frame_quota=20)
        for i in range(10):
            fc.put(f"a_{i}", i, frame="frame_a")
        for i in range(2):
            fc.put(f"b_{i}", i, frame="frame_b")
        fc.rebalance()
        assert fc._frames["frame_a"]._max_size > fc._frames["frame_b"]._max_size

    def test_rebalance_preserves_minimum_quotas(self):
        fc = FrameCache(max_total_size=200, frame_quota=20)
        fc.put("a", 1, frame="frame_a")
        fc.put("b", 2, frame="frame_b")
        fc.rebalance()
        assert fc._frames["frame_a"]._max_size >= 20
        assert fc._frames["frame_b"]._max_size >= 20

    def test_rebalance_empty_noop(self):
        fc = FrameCache(max_total_size=100, frame_quota=20)
        fc.put("k", "v", frame="x")
        fc.clear()
        fc.rebalance()


class TestResize:
    def test_resize_frame(self):
        fc = FrameCache(max_total_size=100, frame_quota=20)
        fc.put("k", "v", frame="x")
        fc.resize_frame("x", 50)
        assert fc._frames["x"]._max_size == 50

    def test_resize_nonexistent_noop(self):
        fc = FrameCache()
        fc.resize_frame("nope", 100)


class TestKeys:
    def test_keys_general(self):
        fc = FrameCache()
        fc.put("k1", "v1")
        fc.put("k2", "v2")
        assert set(fc.keys()) == {"k1", "k2"}

    def test_keys_frame(self):
        fc = FrameCache(max_total_size=100, frame_quota=20)
        fc.put("k1", "v1", frame="classical")
        fc.put("k2", "v2", frame="quantum")
        assert "k1" in fc.keys(frame="classical")

    def test_keys_frame_nonexistent(self):
        fc = FrameCache()
        assert fc.keys(frame="nope") == []


class TestSerialization:
    def test_to_dict_from_dict_roundtrip(self):
        fc = FrameCache(max_total_size=200, frame_quota=30, default_ttl=600.0)
        fc.put("k1", "v1", frame="classical")
        fc.put("k2", "v2", frame="quantum")
        d = fc.to_dict()
        assert d["max_total_size"] == 200
        assert d["frame_quota"] == 30
        assert "classical" in d["frame_sizes"]
        fc2 = FrameCache.from_dict(d)
        assert fc2._max_total_size == 200
        assert fc2._frame_quota == 30
        assert fc2._default_ttl == 600.0
        assert "classical" in fc2._frames
        assert "quantum" in fc2._frames
