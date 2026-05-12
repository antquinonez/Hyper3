# Hierarchical Abstraction and Multi-Level Analysis

> **Collapsing 20 Employees into Teams and Departments for Multi-Level Centrality Analysis**

## 1. The Approach

Real-world graphs have natural hierarchies: employees form teams, teams form departments, departments form divisions. Analyzing 20 individual employees produces different insights than analyzing 4 teams or 2 departments. At the employee level, you see collaboration patterns between individuals. At the team level, you see inter-team dependencies. At the department level, you see organizational structure. The right granularity depends on the question.

The AbstractionNavigator enables working at the right granularity: collapsing detail nodes into summaries for big-picture analysis, then expanding back to drill down into specifics. `collapse_subgraph()` removes internal edges within a group and rewires external connections to a summary node. `expand_summary()` restores the detail nodes and recreates external edges. All structure is preserved — collapsing is lossless because the AbstractionMapping tracks which detail nodes are hidden under which summary. Centrality, paths, and other graph algorithms operate on the abstracted graph without modification, producing different results at each level.

## 2. Key Concepts

| Term | Plain English Meaning |
|------|----------------------|
| **AbstractionMapping** | Tracks which detail nodes are hidden under a summary node |
| **AbstractionSummary** | Result of a collapse: summary node, edges collapsed, internal/external edge counts |
| **ExpandResult** | Result of expanding a summary back into its detail nodes |
| **Abstraction layer** | SUMMARY or DETAIL classification on node metadata |
| **External connection rewiring** | Edges from outside the collapsed set are redirected to the summary node |
| **Internal edges** | Edges between nodes within the collapsed group (removed during collapse) |
| **External edges** | Edges connecting collapsed nodes to nodes outside the group (rewired to summary) |
| **Collapse** | Replace a group of detail nodes with a single summary node |
| **Expand** | Restore detail nodes from a summary, recreating external connections |

## 3. Quick Start

```bash
.venv/bin/python examples/showcase/core/hierarchical_abstraction/hierarchical_abstraction.py
```

```
SECTION 1: BUILD ORGANIZATIONAL GRAPH
nodes: 23, edges: 22

SECTION 2: FIRST-LEVEL ABSTRACTION - COLLAPSE TEAMS
team_alpha: edges collapsed: 6, internal: 4, external: 2
team_beta: edges collapsed: 5, internal: 4, external: 1
team_gamma: edges collapsed: 6, internal: 4, external: 2
team_delta: edges collapsed: 5, internal: 4, external: 1
after team collapse: nodes=27, edges=6
active summaries: 4

SECTION 3: ANALYZE AT TEAM LEVEL
team_alpha: degree_centrality=0.0769
team_beta: degree_centrality=0.0385
team_gamma: degree_centrality=0.0769
team_delta: degree_centrality=0.0385

SECTION 4: SECOND-LEVEL ABSTRACTION - COLLAPSE DEPARTMENTS
dept_engineering: edges collapsed: 2, internal: 1, external: 1
dept_product: edges collapsed: 2, internal: 1, external: 1
after department collapse: nodes=29, edges=4
total active summaries: 6

SECTION 5: EXPAND AND DRILL DOWN
expanded 'dept_engineering': expanded nodes: 2, expanded edges: 2
after expand: nodes=28, edges=5
remaining summaries: 5

SECTION 6: CROSS-LEVEL CENTRALITY
dept_engineering: 0.1111
division_tech: 0.0741
dept_product: 0.0370
```

> Node and edge counts include detail nodes that remain in the graph (hidden but not removed).

## 4. The Scenario

A 23-node organizational graph with four node categories:

- **Employees** (20): 5 per team, distributed across 4 teams
  - team_alpha: aaron, alice, amy, anna, axel
  - team_beta: bella, betty, bob, brian, bruce
  - team_gamma: carmen, carol, charlie, clara, craig
  - team_delta: dave, derek, diana, donna, dylan
- **Departments** (2): dept_engineering (team_alpha + team_beta), dept_product (team_gamma + team_delta)
- **Division** (1): division_tech (both departments)

