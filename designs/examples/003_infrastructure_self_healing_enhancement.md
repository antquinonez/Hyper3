# Enhancement: Infrastructure Self-Healing -- Temporal Reasoning

## Target File
`examples/showcase/infrastructure_self_healing/infrastructure_self_healing.py`

## Current State
Most complex showcase example (130+ nodes) with feedback loops, degradation/recovery cycles, bias profiling, metamorphosis validation, and multiway merge. Models infrastructure *structure* but not incident *timeline*.

## Enhancement
Add a new section modeling the degradation incident as temporal events:

### Section: Temporal Incident Timeline
Model the degradation and recovery as temporal events with Allen interval relations and causal chain detection.

**New APIs introduced:**
- `mem.add_temporal_event(label, start, end, **metadata)` -- register temporal event
- `mem.allen_relation(source, target)` -- compute Allen interval relation
- `mem.detect_temporal_causal_chains(min_chain_length)` -- auto-detect causal chains
- `mem.infer_temporal_constraints()` -- infer Allen constraints between all events
- `mem.check_temporal_constraint_consistency()` -- detect temporal contradictions
- `mem.list_temporal_events()` -- list all registered events
- `mem.temporal_query(concept, relation, max_gap)` -- query by temporal relation

**Narrative flow:**
1. Register 6-8 temporal events modeling the incident timeline:
   - healthy_baseline (0.0 - 10.0)
   - stale_config_push (10.0 - 10.5)
   - connection_pool_growth (11.0 - 14.0)
   - latency_spike (12.0 - 16.0)
   - user_timeouts (13.0 - 17.0)
   - alert_triggered (14.0 - 14.5)
   - feedback_recovery (16.0 - 20.0)
   - restored_baseline (19.0 - 25.0)

2. Compute Allen relations between key event pairs:
   - stale_config_push -> connection_pool_growth (before/meets)
   - latency_spike -> user_timeouts (overlaps)
   - feedback_recovery -> restored_baseline (meets/before)

3. Auto-detect causal chains: stale_config_push -> connection_pool_growth -> latency_spike -> user_timeouts

4. Infer temporal constraints and check consistency

5. Query for events overlapping the peak incident window

## Dependencies
- `memory_temporal.py` -- TemporalMixin methods
- Existing infrastructure graph (unchanged)

## Validation
- Run: `.venv/bin/python examples/showcase/infrastructure_self_healing/infrastructure_self_healing.py`
- Verify temporal events are registered
- Verify Allen relations are correct
- Verify causal chain detection produces the expected chain
- Update README.md
