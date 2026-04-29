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
        qs = mem.superpose(["x", "y", "z"])
        result = mem._quantum.decay_stale_states()
        assert result == []

    def test_decoherent_state_decayed(self):
        mem = _make_mem()
        qs = mem.superpose(["x", "y", "z"])
        qs.coherence_time = 0.0
        qs.base_coherence_time = 0.0
        time.sleep(0.01)
        result = mem._quantum.decay_stale_states()
        assert len(result) == 1
        assert qs.collapsed is True

    def test_max_age_filter(self):
        mem = _make_mem()
        qs = mem.superpose(["x", "y", "z"])
        qs.coherence_time = 0.0
        qs.base_coherence_time = 0.0
        time.sleep(0.01)
        result = mem._quantum.decay_stale_states(max_age=3600.0)
        assert result == []

    def test_non_decoherent_not_decayed(self):
        mem = _make_mem()
        qs = mem.superpose(["x", "y", "z"])
        qs.coherence_time = 99999.0
        qs.base_coherence_time = 99999.0
        result = mem._quantum.decay_stale_states()
        assert result == []

    def test_already_collapsed_skipped(self):
        mem = _make_mem()
        qs = mem.superpose(["x", "y", "z"])
        qs.collapsed = True
        result = mem._quantum.decay_stale_states()
        assert result == []

    def test_amplitudes_reduced(self):
        mem = _make_mem()
        qs = mem.superpose(["x", "y", "z"])
        amps_before = [abs(i.amplitude) for i in qs.interpretations]
        qs.coherence_time = 0.001
        qs.base_coherence_time = 0.001
        qs.created_at = time.time() - 10.0
        mem._quantum.decay_stale_states()
        amps_after = [abs(i.amplitude) for i in qs.interpretations]
        assert qs.collapsed or sum(amps_after) < sum(amps_before)


class TestCleanupCollapsed:

    def test_no_collapsed(self):
        mem = _make_mem()
        mem.superpose(["x", "y"])
        result = mem._quantum.cleanup_collapsed(threshold_age=0.0)
        assert result == 0

    def test_old_collapsed_removed(self):
        mem = _make_mem()
        qs = mem.superpose(["x", "y"])
        qs.collapsed = True
        qs.created_at = time.time() - 7200
        result = mem._quantum.cleanup_collapsed(threshold_age=3600.0)
        assert result == 1
        assert mem._quantum.get_state(qs.id) is None

    def test_recent_collapsed_kept(self):
        mem = _make_mem()
        qs = mem.superpose(["x", "y"])
        qs.collapsed = True
        result = mem._quantum.cleanup_collapsed(threshold_age=3600.0)
        assert result == 0
        assert mem._quantum.get_state(qs.id) is not None

    def test_active_not_removed(self):
        mem = _make_mem()
        qs = mem.superpose(["x", "y"])
        qs.created_at = time.time() - 7200
        result = mem._quantum.cleanup_collapsed(threshold_age=3600.0)
        assert result == 0
