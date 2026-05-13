# Enhancement: Retrieval and Feedback -- Reasoning + Communities

## Target File
`examples/showcase/retrieval/retrieval_and_feedback/retrieval_and_feedback.py`

## Current State
150+ node cybersecurity knowledge graph demonstrating multi-signal retrieval, RRF fusion, and learning-to-rank feedback. Uses only retrieval features; never leverages the graph's reasoning, community detection, or anomaly capabilities.

## Enhancement
Add three new sections after the existing LTR comparison:

### Section: Threat Chain Discovery via Reasoning
Discover multi-hop attack chains using transitive rules.

**New APIs introduced:**
- `TransitiveRule(edge_label, new_label)` -- transitive attack chain inference
- `mem.add_rules(...)` -- rule registration
- `mem.reason(seeds, max_depth, auto_commit)` -- multiway reasoning
- `mem.analyze.edges(label)` -- filter inferred edges

**Narrative flow:**
1. Register TransitiveRule for "enables" -> "enables_chain" (attack enablers)
2. Register TransitiveRule for "targets" -> "targets_chain" (target progression)
3. Run reasoning from key attack vectors (sql_injection, phishing, zero_day)
4. Show discovered multi-hop attack chains (sql_injection -> enables data_exfiltration -> enables compliance_violation)
5. Show which chains are most frequently discovered

### Section: Threat Cluster Identification
Use community detection to identify natural threat groupings.

**New APIs introduced:**
- `mem.analyze.communities(method, seed)` -- community detection
- `CommunityResult.community_count`, `.modularity`, `.communities[].member_labels`

**Narrative flow:**
1. Run community detection on the cybersecurity graph
2. Show discovered threat clusters (e.g., web_attacks, network_attacks, insider_threats)
3. Show modularity and coverage metrics
4. Discuss how clusters inform defense prioritization

### Section: Anomalous Threat Pattern Detection
Flag threats with unusual connectivity patterns.

**New APIs introduced:**
- `mem.analyze.anomalies(concept)` -- structural anomaly detection
- `result.anomaly_status`, `.boundary_score` -- anomaly classification

**Narrative flow:**
1. Run anomaly detection on key threat concepts
2. Flag boundary/anomalous threats that warrant deeper investigation
3. Show how anomalous threats have unusual connectivity patterns

## Dependencies
- `memory_reasoning.py` -- add_rules, reason
- `rules_transitive.py` -- TransitiveRule
- `memory_analytics.py` -- communities, anomalies

## Validation
- Run: `.venv/bin/python examples/showcase/retrieval/retrieval_and_feedback/retrieval_and_feedback.py`
- Verify reasoning discovers multi-hop chains
- Verify community detection identifies threat clusters
- Verify anomaly detection flags unusual patterns
- Update README.md
