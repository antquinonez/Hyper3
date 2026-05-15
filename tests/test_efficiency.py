from __future__ import annotations

import time

import pytest

from hyper3.efficiency import (
    CacheEfficiency,
    EfficiencyReport,
    EfficiencyTracker,
    OperationStats,
    OperationType,
)


class TestEfficiencyTrackerConstruction:
    def test_default_construction(self):
        tracker = EfficiencyTracker()
        report = tracker.get_report()
        assert report.total_operations == 0

    def test_custom_parameters(self):
        tracker = EfficiencyTracker(
            max_records_per_type=500,
            degradation_window=20,
            degradation_threshold=3.0,
        )
        assert tracker._max_records == 500
        assert tracker._degradation_window == 20


class TestEfficiencyRecord:
    def test_record_stores_operation(self):
        tracker = EfficiencyTracker()
        tracker.record(OperationType.TRAVERSAL, 10.5)
        stats = tracker.get_stats(OperationType.TRAVERSAL)
        assert stats.count == 1
        assert stats.avg_duration_ms == pytest.approx(10.5)

    def test_record_respects_max_records(self):
        tracker = EfficiencyTracker(max_records_per_type=5)
        for i in range(10):
            tracker.record(OperationType.SEARCH, float(i))
        stats = tracker.get_stats(OperationType.SEARCH)
        assert stats.count == 5

    def test_record_tracks_success(self):
        tracker = EfficiencyTracker()
        tracker.record(OperationType.REASONING, 100.0, success=True)
        tracker.record(OperationType.REASONING, 200.0, success=False)
        stats = tracker.get_stats(OperationType.REASONING)
        assert stats.count == 2
        assert stats.success_count == 1

    def test_record_with_metadata(self):
        tracker = EfficiencyTracker()
        tracker.record(OperationType.EVOLUTION, 50.0, metadata={"nodes": 100})
        records = tracker._records[OperationType.EVOLUTION]
        assert records[0].metadata["nodes"] == 100


class TestEfficiencyStats:
    def test_empty_stats(self):
        tracker = EfficiencyTracker()
        stats = tracker.get_stats(OperationType.ACTIVATION)
        assert stats.count == 0
        assert stats.avg_duration_ms == 0.0

    def test_single_record_all_percentiles_equal(self):
        tracker = EfficiencyTracker()
        tracker.record(OperationType.CACHE_ACCESS, 42.0)
        stats = tracker.get_stats(OperationType.CACHE_ACCESS)
        assert stats.p50_duration_ms == pytest.approx(42.0)
        assert stats.p95_duration_ms == pytest.approx(42.0)
        assert stats.p99_duration_ms == pytest.approx(42.0)
        assert stats.min_duration_ms == pytest.approx(42.0)
        assert stats.max_duration_ms == pytest.approx(42.0)

    def test_multiple_records_correct_stats(self):
        tracker = EfficiencyTracker()
        for d in [10.0, 20.0, 30.0, 40.0, 50.0]:
            tracker.record(OperationType.TRAVERSAL, d)
        stats = tracker.get_stats(OperationType.TRAVERSAL)
        assert stats.count == 5
        assert stats.avg_duration_ms == pytest.approx(30.0)
        assert stats.min_duration_ms == pytest.approx(10.0)
        assert stats.max_duration_ms == pytest.approx(50.0)
        assert stats.p50_duration_ms == pytest.approx(30.0)


class TestEfficiencyCacheTracking:
    def test_cache_hit_increments(self):
        tracker = EfficiencyTracker()
        tracker.record_cache_hit()
        tracker.record_cache_hit()
        eff = tracker.get_cache_efficiency()
        assert eff.hits == 2
        assert eff.misses == 0
        assert eff.hit_ratio == 1.0

    def test_cache_miss_increments(self):
        tracker = EfficiencyTracker()
        tracker.record_cache_miss()
        eff = tracker.get_cache_efficiency()
        assert eff.misses == 1
        assert eff.hit_ratio == 0.0

    def test_cache_hit_ratio(self):
        tracker = EfficiencyTracker()
        for _ in range(7):
            tracker.record_cache_hit()
        for _ in range(3):
            tracker.record_cache_miss()
        eff = tracker.get_cache_efficiency()
        assert eff.hit_ratio == pytest.approx(0.7)

    def test_cache_eviction_tracking(self):
        tracker = EfficiencyTracker()
        tracker.record_cache_eviction()
        tracker.record_cache_eviction()
        eff = tracker.get_cache_efficiency()
        assert eff.evictions == 2

    def test_empty_cache_efficiency(self):
        tracker = EfficiencyTracker()
        eff = tracker.get_cache_efficiency()
        assert eff.hit_ratio == 0.0
        assert eff.hits == 0


