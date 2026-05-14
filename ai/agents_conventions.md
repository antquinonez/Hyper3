# Subsystem-Specific Conventions

Extracted from [AGENTS.md](../AGENTS.md). Read this when working on specific subsystems (belief, multiway, evolution, community detection, etc.).

## Conventions

### Rule `edge_label` convention
All rules that accept an `edge_label` parameter use `None` as the default, meaning "match all edges." Passing a specific string filters to only edges with that label. Do not use empty string `""` as a filter — it matches only unlabeled edges. The guard pattern is `if self._edge_label and e.label != self._edge_label: continue`, which is falsy for `None`.

### `reason()` uses all graph nodes for pattern matching
`reason()` passes all graph node IDs (not just seed concepts) as active nodes to the multiway expansion engine. This allows rules like `TransitiveRule` to find chains through intermediate nodes that are not part of the seed set. Seeds determine which nodes trigger the expansion; all nodes participate in pattern matching.

### Multi-hop chaining requires `new_label` to match `edge_label`
By default, `TransitiveRule` labels inferred edges `"inferred"`. Since the rule only matches edges with the specified `edge_label`, inferred edges are invisible to subsequent depth levels. For multi-hop chaining, set `new_label` to the same value as `edge_label`: `TransitiveRule(edge_label="causes", new_label="causes")`.

### Born rule sampling is probabilistic
`sample()` samples from the probability distribution defined by `|amplitude|^2`. Tests asserting exact sampling results must either use statistical approaches (run N trials, check distribution) or create single-outcome states.

### Event log uses `"event_type"` key
`EventLog.record()` stores the event type under the key `"event_type"`, not `"type"`.

### `correlate()` remaps labels to IDs

The `HypergraphMemory.correlate()` method takes labels but internally remaps correlation dict keys from labels to node IDs before passing to `BeliefLayer.create_correlation()`. Tests where `node.id == node.label` mask this.

### `context` parameter in structural anomaly detection
`StructuralAnomalyDetector` detection methods accept a `context` dict that supplements structural analysis. Supported keys: `cyclic_structure` (bool/float), `high_centrality` (bool/float), `contradiction` (bool/float), `structural_anomaly` (bool/float), and `contradictory` (bool). Pass `True` for a 0.3 boost, or a float in [0,1] to set a floor.

### `reason()` auto-commits existing overlays
If `reason(use_overlay=True)` is called while an overlay already exists (from a prior `reason(auto_commit=False)`), the existing overlay is auto-committed before a new one is created. No uncommitted inferences are silently lost.

### `Outcome.amplitude` is `float | complex`
After unitary evolution, amplitudes can be complex numbers. Code that consumes amplitudes should use `abs()` for magnitude comparisons. `probability` property already uses `abs()`.

### `create_distribution()` context field is opt-in
`use_context_field` defaults to `True`. The distribution is evolved using spreading activation values and structural prominence, biasing toward well-connected nodes. Prior activation state is preserved (not overwritten) during context evolution. Pass `use_context_field=False` to apply the raw Born rule to the provided amplitudes without structural bias.

### `EquivalenceEngine` uses combined similarity
`find_equivalences()` combines data similarity (`node.matches()`) with structural similarity (Jaccard overlap of neighborhoods). If data similarity meets the threshold, it's returned directly. Otherwise, a weighted combination (40% data + 60% structural) is used, taking the max with pure data similarity. Blocking is data-type-only (not edge labels) to avoid over-splitting. Nodes with empty neighborhoods get structural similarity 0.0 (no evidence of equivalence), not 1.0.

### `sample_with_profile` records effectiveness outcomes
`sample_with_profile()` calls `record_profile_outcome(profile, success)` automatically: `True` when a valid profile produces a sampling result, `False` when the profile is not found or sample returns None. Do not double-record outcomes in calling code.

### Prefetch API uses concept labels
`HypergraphMemory.enable_prefetch()`, `record_access(concept)`, `predict_next_access(concept)`, and `prefetch_neighbors(concept)` all take concept labels (not node IDs). Internally they map to the `"store:<label>"` key format used by the cache. The `cache` property exposes the raw `LazyCache` for direct access if needed.

