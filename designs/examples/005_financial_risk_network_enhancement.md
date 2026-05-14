# Enhancement: Financial Risk Network -- Contagion Flow Analysis

## Target File
`examples/showcase/domain/financial_risk_network/financial_risk_network.py`

## Implementation Status
- **Contagion Flow (max_flow, min_cut global, shortest_path)**: DONE (Section 8)
- **Self-Evolution (`evolve_with_feedback()`)**: DONE (Section 8)
- **`min_cut_st(source, target)` (source-target specific cut)**: MISSING
- **Value of remaining work**: LOW -- adding `min_cut_st` is a 3-line call. The global min_cut already identifies the weakest partition. Source-target cut is a minor refinement.

## Current State
130+ node financial network with community detection, Hebbian learning, belief distributions, multi-frame analysis, and hierarchical abstraction. Uses clustering and centrality but never answers "how much risk can flow from A to B?"

## Enhancement
Add contagion flow analysis using max-flow, min-cut, and shortest path:

### Section: Contagion Flow Analysis
**New APIs introduced:**
- `mem.analyze.max_flow(source, target)` -- maximum contagion flow between counterparties
- `mem.analyze.min_cut_global()` -- weakest partition in the system
- `mem.analyze.min_cut_st(source, target)` -- minimum cut between specific nodes
- `mem.analyze.shortest_path(source, target, weighted=True)` -- most likely contagion route

**Narrative flow:**
1. Compute max contagion flow from a distressed counterparty (archegos_capital) to key exposed banks
2. Show the flow paths and bottleneck edges
3. Compute global minimum cut -- the weakest partition point
4. Compute shortest risk-propagation path using weighted edges (high weight = low cost = preferred route)
5. Discuss implications: which institutions are most exposed, where to add firebreaks

### Section: Self-Evolution for Risk Graph Maintenance
Add evolution to maintain the risk graph over time.

**New APIs introduced:**
- `mem.evolve_with_feedback()` -- feedback-driven evolution

**Narrative flow:**
1. Run evolve_with_feedback() on the risk graph
2. Show which exposures decayed (stale positions), which were reinforced (active trading)
3. Show how evolution maintains graph quality by removing stale relationships

## Dependencies
- `memory_analytics.py` -- max_flow, min_cut_global, min_cut_st, shortest_path
- `memory_core.py` -- evolve_with_feedback

## Validation
- Run: `.venv/bin/python examples/showcase/domain/financial_risk_network/financial_risk_network.py`
- Verify max_flow returns meaningful flow values
- Verify min_cut partitions the network
- Verify shortest path follows high-weight edges
- Update README.md