class TestEfficiencyDegradation:
    def test_no_degradation_initially(self):
        tracker = EfficiencyTracker()
        assert tracker.check_degradation() == []

    def test_detects_degradation(self):
        tracker = EfficiencyTracker(degradation_window=3, degradation_threshold=1.5)
        for _ in range(3):
            tracker.record(OperationType.REASONING, 10.0)
        for _ in range(3):
            tracker.record(OperationType.REASONING, 100.0)
        alerts = tracker.check_degradation()
        assert len(alerts) == 1
        assert "reasoning" in alerts[0]

    def test_no_alert_when_stable(self):
        tracker = EfficiencyTracker(degradation_window=3)
        for _ in range(3):
            tracker.record(OperationType.TRAVERSAL, 10.0)
        for _ in range(3):
            tracker.record(OperationType.TRAVERSAL, 10.0)
        assert tracker.check_degradation() == []

    def test_insufficient_data_no_alert(self):
        tracker = EfficiencyTracker(degradation_window=50)
        tracker.record(OperationType.TRAVERSAL, 10.0)
        assert tracker.check_degradation() == []


class TestEfficiencyReport:
    def test_empty_report(self):
        tracker = EfficiencyTracker()
        report = tracker.get_report()
        assert report.total_operations == 0
        assert report.overall_avg_duration_ms == 0.0
        assert report.slowest_operation == ""
        assert not report.degradation_detected

    def test_report_with_operations(self):
        tracker = EfficiencyTracker()
        tracker.record(OperationType.TRAVERSAL, 10.0)
        tracker.record(OperationType.REASONING, 50.0)
        report = tracker.get_report()
        assert report.total_operations == 2
        assert report.slowest_operation == "reasoning"
        assert len(report.operation_stats) == 2

    def test_report_includes_degradation(self):
        tracker = EfficiencyTracker(degradation_window=2, degradation_threshold=1.5)
        tracker.record(OperationType.EVOLUTION, 10.0)
        tracker.record(OperationType.EVOLUTION, 10.0)
        tracker.record(OperationType.EVOLUTION, 100.0)
        tracker.record(OperationType.EVOLUTION, 100.0)
        report = tracker.get_report()
        assert report.degradation_detected
        assert len(report.degradation_details) == 1

    def test_report_includes_cache_efficiency(self):
        tracker = EfficiencyTracker()
        tracker.record_cache_hit()
        tracker.record_cache_miss()
        report = tracker.get_report()
        assert report.cache_efficiency.hits == 1
        assert report.cache_efficiency.misses == 1


class TestEfficiencyContextManager:
    def test_track_records_duration_on_success(self):
        tracker = EfficiencyTracker()
        with tracker.track(OperationType.TRAVERSAL):
            time.sleep(0.001)
        stats = tracker.get_stats(OperationType.TRAVERSAL)
        assert stats.count == 1
        assert stats.avg_duration_ms > 0.0
        assert stats.success_count == 1

    def test_track_records_failure(self):
        tracker = EfficiencyTracker()
        with pytest.raises(ValueError), tracker.track(OperationType.REASONING):
            raise ValueError("test")
        stats = tracker.get_stats(OperationType.REASONING)
        assert stats.count == 1
        assert stats.success_count == 0

    def test_track_with_metadata(self):
        tracker = EfficiencyTracker()
        with tracker.track(OperationType.SEARCH, metadata={"query": "test"}):
            pass
        records = tracker._records[OperationType.SEARCH]
        assert records[0].metadata["query"] == "test"


class TestEfficiencyReset:
    def test_reset_clears_everything(self):
        tracker = EfficiencyTracker()
        tracker.record(OperationType.TRAVERSAL, 10.0)
        tracker.record_cache_hit()
        tracker.reset()
        assert tracker.get_report().total_operations == 0
        assert tracker.get_cache_efficiency().hits == 0


class TestEfficiencySerialization:
    def test_to_dict_round_trip(self):
        tracker = EfficiencyTracker(
            max_records_per_type=500,
            degradation_window=25,
            degradation_threshold=3.0,
        )
        tracker.record_cache_hit()
        tracker.record_cache_miss()
        data = tracker.to_dict()
        restored = EfficiencyTracker.from_dict(data)
        assert restored._max_records == 500
        assert restored._degradation_window == 25
        assert restored._degradation_threshold == 3.0
        assert restored._cache_hits == 1
        assert restored._cache_misses == 1

    def test_from_dict_defaults(self):
        restored = EfficiencyTracker.from_dict({})
        assert restored._max_records == 1000