### `select_optimal_frame_learned` uses shifted Thompson sampling
Frame selection shifts complexity by +1.0 to avoid zero-base issues, then applies Thompson sampling: `score = (complexity + 1.0) * (1.0 - bonus * 0.6)`. Frames with no recorded outcomes are not eligible for the bonus. The bonus is sampled from `Beta(successes+1, failures+1)`.

### Belief revision uses a negation map
`ContradictionResolver` has a built-in `NEGATION_MAP` with pairs like `supports`/`opposes`, `causes`/`prevents`, `enables`/`blocks`. Custom negation pairs can be added via the `custom_negations` constructor parameter. Two edges between the same nodes with negated labels are flagged as contradictions.

### Subsystem lazy initialization
The new subsystems (backward chain, Hebbian, uncertainty, structural match, belief revision, abstraction, community detection, graph diff) are lazily initialized on first use. They can be accessed via properties (e.g., `mem.hebbian`, `mem.backward_chain`) after first use. Direct constructor access is available for testing individual engines.

### Hebbian learning requires activation state
`hebbian_reinforce()` uses the current `SpreadingActivation` state to find co-activated node pairs. Call `stimulate()` + `spread_activation()` before `hebbian_reinforce()` to have non-trivial results. Without prior activation, the result will be empty.

### Community detection is non-deterministic
Label propagation uses random tie-breaking. Even with a fixed `seed`, results can vary across process invocations because the algorithm iterates over `graph.nodes` (dict-order-dependent) before shuffling. Setting `PYTHONHASHSEED=0` reduces but does not eliminate variability -- community IDs, counts, and modularity may still differ. The `connected_components` method is deterministic and unaffected. For showcase READMEs, describe community results as ranges or typical outcomes rather than exact numbers, and add a non-determinism note. For tests, assert on structural properties (community count range, modularity sign) rather than exact community assignments. Unweighted `detect_label_propagation` with `weighted_fallback=True` (default) automatically retries with weighted propagation if modularity is negative, returning whichever result has higher modularity.

### `exhaustive` flag disables multiway state bounding
`reason(exhaustive=True)` sets the internal `max_total_states` cap to 10M, effectively removing the bounding constraint. This ensures all applicable rules are explored at every depth level. Use for small graphs where completeness matters; avoid on large graphs.

### `multi_edge_count` in stats
`MemoryStats.multi_edge_count` reports the number of true hyperedges (edges where `len(source_ids) > 1` or `len(target_ids) > 1`). Pairwise edges (singleton source and target) are excluded.

### Graph diff captures are point-in-time
`GraphDiffer.capture()` snapshots the full node/edge state. Diffs are computed against these snapshots, not against the live graph. Multiple versions can be captured and compared pairwise.

### Feedback-driven evolution adapts to trends
`evolve_with_feedback()` checks the fitness trend from `OperationFeedback`. On declining trends, it intensifies decay (1.5x) and pruning (0.75x threshold), reinforces top-3 positively-reinforced nodes, and force-prunes suppressed nodes. On stable/improving trends, it uses standard parameters. `evolve_with_feedback()` returns `EvolveResult` with `reinforced` and `suppressed` counts.

### Validated metamorphosis requires a GraphDiffer
`execute_tuning_validated()` captures a pre-version, executes the metamorphosis plan, then compares fitness. If fitness degrades below `fitness_tolerance`, it rolls back to the pre-version. Without a `GraphDiffer` wired to the meta layer, it falls back to unvalidated execution. Call `capture_version()` first to auto-wire the differ.

### Cross-operation feedback identifies correlated nodes
`feedback_summary()` (delegates to `OperationFeedback.cross_operation_summary()`) computes aggregate health across sampling/retrieval/inference/evolution operations and identifies nodes that appear in signals across multiple operation types, reporting their positive rate and signal type distribution.

### Bias profile reveals reasoning tendencies
`compute_bias_profile()` returns a dict with `reasoning_style` (focused/exploratory/balanced/unknown), `bias_score`, `dominant_rules`, `underused_rules`, `position_trajectory` (exploring/exploiting/stable), and `average_effectiveness`. Requires rule effectiveness data from prior reasoning sessions; returns early with "unknown" style when no data exists.

### Causal merge insights capture unique contributions
When `StateConvergenceEngine` merges convergent multiway states, it computes `MergeInsight` for each merge partner listing nodes and edges unique to that state. These insights are attached to the `ConvergenceRecord.insights` list, preserving provenance of what each branch contributed before merging.

