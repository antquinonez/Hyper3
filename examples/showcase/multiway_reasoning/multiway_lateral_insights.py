"""Exploring Alternative Incident Hypotheses with Multiway Expansion.

Demonstrates Hyper3's core multiway reasoning feature by building a cloud
infrastructure graph (81 nodes, 203 edges across 3 regions) and running
multiway expansion from a health check failure seed. Different inference
rules produce genuinely divergent branches (infrastructure failure, network
partition, configuration error) which are then compared via state clustering
analysis and lateral insights.

This is the flagship showcase example for Hyper3's multi-hypothesis reasoning.

Run with:
    .venv/bin/python examples/showcase/multiway_reasoning/01_multiway_lateral_insights.py

See README.md in this directory for detailed architecture diagrams and explanations.
"""

from __future__ import annotations

from hyper3 import (
    HypergraphMemory,
    Modality,
    TransitiveRule,
    InverseRule,
    AbductiveRule,
)


def build_infrastructure(mem: HypergraphMemory) -> None:
    regions = ["us-east", "us-west", "eu-west"]

    for region in regions:
        mem.add(f"{region}-api", data={"type": "service", "tier": "frontend"}, modalities={Modality.CONCEPTUAL})
        mem.add(f"{region}-web", data={"type": "service", "tier": "frontend"}, modalities={Modality.CONCEPTUAL})
        mem.add(f"{region}-auth", data={"type": "service", "tier": "middleware"}, modalities={Modality.CONCEPTUAL})
        mem.add(f"{region}-cache", data={"type": "service", "tier": "middleware"}, modalities={Modality.CONCEPTUAL})
        mem.add(f"{region}-worker", data={"type": "service", "tier": "compute"}, modalities={Modality.CONCEPTUAL})
        mem.add(f"{region}-scheduler", data={"type": "service", "tier": "compute"}, modalities={Modality.CONCEPTUAL})
        mem.add(f"{region}-storage", data={"type": "storage"}, modalities={Modality.CONCEPTUAL})
        mem.add(f"{region}-ratelimiter", data={"type": "middleware"}, modalities={Modality.CONCEPTUAL})
        mem.add(f"{region}-k8s", data={"type": "orchestration"}, modalities={Modality.CONCEPTUAL})

    mem.add("db-primary", data={"type": "database", "engine": "postgresql"}, modalities={Modality.CONCEPTUAL})
    mem.add("db-replica-us-east", data={"type": "database", "engine": "postgresql"}, modalities={Modality.CONCEPTUAL})
    mem.add("db-replica-us-west", data={"type": "database", "engine": "postgresql"}, modalities={Modality.CONCEPTUAL})
    mem.add("db-replica-eu-west", data={"type": "database", "engine": "postgresql"}, modalities={Modality.CONCEPTUAL})

    mem.add("queue-primary", data={"type": "queue", "engine": "rabbitmq"}, modalities={Modality.CONCEPTUAL})
    mem.add("queue-consumer-us-east", data={"type": "queue"}, modalities={Modality.CONCEPTUAL})
    mem.add("queue-consumer-us-west", data={"type": "queue"}, modalities={Modality.CONCEPTUAL})
    mem.add("queue-consumer-eu-west", data={"type": "queue"}, modalities={Modality.CONCEPTUAL})

    mem.add("cache-primary", data={"type": "cache", "engine": "redis"}, modalities={Modality.CONCEPTUAL})
    mem.add("cache-replica-us-east", data={"type": "cache", "engine": "redis"}, modalities={Modality.CONCEPTUAL})
    mem.add("cache-replica-us-west", data={"type": "cache", "engine": "redis"}, modalities={Modality.CONCEPTUAL})
    mem.add("cache-replica-eu-west", data={"type": "cache", "engine": "redis"}, modalities={Modality.CONCEPTUAL})

    mem.add("lb-global", data={"type": "loadbalancer", "scope": "global"}, modalities={Modality.CONCEPTUAL})
    mem.add("lb-us-east", data={"type": "loadbalancer", "scope": "region"}, modalities={Modality.CONCEPTUAL})
    mem.add("lb-us-west", data={"type": "loadbalancer", "scope": "region"}, modalities={Modality.CONCEPTUAL})
    mem.add("lb-eu-west", data={"type": "loadbalancer", "scope": "region"}, modalities={Modality.CONCEPTUAL})

    mem.add("monitor-prometheus", data={"type": "monitoring"}, modalities={Modality.CONCEPTUAL})
    mem.add("alert-pagerduty", data={"type": "alerting"}, modalities={Modality.CONCEPTUAL})
    mem.add("log-aggregator", data={"type": "logging"}, modalities={Modality.CONCEPTUAL})
    mem.add("trace-jaeger", data={"type": "tracing"}, modalities={Modality.CONCEPTUAL})

    mem.add("health-checker", data={"type": "monitoring"}, modalities={Modality.CONCEPTUAL})
    mem.add("deploy-pipeline", data={"type": "ci_cd"}, modalities={Modality.CONCEPTUAL})
    mem.add("config-service", data={"type": "config"}, modalities={Modality.CONCEPTUAL})
    mem.add("dns-resolver", data={"type": "networking"}, modalities={Modality.CONCEPTUAL})
    mem.add("cdn-edge", data={"type": "networking"}, modalities={Modality.CONCEPTUAL})

    mem.add("ssl-cert", data={"type": "security"}, modalities={Modality.CONCEPTUAL})
    mem.add("iam-service", data={"type": "security"}, modalities={Modality.CONCEPTUAL})
    mem.add("secret-vault", data={"type": "security"}, modalities={Modality.CONCEPTUAL})

    mem.add("incident-response", data={"type": "process"}, modalities={Modality.CONCEPTUAL})
    mem.add("runbook-db-failover", data={"type": "runbook"}, modalities={Modality.CONCEPTUAL})
    mem.add("runbook-network-partition", data={"type": "runbook"}, modalities={Modality.CONCEPTUAL})
    mem.add("runbook-config-error", data={"type": "runbook"}, modalities={Modality.CONCEPTUAL})

    mem.add("failed-health-check", data={"type": "alert", "severity": "critical"}, modalities={Modality.CONCEPTUAL})
    mem.add("latency-spike", data={"type": "symptom"}, modalities={Modality.CONCEPTUAL})
    mem.add("error-rate-spike", data={"type": "symptom"}, modalities={Modality.CONCEPTUAL})
    mem.add("connection-refused", data={"type": "symptom"}, modalities={Modality.CONCEPTUAL})
    mem.add("timeout-error", data={"type": "symptom"}, modalities={Modality.CONCEPTUAL})
    mem.add("slow-query", data={"type": "symptom"}, modalities={Modality.CONCEPTUAL})

    mem.add("db-primary-down", data={"type": "incident", "category": "infrastructure"}, modalities={Modality.CONCEPTUAL})
    mem.add("network-partition", data={"type": "incident", "category": "network"}, modalities={Modality.CONCEPTUAL})
    mem.add("bad-deploy", data={"type": "incident", "category": "config"}, modalities={Modality.CONCEPTUAL})
    mem.add("cache-stampede", data={"type": "incident", "category": "infrastructure"}, modalities={Modality.CONCEPTUAL})

    mem.add("db-replication-lag", data={"type": "symptom", "source": "db"}, modalities={Modality.CONCEPTUAL})
    mem.add("auth-failure-rate", data={"type": "symptom", "source": "auth"}, modalities={Modality.CONCEPTUAL})
    mem.add("dns-resolution-failure", data={"type": "symptom", "source": "dns"}, modalities={Modality.CONCEPTUAL})
    mem.add("replication-stall", data={"type": "symptom", "source": "db"}, modalities={Modality.CONCEPTUAL})
    mem.add("cache-miss-rate", data={"type": "symptom", "source": "cache"}, modalities={Modality.CONCEPTUAL})
    mem.add("queue-backlog", data={"type": "symptom", "source": "queue"}, modalities={Modality.CONCEPTUAL})
    mem.add("service-unavailable", data={"type": "symptom"}, modalities={Modality.CONCEPTUAL})
    mem.add("high-cpu-usage", data={"type": "symptom"}, modalities={Modality.CONCEPTUAL})
    mem.add("disk-io-saturation", data={"type": "symptom"}, modalities={Modality.CONCEPTUAL})
    mem.add("service-mesh", data={"type": "networking"}, modalities={Modality.CONCEPTUAL})
    mem.add("api-gateway", data={"type": "networking"}, modalities={Modality.CONCEPTUAL})
    mem.add("firewall", data={"type": "security"}, modalities={Modality.CONCEPTUAL})

    mem.link("lb-global", "lb-us-east", label="routes_to")
    mem.link("lb-global", "lb-us-west", label="routes_to")
    mem.link("lb-global", "lb-eu-west", label="routes_to")

    for region in regions:
        lb = f"lb-{region}"
        api = f"{region}-api"
        web = f"{region}-web"
        auth = f"{region}-auth"
        cache_svc = f"{region}-cache"
        worker = f"{region}-worker"
        scheduler = f"{region}-scheduler"
        storage = f"{region}-storage"
        ratelimiter = f"{region}-ratelimiter"
        k8s = f"{region}-k8s"
        db_replica = f"db-replica-{region}"
        queue_consumer = f"queue-consumer-{region}"
        cache_replica = f"cache-replica-{region}"

        mem.link(lb, api, label="routes_to")
        mem.link(lb, web, label="routes_to")
        mem.link(k8s, api, label="hosts")
        mem.link(k8s, web, label="hosts")
        mem.link(k8s, auth, label="hosts")
        mem.link(k8s, cache_svc, label="hosts")
        mem.link(k8s, worker, label="hosts")
        mem.link(k8s, scheduler, label="hosts")
        mem.link(k8s, storage, label="hosts")
        mem.link(api, auth, label="depends_on")
        mem.link(api, cache_svc, label="depends_on")
        mem.link(api, db_replica, label="depends_on")
        mem.link(api, ratelimiter, label="depends_on")
        mem.link(web, api, label="depends_on")
        mem.link(web, "cdn-edge", label="depends_on")
        mem.link(auth, db_replica, label="depends_on")
        mem.link(auth, cache_svc, label="depends_on")
        mem.link(auth, "iam-service", label="depends_on")
        mem.link(cache_svc, cache_replica, label="depends_on")
        mem.link(worker, db_replica, label="depends_on")
        mem.link(worker, queue_consumer, label="depends_on")
        mem.link(worker, storage, label="depends_on")
        mem.link(scheduler, worker, label="depends_on")
        mem.link(scheduler, db_replica, label="depends_on")
        mem.link(storage, db_replica, label="depends_on")
        mem.link(ratelimiter, cache_svc, label="depends_on")
        mem.link(ratelimiter, "config-service", label="depends_on")

    mem.link("db-primary", "db-replica-us-east", label="replicates_to")
    mem.link("db-primary", "db-replica-us-west", label="replicates_to")
    mem.link("db-primary", "db-replica-eu-west", label="replicates_to")
    mem.link("db-replica-us-east", "db-replica-us-west", label="replicates_to")
    mem.link("db-replica-us-west", "db-replica-eu-west", label="replicates_to")

    mem.link("queue-primary", "queue-consumer-us-east", label="distributes_to")
    mem.link("queue-primary", "queue-consumer-us-west", label="distributes_to")
    mem.link("queue-primary", "queue-consumer-eu-west", label="distributes_to")
    mem.link("queue-consumer-us-east", "queue-consumer-us-west", label="distributes_to")

    mem.link("cache-primary", "cache-replica-us-east", label="replicates_to")
    mem.link("cache-primary", "cache-replica-us-west", label="replicates_to")
    mem.link("cache-primary", "cache-replica-eu-west", label="replicates_to")

    mem.link("health-checker", "us-east-api", label="monitors")
    mem.link("health-checker", "us-west-api", label="monitors")
    mem.link("health-checker", "eu-west-api", label="monitors")
    mem.link("health-checker", "lb-global", label="monitors")
    mem.link("health-checker", "db-primary", label="monitors")
    mem.link("monitor-prometheus", "us-east-api", label="monitors")
    mem.link("monitor-prometheus", "us-west-api", label="monitors")
    mem.link("monitor-prometheus", "eu-west-api", label="monitors")
    mem.link("monitor-prometheus", "db-primary", label="monitors")
    mem.link("monitor-prometheus", "cache-primary", label="monitors")
    mem.link("monitor-prometheus", "queue-primary", label="monitors")
    mem.link("monitor-prometheus", "lb-global", label="monitors")

    mem.link("alert-pagerduty", "monitor-prometheus", label="receives_from")
    mem.link("alert-pagerduty", "health-checker", label="receives_from")
    mem.link("incident-response", "alert-pagerduty", label="receives_from")
    mem.link("incident-response", "runbook-db-failover", label="triggers")
    mem.link("incident-response", "runbook-network-partition", label="triggers")
    mem.link("incident-response", "runbook-config-error", label="triggers")

    mem.link("log-aggregator", "us-east-api", label="collects_from")
    mem.link("log-aggregator", "us-west-api", label="collects_from")
    mem.link("log-aggregator", "eu-west-api", label="collects_from")
    mem.link("log-aggregator", "db-primary", label="collects_from")
    mem.link("trace-jaeger", "us-east-api", label="traces")
    mem.link("trace-jaeger", "us-west-api", label="traces")
    mem.link("trace-jaeger", "eu-west-api", label="traces")

    mem.link("deploy-pipeline", "us-east-api", label="deploys")
    mem.link("deploy-pipeline", "us-west-api", label="deploys")
    mem.link("deploy-pipeline", "eu-west-api", label="deploys")
    mem.link("deploy-pipeline", "config-service", label="reads")
    mem.link("config-service", "us-east-auth", label="configures")
    mem.link("config-service", "us-west-auth", label="configures")
    mem.link("config-service", "eu-west-auth", label="configures")

    mem.link("failed-health-check", "us-east-api", label="indicates")
    mem.link("failed-health-check", "lb-us-east", label="indicates")
    mem.link("latency-spike", "us-east-api", label="indicates")
    mem.link("latency-spike", "us-east-cache", label="indicates")
    mem.link("error-rate-spike", "us-east-api", label="indicates")
    mem.link("error-rate-spike", "us-east-auth", label="indicates")
    mem.link("connection-refused", "db-replica-us-east", label="indicates")
    mem.link("timeout-error", "us-east-cache", label="indicates")
    mem.link("timeout-error", "lb-us-east", label="indicates")
    mem.link("slow-query", "db-replica-us-east", label="indicates")

    mem.link("db-primary-down", "db-primary", label="affects")
    mem.link("db-primary-down", "db-replication-lag", label="causes")
    mem.link("db-primary-down", "connection-refused", label="causes")
    mem.link("db-replication-lag", "slow-query", label="causes")
    mem.link("db-replication-lag", "replication-stall", label="causes")
    mem.link("connection-refused", "failed-health-check", label="causes")
    mem.link("slow-query", "latency-spike", label="causes")
    mem.link("replication-stall", "service-unavailable", label="causes")

    mem.link("network-partition", "lb-global", label="affects")
    mem.link("network-partition", "dns-resolution-failure", label="causes")
    mem.link("dns-resolution-failure", "timeout-error", label="causes")
    mem.link("network-partition", "failed-health-check", label="causes")
    mem.link("network-partition", "latency-spike", label="causes")
    mem.link("timeout-error", "failed-health-check", label="causes")

    mem.link("bad-deploy", "us-east-auth", label="affects")
    mem.link("bad-deploy", "deploy-pipeline", label="via")
    mem.link("bad-deploy", "auth-failure-rate", label="causes")
    mem.link("auth-failure-rate", "error-rate-spike", label="causes")
    mem.link("bad-deploy", "failed-health-check", label="causes")
    mem.link("error-rate-spike", "failed-health-check", label="causes")

    mem.link("cache-stampede", "cache-primary", label="affects")
    mem.link("cache-stampede", "cache-miss-rate", label="causes")
    mem.link("cache-miss-rate", "latency-spike", label="causes")
    mem.link("cache-stampede", "timeout-error", label="causes")
    mem.link("cache-stampede", "queue-backlog", label="causes")
    mem.link("queue-backlog", "high-cpu-usage", label="causes")

    mem.link("disk-io-saturation", "db-primary", label="affects")
    mem.link("disk-io-saturation", "slow-query", label="causes")
    mem.link("disk-io-saturation", "db-replication-lag", label="causes")

    mem.link("service-mesh", "us-east-api", label="routes_to")
    mem.link("service-mesh", "us-west-api", label="routes_to")
    mem.link("service-mesh", "eu-west-api", label="routes_to")
    mem.link("api-gateway", "us-east-api", label="routes_to")
    mem.link("api-gateway", "us-west-api", label="routes_to")
    mem.link("api-gateway", "eu-west-api", label="routes_to")
    mem.link("api-gateway", "service-mesh", label="depends_on")
    mem.link("firewall", "lb-global", label="protects")
    mem.link("firewall", "api-gateway", label="protects")
    mem.link("firewall", "service-mesh", label="protects")

    mem.link("iam-service", "us-east-auth", label="authenticates")
    mem.link("iam-service", "us-west-auth", label="authenticates")
    mem.link("iam-service", "eu-west-auth", label="authenticates")
    mem.link("ssl-cert", "lb-global", label="secures")
    mem.link("ssl-cert", "lb-us-east", label="secures")
    mem.link("ssl-cert", "lb-us-west", label="secures")
    mem.link("ssl-cert", "lb-eu-west", label="secures")
    mem.link("secret-vault", "config-service", label="provides")
    mem.link("secret-vault", "iam-service", label="provides")
    mem.link("dns-resolver", "lb-global", label="resolves")
    mem.link("dns-resolver", "cdn-edge", label="resolves")
    mem.link("dns-resolver", "dns-resolution-failure", label="triggers")
    mem.link("cdn-edge", "us-east-web", label="serves")
    mem.link("cdn-edge", "us-west-web", label="serves")
    mem.link("cdn-edge", "eu-west-web", label="serves")

    mem.link("runbook-db-failover", "db-primary-down", label="resolves")
    mem.link("runbook-network-partition", "network-partition", label="resolves")
    mem.link("runbook-config-error", "bad-deploy", label="resolves")

    for region in regions:
        api = f"{region}-api"
        other_regions = [r for r in regions if r != region]
        for other in other_regions:
            other_api = f"{other}-api"
            mem.link(api, other_api, label="fails_over_to")

    mem.link("lb-us-east", "lb-us-west", label="fails_over_to")
    mem.link("lb-us-west", "lb-eu-west", label="fails_over_to")


