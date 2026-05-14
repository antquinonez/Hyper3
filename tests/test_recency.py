from __future__ import annotations

import time

import pytest

from hyper3.kernel import Hypergraph
from hyper3.recency import RecencyStats, RecencyTracker


class TestRecencyTrackerConstruction:
    def test_default_construction(self):
        g = Hypergraph()
        tracker = RecencyTracker(g)
        assert tracker.get_stats().total_nodes == 0

    def test_custom_decay_rate(self):
        g = Hypergraph()
        tracker = RecencyTracker(g, decay_rate=0.5)
        assert tracker._decay_rate == 0.5

    def test_custom_stale_threshold(self):
        g = Hypergraph()
        tracker = RecencyTracker(g, stale_threshold=5.0)
        assert tracker._stale_threshold == 5.0


class TestRecencyTouch:
    def test_touch_new_node_starts_at_one(self):
        g = Hypergraph()
        tracker = RecencyTracker(g)
        score = tracker.touch("node_a")
        assert score == 1.0

    def test_touch_repeated_increases_with_diminishing_returns(self):
        g = Hypergraph()
        tracker = RecencyTracker(g, decay_rate=0.5)
        s1 = tracker.touch("a")
        s2 = tracker.touch("a")
        s3 = tracker.touch("a")
        assert s1 == 1.0
        assert s2 == pytest.approx(1.5)
        assert s3 == pytest.approx(1.75)

    def test_touch_bounded_by_max_score(self):
        g = Hypergraph()
        tracker = RecencyTracker(g, max_score=2.0, decay_rate=0.999)
        tracker.touch("a")
        tracker.touch("a")
        tracker.touch("a")
        tracker.touch("a")
        assert tracker.get_recency("a") <= 2.0

    def test_touch_returns_current_score(self):
        g = Hypergraph()
        tracker = RecencyTracker(g)
        score = tracker.touch("a", now=1000.0)
        assert score == 1.0
        score2 = tracker.touch("a", now=1001.0)
        assert score2 > 1.0

    def test_touch_accepts_explicit_now(self):
        g = Hypergraph()
        tracker = RecencyTracker(g, update_interval=1e18)
        tracker.touch("a", now=100.0)
        tracker.touch("a", now=200.0)
        assert tracker.get_recency("a") > 1.0


class TestRecencyGetRecency:
    def test_unknown_node_returns_zero(self):
        g = Hypergraph()
        tracker = RecencyTracker(g)
        assert tracker.get_recency("nonexistent") == 0.0

    def test_touched_node_returns_score(self):
        g = Hypergraph()
        tracker = RecencyTracker(g)
        tracker.touch("a")
        assert tracker.get_recency("a") == 1.0


class TestRecencyGetTopRecent:
    def test_empty_tracker_returns_empty(self):
        g = Hypergraph()
        tracker = RecencyTracker(g)
        assert tracker.get_top_recent() == []

    def test_returns_sorted_descending(self):
        g = Hypergraph()
        tracker = RecencyTracker(g, decay_rate=0.5)
        tracker.touch("a")
        tracker.touch("b")
        tracker.touch("b")
        top = tracker.get_top_recent(limit=10)
        assert top[0][0] == "b"
        assert top[1][0] == "a"
        assert top[0][1] > top[1][1]

    def test_respects_limit(self):
        g = Hypergraph()
        tracker = RecencyTracker(g)
        for i in range(10):
            tracker.touch(f"n{i}")
        top = tracker.get_top_recent(limit=3)
        assert len(top) == 3


class TestRecencyGetStaleNodes:
    def test_no_stale_when_all_active(self):
        g = Hypergraph()
        tracker = RecencyTracker(g, stale_threshold=0.5)
        tracker.touch("a")
        assert tracker.get_stale_nodes() == []

    def test_stale_after_decay(self):
        g = Hypergraph()
        tracker = RecencyTracker(g, decay_rate=0.1, stale_threshold=0.5)
        tracker.touch("a")
        tracker.decay_all()
        stale = tracker.get_stale_nodes()
        assert "a" in stale

    def test_untouched_node_not_stale(self):
        g = Hypergraph()
        tracker = RecencyTracker(g)
        assert tracker.get_stale_nodes() == []