### `describe()` for graph summary
`mem.describe()` returns `GraphDescription` with node type distribution, edge label distribution, degree statistics (min/max/mean/median), isolated node count, component count, and density.

### `pagerank()` for PageRank centrality
`mem.pagerank(alpha=0.85, top_k=10)` computes PageRank. Uses raw edge weights as transition probabilities (not inverted — PageRank treats higher weight as stronger endorsement). Supports `weighted` flag and `top_k`.

### `top_k` on centrality methods
`degree_centrality(top_k=10)` and `betweenness_centrality(top_k=10)` return only the top-N entries. `top_k=None` returns all (default, backward compatible). The standalone `top_k()` utility in `results.py` sorts any score dict.

### Bayesian belief updating
`BayesianLayer` performs proper Bayesian prior x likelihood -> posterior updating. `set_prior()` initializes a categorical prior, `update_belief()` applies likelihood to produce a posterior, `get_belief()` returns the current distribution. `map_estimate()` returns the most probable outcome. `bayes_factor()` computes the Bayes factor between two hypotheses. `credible_set()` returns outcomes within a probability mass threshold. `reset_belief()` restores the prior.

### N-ary hyperedge creation via `relate_hyperedge()`
`mem.relate_hyperedge(sources={"a", "b"}, targets={"c", "d"}, label="joint")` creates true n-ary edges. Unlike `relate()` which creates pairwise (1:1) edges, this connects multiple sources to multiple targets in a single hyperedge. Source and target sets must be non-empty; weight must be positive (> 0). All source and target concepts must already exist as nodes (raises `NodeNotFoundError` otherwise).

### Hyperedge querying via `query_hyperedges()`
`mem.query_hyperedges(min_source_cardinality=2, containing="gene_a")` filters edges by cardinality and node membership. Returns raw `Hyperedge` objects (which use node IDs internally). Use `min_source_cardinality` and `min_target_cardinality` to find true n-ary edges.

### `hyperedge_neighbors()` for co-participation queries
`mem.hyperedge_neighbors("concept")` returns a dict mapping neighbor concept labels to lists of shared hyperedges. This is the n-ary counterpart to `neighbors()`, showing which concepts co-occur in the same hyperedges.

### Native hypergraph algorithms
All graph algorithms in `kernel.py` now use hypergraph-native implementations instead of pairwise NetworkX decomposition:
- `connected_components()` uses union-find on shared hyperedges. Accepts `s` parameter for s-connected components (minimum vertex overlap threshold).
- `shortest_path()` uses Dijkstra/BFS treating hyperedges as single hops. An edge {A,B}->{C,D} lets A and B both reach C and D in one step.
- `betweenness_centrality()` uses hypergraph-native s-path enumeration. Accepts `max_samples` for approximate computation.
- `has_cycle()` and `detect_cycles()` use native DFS on outgoing edges without NetworkX.
- `pagerank()` uses the incidence-based transition matrix `P = D_v^{-1} H W D_e^{-1} H^T`. Degrades to standard PageRank on pairwise graphs.
- All algorithms degrade gracefully: when all edges are pairwise, results match standard graph algorithms.

### `s_persistence()` for multi-resolution structure
`mem.s_persistence(max_s=5)` computes s-connected components for s=1,2,...,max_s. Components split as s increases, revealing multi-resolution hypergraph structure. Returns list of dicts with `s`, `components`, `num_components`, `largest_component_size`.

### Hyperedge diffusion modes
`mem.spread_hyperedge("concept", mode="and")` supports four gate modes for n-ary edge activation:
- `"linear"`: standard weighted propagation through all targets.
- `"and"`: activation flows only if ALL source nodes of the hyperedge are activated.
- `"or"`: activation flows if ANY source node is activated.
- `"majority"`: activation flows if >50% of source nodes are activated.

### Spectral embedding from hypergraph Laplacian
`mem.spectral_embedding(dimensions=8)` computes spectral embeddings from the bottom-k eigenvectors of the normalized hypergraph Laplacian `L = I - D_v^{-1/2} H W D_e^{-1} H^T D_v^{-1/2}`. Returns dict mapping concept labels to embedding vectors.

### Hyperedge similarity search
`mem.hyperedge_similarity("concept", metric="jaccard")` finds hyperedges similar to those containing a concept by node-set overlap. Metrics: `jaccard`, `sorensen_dice`, `overlap_coefficient`.