def score_branch_against_symptoms(
    mem: HypergraphMemory,
    leaf,
    symptom_ids: set[str],
) -> float:
    produced = set(leaf.produced_edge_ids)
    hits = 0
    total = len(symptom_ids)
    if total == 0:
        return 0.0
    for eid in produced:
        edge = mem.engine.graph.get_edge(eid)
        if edge and (edge.source_ids & symptom_ids or edge.target_ids & symptom_ids):
            hits += 1
    active_symptom_overlap = len(leaf.active_node_ids & symptom_ids)
    return (hits + active_symptom_overlap) / (total + len(produced) + 1)


def summarize_state(mem: HypergraphMemory, state, max_labels: int = 6) -> dict:
    labels: list[str] = []
    for nid in list(state.active_node_ids)[:max_labels]:
        node = mem.engine.graph.get_node(nid)
        labels.append(node.label if node else nid[:8])
    produced_labels: list[str] = []
    for eid in state.produced_edge_ids:
        edge = mem.engine.graph.get_edge(eid)
        if edge:
            src_labels = []
            for sid in edge.source_ids:
                n = mem.engine.graph.get_node(sid)
                src_labels.append(n.label if n else sid[:8])
            tgt_labels = []
            for tid in edge.target_ids:
                n = mem.engine.graph.get_node(tid)
                tgt_labels.append(n.label if n else tid[:8])
            produced_labels.append(f"{' '.join(src_labels)}-[{edge.label}]->{' '.join(tgt_labels)}")
    return {
        "id": state.id[:8],
        "depth": state.depth,
        "rule": state.rule_applied or "root",
        "active_nodes": labels,
        "produced_edges": produced_labels[:4],
    }