The hierarchy is: employees -> teams -> departments -> division.

```mermaid
graph TD
    subgraph dept_engineering
        subgraph team_alpha
            aaron ---|collaborates_with| alice
            amy ---|collaborates_with| anna
            axel ---|collaborates_with| aaron
        end
        subgraph team_beta
            bella ---|collaborates_with| bob
            betty ---|collaborates_with| brian
            bruce ---|collaborates_with| bella
        end
    end
    subgraph dept_product
        subgraph team_gamma
            carmen ---|collaborates_with| carol
            charlie ---|collaborates_with| clara
            craig ---|collaborates_with| carmen
        end
        subgraph team_delta
            dave ---|collaborates_with| diana
            derek ---|collaborates_with| donna
            dylan ---|collaborates_with| dave
        end
    end
    team_alpha -->|managed_by| dept_engineering
    team_beta -->|managed_by| dept_engineering
    team_gamma -->|managed_by| dept_product
    team_delta -->|managed_by| dept_product
```

Internal `collaborates_with` edges (within teams) are removed during collapse. External `managed_by` edges are rewired to summary nodes. Cross-team collaboration edges connect team_alpha to team_gamma and team_gamma to team_delta.

## 5. Analysis Pipeline

**Section 1 — Build organizational graph:** 23 nodes and 22 edges are created. 20 employees are stored with `data={"team": team_name}`. 2 departments and 1 division are stored with `data={"type": "department"}` and `data={"type": "division"}`. Each team has 4 internal `collaborates_with` edges (e.g., aaron-alice, amy-anna, axel-aaron, alice-amy for team_alpha), totaling 16 internal edges. Each team has 1 `managed_by` edge to its department, totaling 4 department edges. 2 cross-team `collaborates_with` edges connect team_alpha to team_gamma (alice -> carol) and team_gamma to team_delta (charlie -> dave). The division_tech node has no edges yet — it will become relevant at the department collapse level. Why this matters: the graph encodes both the hierarchy (managed_by) and the collaboration network (collaborates_with). Collapsing will hide the internal collaboration edges while preserving the hierarchical and cross-team connections.

**Section 2 — First-level abstraction — collapse teams:** `collapse_subgraph()` is called 4 times, once per team. For team_alpha: 5 employee nodes are collapsed into the summary node team_alpha. 6 edges are collapsed: 4 internal `collaborates_with` edges (within the team, removed) and 2 external connections (alice -> carol cross-team edge and managed_by edge, rewired to team_alpha). The same process applies to team_beta (5 edges collapsed: 4 internal + 1 external), team_gamma (6 edges collapsed: 4 internal + 2 external), and team_delta (5 edges collapsed: 4 internal + 1 external). After collapse: 27 nodes (20 detail employees + 4 team summaries + 2 departments + 1 division) and 6 edges (4 managed_by edges to departments + 2 cross-team collaboration edges). Active summaries: 4. Why this matters: the collapse operation reduces 16 internal edges to 0 and rewires 6 external edges to summary nodes. The abstracted graph has only 6 edges, making team-level analysis tractable. Detail nodes remain in the graph (counted in the 27 total) but are not connected — they are hidden under their summaries.

**Section 3 — Analyze at team level:** Degree centrality is computed on the abstracted graph. team_alpha and team_gamma each have centrality 0.0769 — they are connected to 2 other nodes each (1 department + 1 cross-team collaboration). team_beta and team_delta each have centrality 0.0385 — they are connected to only 1 node (their department). Betweenness centrality is 0.0000 for all teams — no team sits on the shortest path between other teams because the graph is a simple chain with cross-links. Why this matters: the team-level analysis reveals that team_alpha and team_gamma are more connected than team_beta and team_delta. At the employee level, this pattern is invisible — you would need to aggregate 20 individual centrality scores to see it. The abstraction makes the structural difference between teams immediately apparent.