### `betweenness_centrality(max_samples=N)` uses sampled normalization
Without `max_samples`, betweenness is normalized by `1/((n-1)(n-2))` for n >= 3, producing values in [0, 1]. With `max_samples`, normalization is `1/max_samples` and values are raw pairwise dependency counts that can exceed 1.0. Tests on sampled betweenness should not assert `<= 1.0`.

### `detect_cycles(max_cycles=N)` is a soft limit
The DFS checks `len(cycles) >= max_cycles` at function entry, not at the point of cycle discovery. The algorithm may produce more than `N` cycles. Tests should assert `len(limited) < len(all_cycles)`, not `len(limited) == N`.

### `find_paths` returns all paths, not just shortest
`find_paths(source, target)` finds every path from source to target. A graph with both a direct edge and an indirect chain returns both paths. The exact count depends on graph structure. Use `max_paths=1` when only one path is expected.

### `ObserverSlice.narrow` depth counts expansion steps
`narrow("root", max_depth=1)` returns only the root node itself, not root + direct neighbors. `max_depth` limits how many expansion steps the traversal takes. For root + neighbors, use `max_depth=2`.

### `GraphMaintenanceEngine()` default merges identical-data neighbors
Nodes with matching `data` values that share a connecting edge will merge during `evolve()` even without an explicit `merge_threshold`. The default constructor enables merging. For tests that need to avoid merging, use `merge_threshold=1.0` (disabled).

### `hyperedge_similarity` with unknown metric defaults to jaccard
Passing an unrecognized metric string falls through to the `else` branch which computes `intersection / union` — identical to the jaccard formula. No error is raised.

## Common Pitfalls

- **Wrong Python**: The system Python is not the project Python. Always use `.venv/bin/python`.
- **Label vs ID**: Hypernodes have both `id` (auto-generated UUID hex) and `label` (human-readable). Most APIs take labels; internal engines use IDs.
- **`load()` resets thresholds**: `HypergraphMemory.load()` restores graph structure but constructor args (like `merge_threshold`) are set at construction time, not from the saved file. Tests must pass matching constructor args to the loading instance.
- **Fitness never drops below 0.9**: The architectural fitness formula in `SystemMonitor` is `1.0 - (prunes/(total+1)) * 0.1`, which stays above 0.9 even with 100% prunes. Tests should set `_state.architectural_fitness` directly instead of trying to lower it via evolution metrics.
- **Multiway expansion needs chains**: `TransitiveRule` only matches when there is a two-hop chain (A->B, B->C). Starting from a root node with no outgoing edges produces zero matches.
- **EquivalenceEngine structural similarity**: Two nodes with no edges get structural score 0.0 (no evidence of equivalence). Two nodes with no overlapping neighbors also get structural score 0.0. Data similarity alone can still exceed the threshold if all shared dict keys have matching values. Provide discriminative data (unique names, IDs) to prevent false merges.
- **ValidationEngine mutates then reverts**: `_run_simple()` applies rules to the graph, collects results, then removes newly added edges. It does NOT clone the graph. Do not call it from inside a running `reason()` call.
- **Belief state staleness is timing-dependent**: `decay_stale_states()` reduces amplitudes based on `time.time() - qs.created_at`. Tests with very short `coherence_time` values may see probabilistic collapse instead of amplitude reduction. Use `<=` comparisons, not strict `<`.
- **`_SimpleResultBase.get()` and `None` fields**: `.get("field", fallback)` returns the fallback when the field value is `None`, matching `dict.get()` semantics. For fields that may legitimately be `None` (e.g., `result.state_convergence`), use attribute access with explicit `if ci:` guards instead of `.get()`.
- **Shortcut-namespace recursion**: Top-level shortcuts that share a name with a mixin method (e.g., `prove`, `activate`, `introspect`) must call the mixin directly (`CognitiveMixin.prove(self, ...)`) rather than delegating through the namespace (`self.cognitive.prove(...)`). The namespace calls `self._mem.prove()` which would recurse back to the shortcut, causing infinite recursion.
- **Community detection self-loops**: `CommunityDetector` filters self-loops in `_build_neighbor_map`. Graphs with self-referential edges (a node connecting to itself) will have those edges excluded from community analysis to prevent `frozenset` collapse in modularity calculation.
