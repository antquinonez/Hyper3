# Full System Snapshot and Restore

> **Cross-Subsystem State Serialization and Round-Trip Verification on a 12-Node Graph**

## 1. The Approach

Analysis sessions are stateful — belief distributions accumulate over multiple `create_distribution` and `sample` calls, multiway expansion builds branching state trees, provenance records track every inferred edge back to its source rules, retrieval feedback adjusts future recall rankings, rule analytics measure which rules produce useful edges, and cache entries accelerate repeated lookups. After a session processing thousands of concepts, all this subsystem state represents significant computational investment.

Without snapshotting, restarting the process loses everything. The snapshot subsystem serializes every subsystem into a single immutable `SystemSnapshot` object, enabling checkpoint-restore workflows, session transfer between machines, and audit-compliant state archival. The graph structure is saved separately (via `save/load`), while the snapshot captures the subsystem layer above the graph. This separation means you can restore subsystem state onto a different graph topology if needed — for example, restoring analytics and provenance onto a pruned version of the graph.

## 2. Key Concepts

| Term | Plain English Meaning |
|------|----------------------|
| **SystemSnapshot** | Immutable cross-subsystem state container with 20+ fields |
| **capture_snapshot** | Module-level function that reads state from all subsystems |
| **restore_snapshot** | Rebuilds subsystems from a snapshot, returning multiway/clustering/analytics engines |
| **save_state / load_state** | JSON file I/O for snapshots |
| **to_dict / from_dict** | Serialization round-trip enabling custom storage backends |
| **BeliefLayer state** | Quantum amplitude distributions and correlation records |
| **MultiwayEngine state** | Expansion graph with branch states and leaf tracking |
| **ProvenanceTracker state** | Edge-to-rule-to-seed inference chains |
| **RetrievalEngine state** | Feedback signals and relevance rankings |

## 3. Quick Start

```bash
.venv/bin/python examples/showcase/workflow/system_snapshot/system_snapshot.py
```

```
SECTION 1: BUILD AND ENRICH THE KNOWLEDGE GRAPH
reasoning: edges_produced=6, states_created=7
graph: nodes=12, edges=18

SECTION 2: CAPTURE FULL SYSTEM SNAPSHOT
snapshot captured:
  belief states: 1
  multiway states: 7
  provenance records: 6
  cache items: 12

SECTION 3: SAVE SNAPSHOT TO DISK
saved graph to: graph.json (23484 bytes)
saved snapshot to: snapshot.json (46198 bytes, 45.1 KB)

SECTION 4: RESTORE INTO FRESH INSTANCE
nodes match: True
edges match: True
```

File sizes vary by OS tempfile location. The snapshot JSON is typically 44-46 KB for a 12-node enriched graph.

## 4. Analysis Pipeline

**Section 1 — Build and enrich the knowledge graph:** 12 quantum computing research concepts are stored and connected with 12 `influences` edges. A `TransitiveRule` on the `influences` label is registered at construction, and `reason()` produces 6 inferred edges via multiway expansion (7 states created). A belief distribution is created over three concepts (`quantum_computing`, `machine_learning`, `cryptography`). Two nodes are stimulated with activation energy and activation is spread for 2 iterations. Retrieval feedback is recorded for `machine_learning` and `cryptography`. The graph ends at 12 nodes, 18 edges (12 base + 6 inferred). Why this matters: the snapshot must capture the state of every subsystem that contributed to this enriched graph — not just the nodes and edges, but the belief amplitudes, multiway expansion tree, provenance chains, retrieval rankings, and cache entries. Missing any one of these produces a restored system that silently disagrees with the original.

**Section 2 — Capture full system snapshot:** `capture_snapshot()` is called with all 10 subsystem references (belief, multiway_engine, state_clustering, rule_analytics, provenance, retrieval, perspective, meta, cache, feedback). The result is an immutable `SystemSnapshot` containing: 1 belief state, 7 multiway states, 6 provenance records, 6 retrieval feedback entries, 0 frame outcomes, 12 cache items, and 0 feedback signals. Why this matters: the snapshot is a single object that can be inspected, serialized, or transmitted without reference to the live system. Its immutability guarantees that downstream consumers see a consistent view — no partial updates, no race conditions, no "snapshot captured mid-mutation" anomalies.

