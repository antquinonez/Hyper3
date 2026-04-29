import time

from hyper3.memory import HypergraphMemory
from hyper3.kernel import Hyperedge


def _make_mem():
    mem = HypergraphMemory(evolve_interval=0)
    mem.store("x")
    mem.store("y")
    mem.store("z")
    return mem


class TestDecayStaleStates:

    def test_no_stale_states(self):
        mem = _make_mem()
        qs = mem.create_distribution(["x", "y", "z"])
        result = mem._belief.decay_stale_states()
        assert result == []

    def test_stale_state_decayed(self):
        mem = _make_mem()
        qs = mem.create_distribution(["x", "y", "z"])
        qs.coherence_time = 0.0
        qs.base_coherence_time = 0.0
        time.sleep(0.01)
        result = mem._belief.decay_stale_states()
        assert len(result) == 1
        assert qs.resolved is True

    def test_max_age_filter(self):
        mem = _make_mem()
        qs = mem.create_distribution(["x", "y", "z"])
        qs.coherence_time = 0.0
        qs.base_coherence_time = 0.0
        time.sleep(0.01)
        result = mem._belief.decay_stale_states(max_age=3600.0)
        assert result == []

    def test_non_stale_not_decayed(self):
        mem = _make_mem()
        qs = mem.create_distribution(["x", "y", "z"])
        qs.coherence_time = 99999.0
        qs.base_coherence_time = 99999.0
        result = mem._belief.decay_stale_states()
        assert result == []

    def test_already_resolved_skipped(self):
        mem = _make_mem()
        qs = mem.create_distribution(["x", "y", "z"])
        qs.resolved = True
        result = mem._belief.decay_stale_states()
        assert result == []

    def test_amplitudes_reduced(self):
        mem = _make_mem()
        qs = mem.create_distribution(["x", "y", "z"])
        amps_before = [abs(i.amplitude) for i in qs.outcomes]
        qs.coherence_time = 0.001
        qs.base_coherence_time = 0.001
        qs.created_at = time.time() - 10.0
        mem._belief.decay_stale_states()
        amps_after = [abs(i.amplitude) for i in qs.outcomes]
        assert qs.resolved or sum(amps_after) < sum(amps_before)


class TestCleanupResolved:

    def test_no_resolved(self):
        mem = _make_mem()
        mem.create_distribution(["x", "y"])
        result = mem._belief.cleanup_resolved(threshold_age=0.0)
        assert result == 0

    def test_old_resolved_removed(self):
        mem = _make_mem()
        qs = mem.create_distribution(["x", "y"])
        qs.resolved = True
        qs.created_at = time.time() - 7200
        result = mem._belief.cleanup_resolved(threshold_age=3600.0)
        assert result == 1
        assert mem._belief.get_state(qs.id) is None

    def test_recent_resolved_kept(self):
        mem = _make_mem()
        qs = mem.create_distribution(["x", "y"])
        qs.resolved = True
        result = mem._belief.cleanup_resolved(threshold_age=3600.0)
        assert result == 0
        assert mem._belief.get_state(qs.id) is not None

    def test_active_not_removed(self):
        mem = _make_mem()
        qs = mem.create_distribution(["x", "y"])
        qs.created_at = time.time() - 7200
        result = mem._belief.cleanup_resolved(threshold_age=3600.0)
        assert result == 0