**Section 4 — Second-level abstraction — collapse departments:** `collapse_subgraph()` is called 2 more times, collapsing team_alpha + team_beta into dept_engineering and team_gamma + team_delta into dept_product. dept_engineering collapses 2 edges: 1 internal (the managed_by edges from team_alpha and team_beta to dept_engineering become internal) and 1 external (dept_engineering -> division_tech). dept_product similarly collapses 2 edges. After department collapse: 29 nodes and 4 edges. Total active summaries: 6 (4 team summaries + 2 department summaries). The division_tech node now has edges to both department summaries. Why this matters: the second-level collapse stacks on top of the first. Team summaries become detail nodes under department summaries. The graph is now at department granularity, with only 4 edges connecting the 2 departments to the division and to each other.

**Section 5 — Expand and drill down:** `expand_summary()` is called on dept_engineering. This restores team_alpha and team_beta as active nodes, recreates the 2 edges that were rewired to dept_engineering, and removes the dept_engineering summary node. After expansion: 28 nodes and 5 edges. Remaining summaries: 5 (4 teams + dept_product). The expansion is precise — only dept_engineering is expanded; all other summaries remain collapsed. Why this matters: expansion is targeted. A user analyzing the department-level graph can expand one department to drill into its teams without affecting the rest of the abstraction. This enables interactive exploration: start at the top, identify the department of interest, expand it, analyze its teams, and expand further if needed.

**Section 6 — Cross-level centrality comparison:** Degree centrality is computed on the partially-expanded graph (dept_engineering expanded, dept_product still collapsed). dept_engineering has the highest centrality (0.1111) because it is connected to team_alpha, team_beta, division_tech, and dept_product via the remaining cross-department edges. division_tech follows at 0.0741. dept_product and team_alpha/team_beta each have 0.0370. Individual employees (alice, anna, aaron) have centrality 0.0000 — they are detail nodes with no edges. Why this matters: the mixed-level analysis shows how different abstraction levels coexist in the same graph. dept_engineering (expanded, showing teams) has higher centrality than dept_product (still collapsed) because its internal structure is visible. This is the correct result: dept_engineering is more connected because its teams have external edges that dept_product's collapsed summary hides.

## 6. Key Metrics

| Metric | Value |
|--------|-------|
| Original nodes | 23 (20 employees + 2 departments + 1 division) |
| Original edges | 22 |
| After team collapse | 27 nodes, 6 edges, 4 active summaries |
| Internal edges collapsed per team | 4 |
| External connections rewired per team | 1-2 |
| After department collapse | 29 nodes, 4 edges, 6 active summaries |
| After expanding dept_engineering | 28 nodes, 5 edges, 5 remaining summaries |
| Highest team-level centrality | team_alpha, team_gamma (0.0769) |
| Lowest team-level centrality | team_beta, team_delta (0.0385) |
| Highest cross-level centrality | dept_engineering (0.1111) |
| Division centrality | division_tech (0.0741) |

## 7. What Makes This Different

**Lossless collapse and expand** preserves all graph structure. Collapsing removes internal edges and rewires external connections to the summary node, but the AbstractionMapping records every detail. Expanding restores the detail nodes and recreates external edges exactly as they were. No information is lost — the graph can be collapsed and expanded any number of times without degradation.

**Multi-level stacking** enables hierarchical abstraction. Teams can be collapsed into departments, which can be collapsed into divisions, creating multiple abstraction levels in the same graph. Each level operates independently — expanding a department does not affect other departments, and collapsing a department does not require expanding its teams first. This mirrors how real organizations work: you analyze at the division level, drill into a department, then drill into a team.

**Analysis at every level** works without modification. Centrality, paths, and other graph algorithms operate on whatever nodes and edges are currently active, whether those are employees, teams, departments, or a mix. The algorithms do not need to know about the abstraction layer — they see a graph with nodes and edges, and produce results accordingly. This means the same analysis pipeline produces different insights at different granularities, all from the same underlying graph.

## 8. Code Implementation

**1. Build the organizational graph:**