**Section 3 — Save snapshot to disk:** `mem.save()` writes the graph structure to `graph.json` (~23 KB). `mem.save(path, full=True)` writes the full system state (graph + subsystems) to `snapshot.json` (~45 KB). These are two separate files because the graph and subsystems have different serialization formats and different lifecycles. Why this matters: the graph JSON contains nodes, edges, weights, labels, and data payloads — the structural substrate. The snapshot JSON contains belief amplitudes, multiway states, provenance chains, retrieval feedback, analytics counters, cache entries, and monitor readings — the computational layer. Separating them allows restoring the graph alone (for structural analysis) or the subsystem state alone (for analytics audit) without the other.

**Section 4 — Restore into fresh instance:** A new `HypergraphMemory` is created with the same rules configuration. `mem2.load(graph_path)` restores the graph structure. `mem2.load_state(snapshot_path)` restores the subsystem state. The restored graph matches: 12 nodes, 18 edges. Why this matters: the fresh instance starts from zero — no nodes, no edges, no subsystem state. The two-step restore (graph first, then snapshot) rebuilds the complete session. The rules configuration must match the original because rule objects are not serialized — they are code, not data. A mismatch here means reasoning after restore may behave differently.

**Section 5 — Verify restored state:** All 12 concept labels are present in the restored graph. Density matches (0.1364 vs 0.1364). Confidence score for `quantum_computing` matches (1.0000 vs 1.0000). Average confidence across all nodes matches (3.0854 vs 3.0854). Why this matters: confidence scores depend on edge weights, connectivity, and provenance depth — all of which must be restored correctly for the numbers to match. A confidence mismatch would indicate that some subsystem state (edge weights, provenance chains, or activation values) was not restored faithfully.

**Section 6 — Serialization round-trip:** `snapshot.to_dict()` produces a dict with 32 keys. `SystemSnapshot.from_dict(data_dict)` reconstructs the snapshot. Belief states (1), multiway states (7), and provenance records (6) counts are preserved through the round-trip. Why this matters: `to_dict`/`from_dict` enables custom storage backends — you can write the dict to a database, send it over a network, or store it in an object store. The round-trip guarantee means no information is lost through JSON serialization, even for complex nested structures like multiway expansion trees and belief amplitude arrays.

## 5. Key Metrics

| Metric | Value |
|--------|-------|
| Nodes | 12 |
| Base edges | 12 |
| Inferred edges (reasoning) | 6 |
| Total edges | 18 |
| Multiway states | 7 |
| Belief distributions | 1 |
| Provenance records | 6 |
| Retrieval feedback entries | 6 |
| Cache items | 12 |
| Graph JSON size | ~23 KB |
| Snapshot JSON size | ~45 KB |
| Snapshot dict keys | 32 |

## 6. What Makes This Different

**Cross-subsystem completeness** means the snapshot captures state from every subsystem in a single object: belief amplitudes and correlations, multiway expansion states and leaves, provenance edge-to-rule chains, retrieval feedback and rankings, rule analytics counters, cache entries and TTL, perspective frame outcomes, system monitor readings, and feedback signals. Restoring the snapshot rebuilds all of these into operational engines that produce identical results to the original session.

**Round-trip fidelity** through `to_dict`/`from_dict` ensures that no information is lost through JSON serialization. The 32-key dict preserves complex nested structures — multiway expansion trees with parent-child references, belief amplitude arrays with complex components, and provenance chains linking edges to rules to seed concepts. The round-trip guarantee is verified by comparing field counts before and after serialization.