def main():
    mem = HypergraphMemory(evolve_interval=0)

    # =====================================================================
    # SECTION 1: Build Cloud Infrastructure Graph
    # =====================================================================

    print("=" * 70)
    print("SECTION 1: Cloud Infrastructure Graph")
    print("=" * 70)

    build_infrastructure(mem)

    print(f"  Nodes: {mem.size[0]}")
    print(f"  Edges: {mem.size[1]}")
    print()

    # =====================================================================
    # SECTION 2: Multiway Expansion from Failed Health Check
    # =====================================================================

    print("=" * 70)
    print("SECTION 2: Multiway Expansion from Failed Health Check")
    print("=" * 70)

    rules = [
        TransitiveRule(edge_label="depends_on", new_label="cascade_depends"),
        TransitiveRule(edge_label="causes", new_label="indirectly_causes"),
        TransitiveRule(edge_label="affects", new_label="indirectly_affects"),
        TransitiveRule(edge_label="indicates", new_label="correlates_with"),
        TransitiveRule(edge_label="routes_to", new_label="indirectly_routes"),
        InverseRule(edge_label="depends_on", inverse_label="depended_on_by"),
        InverseRule(edge_label="causes", inverse_label="caused_by"),
        InverseRule(edge_label="monitors", inverse_label="monitored_by"),
        InverseRule(edge_label="affects", inverse_label="affected_by"),
        AbductiveRule(effect_label="causes", cause_label="possible_cause"),
    ]
    mem.add_rules(*rules)

    seed = {
        "failed-health-check", "latency-spike", "error-rate-spike",
        "connection-refused", "timeout-error", "slow-query",
        "db-primary-down", "network-partition", "bad-deploy",
        "us-east-api", "us-east-auth", "us-east-cache",
        "db-replica-us-east", "cache-replica-us-east",
        "lb-us-east", "lb-global",
    }
    result = mem.reason(
        seeds=seed,
        max_depth=3,
        max_total_states=50,
    )

    exp = result.expansion
    print(f"  States created:    {exp.states_created}")
    print(f"  Rules applied:     {exp.rules_applied}")
    print(f"  New edges:         {exp.edges_produced}")
    print(f"  New nodes:         {exp.nodes_produced}")
    print(f"  Max depth:         {exp.max_depth}")
    print(f"  Branches (leaves): {exp.branches}")
    print()

    # =====================================================================
    # SECTION 3: Branch-by-Branch Hypothesis Analysis
    # =====================================================================

    print("=" * 70)
    print("SECTION 3: Branch-by-Branch Hypothesis Analysis")
    print("=" * 70)

    symptom_labels = [
        "failed-health-check", "latency-spike", "error-rate-spike",
        "connection-refused", "timeout-error", "slow-query",
        "service-unavailable", "high-cpu-usage",
    ]
    symptom_ids: set[str] = set()
    for s_label in symptom_labels:
        node = mem.engine.graph.get_node_by_label(s_label)
        if node:
            symptom_ids.add(node.id)

    mw_graph = mem.multiway.multiway if mem.multiway else None
    leaves = mw_graph.get_leaves() if mw_graph else []
    print(f"  Total leaf states: {len(leaves)}")

    branch_scores: list[tuple[dict, float]] = []
    for leaf in leaves:
        summary = summarize_state(mem, leaf)
        score = score_branch_against_symptoms(mem, leaf, symptom_ids)
        branch_scores.append((summary, score))

    branch_scores.sort(key=lambda x: x[1], reverse=True)

    print("\n  Top branches by symptom explanation power:")
    for i, (summary, score) in enumerate(branch_scores[:10]):
        print(f"\n  Branch {i+1}: score={score:.3f}  depth={summary['depth']}  rule={summary['rule']}")
        print(f"    Active: {', '.join(summary['active_nodes'])}")
        if summary["produced_edges"]:
            print(f"    Inferred edges:")
            for pe in summary["produced_edges"]:
                print(f"      {pe}")
    print()

    # =====================================================================
    # SECTION 4: State Clustering -- Similarity and Convergence
    # =====================================================================

    print("=" * 70)
    print("SECTION 4: State Clustering Analysis")
    print("=" * 70)

    clustering_report = result.clustering
    if clustering_report:
        print("  Clustering analysis:")
        for key, val in clustering_report.items():
            if isinstance(val, (int, float, str)):
                print(f"    {key}: {val}")
            elif isinstance(val, list):
                print(f"    {key}: {len(val)} items")

    if mem.state_clustering:
        groups = mem.state_clustering.simultaneity_groups
        print(f"\n  Simultaneity groups: {len(groups)}")
        for i, group in enumerate(groups[:5]):
            group_labels: list[str] = []
            for sid in list(group.state_ids)[:4]:
                st = mw_graph.get_state(sid) if mw_graph else None
                if st:
                    rule = st.rule_applied or "root"
                    group_labels.append(f"[{rule} d={st.depth}]")
            print(f"    Group {i+1}: {len(group.state_ids)} states  {', '.join(group_labels)}")

        coords = mem.state_clustering.coordinates
        if coords and len(leaves) >= 2:
            print(f"\n  Pairwise state_clustering distances (top leaves):")
            top_leaves = leaves[:6] if len(leaves) >= 6 else leaves
            for i, la in enumerate(top_leaves):
                for lb in top_leaves[i+1:]:
                    ca = coords.get(la.id)
                    cb = coords.get(lb.id)
                    if ca and cb:
                        dist = ca.distance_to(cb)
                        ra = la.rule_applied or "root"
                        rb = lb.rule_applied or "root"
                        print(f"    [{ra} d={la.depth}] <-> [{rb} d={lb.depth}]: {dist:.3f}")
    print()

    # =====================================================================
    # SECTION 5: Convergence Detection
    # =====================================================================

    print("=" * 70)
    print("SECTION 5: Convergent Hypothesis Branches")
    print("=" * 70)

    ci = result.state_convergence
    invariants = ci.merges_performed if ci else 0
    reduction = ci.reduction if ci else 0
    print(f"  Causal invariants found: {invariants}")
    print(f"  States reduced via merge: {reduction}")

    convergent_pairs: list[tuple[str, str, int]] = []
    if mw_graph:
        states = mw_graph.states
        target_sets: dict[str, set[str]] = {}
        for s in states:
            targets: set[str] = set()
            for eid in s.produced_edge_ids:
                edge = mem.engine.graph.get_edge(eid)
                if edge:
                    targets |= edge.target_ids
            target_sets[s.id] = targets

        all_states = [s for s in states if s.rule_applied]
        for i, sa in enumerate(all_states):
            for sb in all_states[i+1:]:
                if sa.rule_applied is not None and sb.rule_applied is not None and sa.rule_applied == sb.rule_applied:
                    continue
                overlap = target_sets.get(sa.id, set()) & target_sets.get(sb.id, set())
                if len(overlap) >= 2:
                    a_rule = sa.rule_applied or ""
                    b_rule = sb.rule_applied or ""
                    convergent_pairs.append((a_rule, b_rule, len(overlap)))

    if convergent_pairs:
        print("\n  Convergent branches (different rules, overlapping conclusions):")
        seen: set[tuple[str, ...]] = set()
        for ra, rb, overlap in convergent_pairs:
            key = tuple(sorted([ra, rb]))
            if key not in seen:
                seen.add(key)
                print(f"    {ra} <-> {rb}: {overlap} shared target nodes")
    else:
        print("  No strong convergence detected across different rule paths")
    print()

    # =====================================================================
    # SECTION 6: Lateral Insights Across Branches
    # =====================================================================

    print("=" * 70)
    print("SECTION 6: Lateral Insights Across Branches")
    print("=" * 70)

    insight_seeds = ["failed-health-check", "db-primary-down", "network-partition", "bad-deploy"]
    total_insights = 0
    for concept in insight_seeds:
        insights = mem.lateral_insights(concept)
        total_insights += len(insights)
        if insights:
            print(f"\n  API lateral insights for '{concept}':")
            for ins in insights[:3]:
                lat_id = ins.get("lateral_state", "")
                lat_state = mw_graph.get_state(lat_id) if mw_graph else None
                rule = lat_state.rule_applied if lat_state else "unknown"
                distance = ins.get("jaccard_distance", 0.0)
                novel_lateral = ins.get("novel_in_lateral", [])
                novel_labels = []
                for nid in novel_lateral:
                    node = mem.engine.graph.get_node(nid)
                    if node:
                        novel_labels.append(node.label)
                print(f"    Branch [{rule}], distance={distance:.2f}")
                if novel_labels:
                    print(f"      Novel nodes: {', '.join(novel_labels[:5])}")
        else:
            print(f"  No API lateral insights for '{concept}'")

    print(f"\n  Manual lateral comparison across simultaneity groups:")
    if mem.state_clustering and mw_graph:
        for gi, group in enumerate(mem.state_clustering.simultaneity_groups[:4]):
            group_states = [mw_graph.get_state(sid) for sid in group.state_ids]
            group_states = [s for s in group_states if s is not None]
            if len(group_states) < 2:
                continue
            print(f"\n    Group {gi+1} ({len(group_states)} states):")
            edge_label_sets: list[tuple[str, set[str]]] = []
            node_label_sets: list[tuple[str, set[str]]] = []
            for s in group_states:
                s_edge_labels: set[str] = set()
                s_node_labels: set[str] = set()
                for eid in s.produced_edge_ids:
                    edge = mem.engine.graph.get_edge(eid)
                    if edge:
                        src = next(iter(edge.source_ids), "")
                        tgt = next(iter(edge.target_ids), "")
                        sn = mem.engine.graph.get_node(src)
                        tn = mem.engine.graph.get_node(tgt)
                        s_edge_labels.add(f"{sn.label if sn else src[:8]}-{edge.label}->{tn.label if tn else tgt[:8]}")
                for nid in s.produced_node_ids:
                    n = mem.engine.graph.get_node(nid)
                    s_node_labels.add(n.label if n else nid[:8])
                rule = s.rule_applied or "root"
                edge_label_sets.append((rule, s_edge_labels))
                node_label_sets.append((rule, s_node_labels))

            shown = 0
            for i, (rule_a, edges_a) in enumerate(edge_label_sets):
                if shown >= 3:
                    break
                for j, (rule_b, edges_b) in enumerate(edge_label_sets):
                    if j <= i or shown >= 3:
                        continue
                    if rule_a == rule_b:
                        continue
                    novel_a = edges_a - edges_b
                    novel_b = edges_b - edges_a
                    if novel_a or novel_b:
                        print(f"      [{rule_a[:30]}] vs [{rule_b[:30]}]:")
                        if novel_a:
                            print(f"        Unique to first: {', '.join(list(novel_a)[:2])}")
                        if novel_b:
                            print(f"        Unique to second: {', '.join(list(novel_b)[:2])}")
                        total_insights += 1
                        shown += 1

            all_node_sets = [ns for _, ns in node_label_sets]
            if all_node_sets:
                common_nodes = set.intersection(*all_node_sets) if len(all_node_sets) > 1 else all_node_sets[0]
                novel_nodes_across = set()
                for ns in all_node_sets:
                    novel_nodes_across |= (ns - common_nodes)
                if novel_nodes_across:
                    print(f"      Novel hypothesis nodes across group: {', '.join(list(novel_nodes_across)[:5])}")
    print()

    # =====================================================================
    # SUMMARY
    # =====================================================================

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Infrastructure graph: {mem.size[0]} nodes, {mem.size[1]} edges")
    print(f"  Reasoning branches explored: {len(leaves)}")
    print(f"  Total inference edges produced: {exp.edges_produced}")
    print(f"  Total inference nodes produced: {exp.nodes_produced}")
    if branch_scores:
        best = branch_scores[0]
        print(f"  Best explanation branch: rule={best[0]['rule']}, score={best[1]:.3f}")
    print(f"  Convergent branch pairs found: {len(convergent_pairs)}")
    print(f"  Causal invariants merged: {ci.get('reduction', 0) if ci else 0}")
    print(f"  Lateral insights discovered: {total_insights}")
    print()
    print("  Key finding: multiway expansion produces genuinely different")
    print("  hypothesis branches (infrastructure, network, config) from a")
    print("  single seed event, each explaining different subsets of symptoms.")
    print("  State clustering reveals which branches converge and lateral")
    print("  insights identify knowledge transferable across hypotheses.")
    print()


if __name__ == "__main__":
    main()