```python
from hyper3 import HypergraphMemory

mem = HypergraphMemory(evolve_interval=0)

teams = {
    "team_alpha": ["aaron", "alice", "amy", "anna", "axel"],
    "team_beta": ["bella", "betty", "bob", "brian", "bruce"],
    "team_gamma": ["carmen", "carol", "charlie", "clara", "craig"],
    "team_delta": ["dave", "derek", "diana", "donna", "dylan"],
}

for team_name, members in teams.items():
    for member in members:
        mem.add(member, data={"team": team_name})

mem.add("dept_engineering", data={"type": "department"})
mem.add("dept_product", data={"type": "department"})
mem.add("division_tech", data={"type": "division"})

for members in teams.values():
    for i in range(0, len(members) - 1, 2):
        mem.link(members[i], members[i + 1], label="collaborates_with")
```

**2. Collapse teams into summary nodes:**

```python
summaries = []
for team_name, members in teams.items():
    result = mem.collapse_subgraph(
        summary_name=team_name,
        detail_nodes=set(members),
    )
    summaries.append(result)
    print(f"{team_name}: internal={result.internal_edges}, external={result.external_connections}")
```

**3. Analyze at team level:**

```python
centrality = mem.analyze.centrality("degree", )
for team_name in teams:
    print(f"{team_name}: {centrality.get(team_name, 0.0):.4f}")
```

**4. Collapse departments (second level):**

```python
mem.collapse_subgraph(
    summary_name="dept_engineering",
    detail_nodes={"team_alpha", "team_beta"},
)
mem.collapse_subgraph(
    summary_name="dept_product",
    detail_nodes={"team_gamma", "team_delta"},
)
```

**5. Expand a department to drill down:**

```python
result = mem.expand_summary("dept_engineering")
print(f"expanded nodes: {result.expanded_nodes}")
print(f"expanded edges: {result.expanded_edges}")
```

**6. Cross-level centrality comparison:**

```python
centrality = mem.analyze.centrality("degree", )
for node, score in sorted(centrality.items(), key=lambda x: -x[1])[:8]:
    print(f"  {node}: {score:.4f}")
```

## 9. Real-World Gap

This showcase demonstrates hierarchical abstraction on a small organizational graph. Real-world adoption involves additional work:

- **Detail node footprint:** Collapsed detail nodes remain in the graph (hidden but not removed). Large hierarchies with thousands of employees would retain all detail nodes, increasing memory usage. True removal with re-creation on expand would be needed for production scale.
- **Automatic hierarchy detection:** The showcase manually specifies which nodes belong to each team and department. Real organizational data would require automatic hierarchy detection from attributes (team labels, reporting lines, org charts).
- **Edge weight aggregation:** When external edges are rewired to summary nodes, the showcase preserves individual edges. Production use may need weight aggregation (sum, average, max) when multiple detail nodes connect to the same external target.
- **Scale:** The showcase runs on 23 nodes with 2 abstraction levels. Performance at 10K+ nodes with 4-5 levels is untested, particularly for the collapse/expand operations that iterate over all edges.
- **Concurrent abstraction:** The showcase serializes all collapse/expand operations. Collaborative editing with concurrent abstraction changes requires conflict resolution.
- **Persistence:** Abstraction mappings are in-memory. Persisting the mapping alongside the graph is needed for session continuity.

## 10. Reference

| Method | Purpose |
|--------|---------|
| `mem.collapse_subgraph(summary_name, detail_nodes)` | Replace detail nodes with a summary node, rewiring external edges |
| `mem.expand_summary(summary_name)` | Restore detail nodes from a summary, recreating external edges |
| `mem.analyze.centrality("degree", )` | Compute degree centrality for all nodes |
| `mem.analyze.centrality("betweenness", )` | Compute betweenness centrality for all nodes |
| `mem.add(concept, data)` | Create a node with optional data dict |
| `mem.link(source, target, label, weight)` | Add a pairwise directed edge |
| `mem.describe()` | Return graph statistics (nodes, edges, density, components) |
| `mem.neighbors(concept, direction, edge_label)` | Query neighbors filtered by direction and/or label |

### Related Examples

| Example | Connection |
|---------|-----------|
| `construction_and_queries` | Graph construction patterns used in this showcase |
| `centrality_and_ranking` | Centrality algorithms used in multi-level analysis |
| `communities_and_clustering` | Community detection as an alternative to manual hierarchy |