class TestRecencyDecayAll:
    def test_decay_reduces_scores(self):
        g = Hypergraph()
        tracker = RecencyTracker(g, decay_rate=0.5)
        tracker.touch("a")
        tracker.touch("a")
        before = tracker.get_recency("a")
        active = tracker.decay_all()
        after = tracker.get_recency("a")
        assert after < before
        assert active >= 1

    def test_decay_removes_near_zero_scores(self):
        g = Hypergraph()
        tracker = RecencyTracker(g, decay_rate=0.01)
        tracker.touch("a")
        for _ in range(5):
            tracker.decay_all()
        assert tracker.get_recency("a") == 0.0

    def test_decay_returns_active_count(self):
        g = Hypergraph()
        tracker = RecencyTracker(g, decay_rate=0.5)
        tracker.touch("a")
        tracker.touch("b")
        active = tracker.decay_all()
        assert active == 2

    def test_decay_accepts_explicit_now(self):
        g = Hypergraph()
        tracker = RecencyTracker(g)
        tracker.touch("a")
        tracker.decay_all(now=9999.0)
        assert tracker._last_decay == 9999.0


class TestRecencyGetStats:
    def test_empty_tracker_stats(self):
        g = Hypergraph()
        tracker = RecencyTracker(g)
        stats = tracker.get_stats()
        assert stats.total_nodes == 0
        assert stats.active_nodes == 0
        assert stats.avg_recency == 0.0
        assert stats.stale_count == 0

    def test_stats_after_touches(self):
        g = Hypergraph()
        tracker = RecencyTracker(g, decay_rate=0.5)
        tracker.touch("a")
        tracker.touch("b")
        tracker.touch("b")
        stats = tracker.get_stats()
        assert stats.total_nodes == 2
        assert stats.active_nodes == 2
        assert stats.avg_recency > 0.0
        assert len(stats.top_recent) == 2
        assert stats.top_recent[0][0] == "b"

    def test_stats_with_stale_nodes(self):
        g = Hypergraph()
        tracker = RecencyTracker(g, decay_rate=0.1, stale_threshold=0.5)
        tracker.touch("a")
        tracker.decay_all()
        stats = tracker.get_stats()
        assert stats.stale_count >= 1


class TestRecencySerialization:
    def test_to_dict_round_trip(self):
        g = Hypergraph()
        tracker = RecencyTracker(g, decay_rate=0.8, stale_threshold=2.0)
        tracker.touch("a")
        tracker.touch("b")
        data = tracker.to_dict()
        restored = RecencyTracker.from_dict(data, g)
        assert restored._decay_rate == 0.8
        assert restored._stale_threshold == 2.0
        assert restored.get_recency("a") == tracker.get_recency("a")
        assert restored.get_recency("b") == tracker.get_recency("b")

    def test_from_dict_defaults(self):
        g = Hypergraph()
        restored = RecencyTracker.from_dict({}, g)
        assert restored._decay_rate == 0.95


class TestRecencyEdgeCases:
    def test_decay_rate_zero_means_only_last_touch(self):
        g = Hypergraph()
        tracker = RecencyTracker(g, decay_rate=0.0)
        tracker.touch("a")
        tracker.touch("a")
        tracker.touch("a")
        assert tracker.get_recency("a") == 1.0

    def test_decay_rate_one_means_perfect_memory(self):
        g = Hypergraph()
        tracker = RecencyTracker(g, decay_rate=1.0, max_score=100.0)
        for _ in range(5):
            tracker.touch("a")
        assert tracker.get_recency("a") == 5.0

    def test_many_touches_approach_asymptote(self):
        g = Hypergraph()
        tracker = RecencyTracker(g, decay_rate=0.5, max_score=1e9)
        for _ in range(200):
            tracker.touch("a")
        asymptote = 1.0 / (1.0 - 0.5)
        assert tracker.get_recency("a") == pytest.approx(asymptote, rel=0.01)