**Separate graph/snapshot** serialization reflects the architectural separation between the structural substrate (nodes and edges) and the computational layer (belief, reasoning, analytics). The graph is restored via `save/load` using the graph's own serialization format. The snapshot is restored via `save_state/load_state` using the subsystem serialization format. This separation means you can restore subsystem state onto a different graph topology if needed — for example, restoring analytics and provenance onto a pruned version of the graph for a focused analysis session.

## 7. Code Implementation

**1. Build and enrich the graph:**

```python
from hyper3 import HypergraphMemory, TransitiveRule

mem = HypergraphMemory(evolve_interval=0, rules=[
    TransitiveRule(edge_label="influences", new_label="indirect_influence"),
])

for concept in ["quantum_computing", "machine_learning", "cryptography", ...]:
    mem.add(concept, data={"type": "concept"})

mem.link("quantum_computing", "machine_learning", label="influences", weight=3.0)

result = mem.reason(seeds={"quantum_computing"}, depth=3)
mem.belief.create(["quantum_computing", "machine_learning", "cryptography"])
```

**2. Capture a full system snapshot:**

```python
from hyper3.snapshot import capture_snapshot

snapshot = capture_snapshot(
    belief=mem._belief,
    multiway_engine=mem._multiway_engine,
    provenance=mem._provenance,
    retrieval=mem._retrieval,
    cache=mem._cache,
    ...
)
print(f"belief states: {len(snapshot.belief_states)}")
```

**3. Save to disk and restore:**

```python
mem.save("graph.json")
mem.save("snapshot.json", full=True)

mem2 = HypergraphMemory(evolve_interval=0, rules=[...])
mem2.load("graph.json")
mem2.load("snapshot.json")
```

**4. Serialization round-trip via to_dict/from_dict:**

```python
from hyper3.snapshot import SystemSnapshot

data_dict = snapshot.to_dict()
restored = SystemSnapshot.from_dict(data_dict)

assert len(restored.belief_states) == len(snapshot.belief_states)
assert len(restored.multiway_states) == len(snapshot.multiway_states)
```

## 8. Real-World Gap

This showcase snapshots a 12-node enriched graph. Real-world adoption involves additional considerations:

- **Large multiway states** — graphs with deep reasoning chains produce large multiway expansion trees. The snapshot serializes all states, which may produce multi-MB files for heavily reasoned graphs.
- **Cache TTL and wall-clock time** — cache entries store creation timestamps. Restoring on a different machine with a different clock means TTL-based expiry may fire at different times relative to the restoration point.
- **No incremental snapshots** — each `capture_snapshot()` is a full capture. For large states, incremental or differential snapshots would reduce storage and transfer costs.
- **Rule objects are not serialized** — rules are code (Python classes), not data. The restored instance must be constructed with the same rules list for reasoning behavior to match.
- **Private subsystem access** — `capture_snapshot()` requires references to internal subsystem objects (`mem._belief`, `mem._multiway_engine`, etc.). A future API may provide a public `mem.capture_snapshot()` method that collects these automatically.

## 9. Reference

| Method | Purpose |
|--------|---------|
| `mem.save(path)` | Serialize graph structure to JSON file |
| `mem.load(path)` | Restore graph structure from JSON file |
| `mem.save(path, full=True)` | Serialize full system state (graph + subsystems) to JSON file |
| `capture_snapshot(belief, multiway_engine, ...)` | Capture all subsystem state into a SystemSnapshot |
| `snapshot.to_dict()` | Convert snapshot to a JSON-serializable dict |
| `SystemSnapshot.from_dict(data)` | Reconstruct snapshot from a dict |
| `mem.describe()` | Return graph statistics (nodes, edges, density) |
| `mem.cognitive.confidence(concept)` | Compute confidence score for a concept |
| `mem.cognitive.all_confidences()` | Compute average confidence across all nodes |

| Related Example | Connection |
|----------------|------------|
| `graph_versioning` | Structural versioning of graph topology |
| `provenance_and_retraction` | Provenance records captured in the snapshot |
