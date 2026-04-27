"""
Code Dependency and Blast Radius Analysis
==========================================

Model a realistic large monorepo as a dependency graph in Hyper3, then
analyze blast radius, circular dependencies, coupling, test-coverage gaps,
and outdated third-party packages.

Run with:
    .venv/bin/python examples/domain/code_dependency_analysis.py
"""

from __future__ import annotations

from hyper3 import CognitiveMemory, TransitiveRule


def main():
    mem = CognitiveMemory(evolve_interval=0)

    # =====================================================================
    # SECTION 1: Generate 120+ Module Nodes
    # =====================================================================

    print("=" * 70)
    print("SECTION 1: Generating Monorepo Module Graph")
    print("=" * 70)

    core_modules = {}
    for i, name in enumerate([
        "core.engine", "core.runtime", "core.scheduler", "core.dispatcher",
        "core.registry", "core.pipeline", "core.validator", "core.serializer",
        "core.parser", "core.encoder", "core.transform", "core.loader",
        "core.resolver", "core.emitter", "core.handler", "core.middleware_base",
        "core.plugin_host", "core.event_bus", "core.state_machine", "core.graph",
        "core.cache_base", "core.retry", "core.circuit_breaker", "core.rate_limiter",
        "core.health", "core.config_base", "core.logging_base", "core.metrics_base",
        "core.auth_base", "core.crypto",
    ], start=1):
        core_modules[name] = {
            "category": "core",
            "layer": "core" if i <= 15 else ("infra" if i <= 22 else "util"),
            "language": "python",
            "team": ["platform", "infra", "sdk"][i % 3],
            "test_coverage": round(0.4 + (i % 10) * 0.06, 2),
            "loc": 200 + i * 120,
        }

    service_modules = {}
    for i, name in enumerate([
        "svc.auth", "svc.users", "svc.orders", "svc.payments",
        "svc.notifications", "svc.search", "svc.analytics", "svc.billing",
        "svc.inventory", "svc.shipping", "svc.reviews", "svc.recommendations",
        "svc.media", "svc.messages", "svc.sessions", "svc.tenants",
        "svc.audit", "svc.webhooks", "svc.exports", "svc.imports",
        "svc.scheduler", "svc.workflows", "svc.comments", "svc.tags",
        "svc.bookmarks",
    ], start=1):
        service_modules[name] = {
            "category": "service",
            "api_version": f"v{(i % 3) + 1}",
            "team": ["identity", "commerce", "content", "platform"][i % 4],
            "endpoint_count": 3 + (i % 8),
            "latency_p95": 40 + (i % 5) * 30,
        }

    data_modules = {}
    for i, name in enumerate([
        "data.models_user", "data.models_order", "data.models_product",
        "data.models_payment", "data.models_notification", "data.models_session",
        "data.models_audit", "data.models_media", "data.models_analytics",
        "data.models_inventory", "data.models_shipping", "data.models_review",
        "data.repo_user", "data.repo_order", "data.repo_product",
        "data.repo_payment", "data.repo_analytics", "data.migration_framework",
        "data.connection_pool", "data.query_builder",
    ], start=1):
        data_modules[name] = {
            "category": "data",
            "orm": "sqlalchemy" if i <= 12 else "raw",
            "table_count": 2 + (i % 6),
            "migration_count": 1 + (i % 10),
        }

    third_party = {}
    for i, (name, ver, yr) in enumerate([
        ("3p.django", "4.2", 2023), ("3p.flask", "3.0", 2024),
        ("3p.requests", "2.31", 2023), ("3p.numpy", "1.26", 2024),
        ("3p.pandas", "2.1", 2023), ("3p.redis", "5.0", 2024),
        ("3p.celery", "5.3", 2023), ("3p.sqlalchemy", "2.0", 2024),
        ("3p.psycopg2", "2.9", 2021), ("3p.pymongo", "4.5", 2023),
        ("3p.boto3", "1.28", 2023), ("3p.pyjwt", "2.8", 2023),
        ("3p.sentry", "1.38", 2023), ("3p.urllib3", "1.26", 2021),
        ("3p.protobuf", "4.24", 2023),
    ], start=1):
        third_party[name] = {
            "category": "third_party",
            "version": ver,
            "license": ["MIT", "Apache-2.0", "BSD-3"][i % 3],
            "last_updated": yr,
            "is_pinned": i % 3 == 0,
        }

    config_modules = {}
    for i, name in enumerate([
        "cfg.app", "cfg.database", "cfg.cache", "cfg.queue",
        "cfg.auth", "cfg.logging", "cfg.metrics", "cfg.features",
        "cfg.rate_limits", "cfg.cors", "cfg.secrets", "cfg.endpoints",
        "cfg.tenant", "cfg.worker", "cfg.storage",
    ], start=1):
        config_modules[name] = {
            "category": "config",
            "env": ["prod", "staging", "dev"][i % 3],
            "type": ["yaml", "env_var", "json"][i % 3],
        }

    shared_utils = {}
    for i, name in enumerate([
        "util.logging", "util.auth_helpers", "util.metrics", "util.tracing",
        "util.http_client", "util.date_helpers", "util.serialization",
        "util.validation", "util.retry_helpers", "util.encoding",
    ], start=1):
        shared_utils[name] = {
            "category": "shared",
            "type": ["logging", "auth", "metrics", "tracing",
                     "http", "date", "serialization", "validation",
                     "retry", "encoding"][i - 1],
            "team": ["platform", "infra", "sdk"][i % 3],
        }

    test_modules = {}
    for i, name in enumerate([
        "test.unit_core", "test.unit_services", "test.unit_data",
        "test.integraton_auth", "test.integration_orders",
        "test.e2e_checkout", "test.e2e_user_flow",
        "test.load_billing", "test.smoke", "test.regression_payments",
    ], start=1):
        test_modules[name] = {
            "category": "test",
            "type": ["unit", "integration", "e2e", "load", "smoke"][(i - 1) // 2],
            "coverage_pct": round(0.3 + (i % 6) * 0.12, 2),
        }

    all_modules = {}
    for group in [core_modules, service_modules, data_modules, third_party,
                  config_modules, shared_utils, test_modules]:
        all_modules.update(group)

    for label, data in all_modules.items():
        mem.store(label, data=data)

    print(f"  Stored {len(all_modules)} modules")
    print()

    # =====================================================================
    # SECTION 2: Create 250+ Dependency Edges
    # =====================================================================

    print("=" * 70)
    print("SECTION 2: Creating Dependency Edges")
    print("=" * 70)

    edges = []

    for svc in list(service_modules)[:20]:
        edges.append((svc, "core.engine", "depends_on"))
    for svc in list(service_modules)[:15]:
        edges.append((svc, "core.config_base", "depends_on"))
    for svc in list(service_modules)[:10]:
        edges.append((svc, "core.middleware_base", "depends_on"))

    for svc in ["svc.auth", "svc.sessions", "svc.tenants"]:
        edges.append((svc, "core.auth_base", "depends_on"))
        edges.append((svc, "core.crypto", "depends_on"))

    for svc in ["svc.notifications", "svc.messages", "svc.webhooks"]:
        edges.append((svc, "core.event_bus", "depends_on"))
        edges.append((svc, "svc.scheduler", "depends_on"))

    for svc in ["svc.search", "svc.analytics", "svc.recommendations"]:
        edges.append((svc, "core.graph", "depends_on"))
        edges.append((svc, "core.cache_base", "depends_on"))

    edges += [
        ("svc.orders", "svc.users", "depends_on"),
        ("svc.orders", "svc.payments", "depends_on"),
        ("svc.orders", "svc.inventory", "depends_on"),
        ("svc.orders", "svc.shipping", "depends_on"),
        ("svc.orders", "data.repo_order", "depends_on"),
        ("svc.orders", "data.models_order", "imports"),
        ("svc.billing", "svc.payments", "depends_on"),
        ("svc.billing", "svc.orders", "depends_on"),
        ("svc.shipping", "svc.inventory", "depends_on"),
        ("svc.inventory", "data.repo_inventory", "depends_on"),
        ("svc.reviews", "svc.users", "depends_on"),
        ("svc.reviews", "data.repo_product", "depends_on"),
        ("svc.media", "core.loader", "depends_on"),
        ("svc.comments", "svc.users", "depends_on"),
        ("svc.tags", "core.graph", "depends_on"),
        ("svc.bookmarks", "svc.users", "depends_on"),
        ("svc.exports", "core.serializer", "depends_on"),
        ("svc.imports", "core.parser", "depends_on"),
        ("svc.workflows", "core.state_machine", "depends_on"),
        ("svc.workflows", "core.pipeline", "depends_on"),
        ("svc.audit", "data.repo_audit", "depends_on"),
        ("svc.audit", "core.event_bus", "depends_on"),
    ]

    edges += [
        ("svc.auth", "data.repo_user", "depends_on"),
        ("svc.auth", "data.models_user", "imports"),
        ("svc.auth", "util.auth_helpers", "depends_on"),
        ("svc.auth", "cfg.auth", "configures"),
        ("svc.auth", "3p.pyjwt", "depends_on"),
        ("svc.users", "data.repo_user", "depends_on"),
        ("svc.users", "data.models_user", "imports"),
        ("svc.users", "util.serialization", "imports"),
        ("svc.payments", "data.repo_payment", "depends_on"),
        ("svc.payments", "data.models_payment", "imports"),
        ("svc.payments", "3p.stripe", "depends_on"),
        ("svc.payments", "cfg.app", "configures"),
        ("svc.notifications", "data.models_notification", "imports"),
        ("svc.notifications", "3p.sentry", "depends_on"),
        ("svc.search", "data.models_product", "imports"),
        ("svc.analytics", "data.repo_analytics", "depends_on"),
        ("svc.analytics", "data.models_analytics", "imports"),
    ]

    for repo in ["data.repo_user", "data.repo_order", "data.repo_product",
                 "data.repo_payment", "data.repo_analytics", "data.repo_inventory"]:
        edges.append((repo, "data.connection_pool", "depends_on"))
        edges.append((repo, "data.query_builder", "depends_on"))

    edges += [
        ("data.repo_user", "data.models_user", "imports"),
        ("data.repo_order", "data.models_order", "imports"),
        ("data.repo_product", "data.models_product", "imports"),
        ("data.repo_payment", "data.models_payment", "imports"),
        ("data.repo_analytics", "data.models_analytics", "imports"),
        ("data.repo_inventory", "data.models_inventory", "imports"),
    ]

    for model in list(data_modules)[:12]:
        edges.append((model, "3p.sqlalchemy", "depends_on"))

    edges += [
        ("data.connection_pool", "3p.psycopg2", "depends_on"),
        ("data.connection_pool", "cfg.database", "configures"),
        ("data.query_builder", "3p.sqlalchemy", "depends_on"),
        ("data.migration_framework", "data.connection_pool", "depends_on"),
        ("data.migration_framework", "3p.sqlalchemy", "depends_on"),
    ]

    for model in list(data_modules)[:8]:
        edges.append((model, "core.serializer", "imports"))

    edges += [
        ("core.engine", "core.registry", "depends_on"),
        ("core.engine", "core.event_bus", "depends_on"),
        ("core.engine", "core.config_base", "depends_on"),
        ("core.engine", "core.logging_base", "imports"),
        ("core.engine", "core.metrics_base", "imports"),
        ("core.runtime", "core.state_machine", "depends_on"),
        ("core.runtime", "core.health", "depends_on"),
        ("core.scheduler", "core.runtime", "depends_on"),
        ("core.scheduler", "core.pipeline", "depends_on"),
        ("core.dispatcher", "core.handler", "depends_on"),
        ("core.dispatcher", "core.event_bus", "depends_on"),
        ("core.pipeline", "core.validator", "depends_on"),
        ("core.pipeline", "core.transform", "depends_on"),
        ("core.registry", "core.resolver", "depends_on"),
        ("core.validator", "core.parser", "depends_on"),
        ("core.serializer", "core.encoder", "depends_on"),
        ("core.loader", "core.parser", "depends_on"),
        ("core.loader", "core.resolver", "depends_on"),
        ("core.middleware_base", "core.handler", "depends_on"),
        ("core.middleware_base", "core.pipeline", "depends_on"),
        ("core.plugin_host", "core.registry", "depends_on"),
        ("core.plugin_host", "core.loader", "depends_on"),
        ("core.event_bus", "core.emitter", "depends_on"),
        ("core.state_machine", "core.graph", "depends_on"),
        ("core.cache_base", "3p.redis", "depends_on"),
        ("core.cache_base", "cfg.cache", "configures"),
        ("core.retry", "core.circuit_breaker", "depends_on"),
        ("core.rate_limiter", "3p.redis", "depends_on"),
        ("core.rate_limiter", "cfg.rate_limits", "configures"),
        ("core.health", "core.metrics_base", "imports"),
        ("core.config_base", "core.logging_base", "imports"),
        ("core.auth_base", "core.crypto", "depends_on"),
        ("core.auth_base", "cfg.auth", "configures"),
        ("core.crypto", "3p.pyjwt", "depends_on"),
    ]

    edges += [
        ("util.logging", "core.logging_base", "extends"),
        ("util.logging", "cfg.logging", "configures"),
        ("util.auth_helpers", "core.auth_base", "extends"),
        ("util.metrics", "core.metrics_base", "extends"),
        ("util.metrics", "cfg.metrics", "configures"),
        ("util.tracing", "core.pipeline", "depends_on"),
        ("util.http_client", "3p.requests", "depends_on"),
        ("util.http_client", "3p.urllib3", "depends_on"),
        ("util.http_client", "core.retry", "depends_on"),
        ("util.date_helpers", "core.transform", "imports"),
        ("util.serialization", "core.serializer", "extends"),
        ("util.validation", "core.validator", "extends"),
        ("util.retry_helpers", "core.retry", "extends"),
        ("util.retry_helpers", "core.circuit_breaker", "imports"),
        ("util.encoding", "core.encoder", "extends"),
    ]

    edges += [
        ("cfg.app", "cfg.secrets", "depends_on"),
        ("cfg.app", "cfg.endpoints", "depends_on"),
        ("cfg.database", "cfg.secrets", "depends_on"),
        ("cfg.cache", "cfg.app", "depends_on"),
        ("cfg.queue", "cfg.app", "depends_on"),
        ("cfg.auth", "cfg.secrets", "depends_on"),
        ("cfg.logging", "cfg.app", "depends_on"),
        ("cfg.metrics", "cfg.app", "depends_on"),
        ("cfg.rate_limits", "cfg.app", "depends_on"),
        ("cfg.cors", "cfg.app", "depends_on"),
        ("cfg.tenant", "cfg.database", "depends_on"),
        ("cfg.worker", "cfg.queue", "depends_on"),
        ("cfg.storage", "cfg.secrets", "depends_on"),
    ]

    edges += [
        ("test.unit_core", "core.engine", "tests"),
        ("test.unit_core", "core.runtime", "tests"),
        ("test.unit_core", "core.scheduler", "tests"),
        ("test.unit_core", "core.validator", "tests"),
        ("test.unit_services", "svc.auth", "tests"),
        ("test.unit_services", "svc.users", "tests"),
        ("test.unit_services", "svc.orders", "tests"),
        ("test.unit_services", "svc.payments", "tests"),
        ("test.unit_data", "data.repo_user", "tests"),
        ("test.unit_data", "data.repo_order", "tests"),
        ("test.integraton_auth", "svc.auth", "tests"),
        ("test.integraton_auth", "svc.sessions", "tests"),
        ("test.integration_orders", "svc.orders", "tests"),
        ("test.integration_orders", "svc.payments", "tests"),
        ("test.integration_orders", "svc.inventory", "tests"),
        ("test.e2e_checkout", "svc.orders", "tests"),
        ("test.e2e_checkout", "svc.payments", "tests"),
        ("test.e2e_checkout", "svc.shipping", "tests"),
        ("test.e2e_user_flow", "svc.auth", "tests"),
        ("test.e2e_user_flow", "svc.users", "tests"),
        ("test.load_billing", "svc.billing", "tests"),
        ("test.smoke", "core.health", "tests"),
        ("test.regression_payments", "svc.payments", "tests"),
    ]

    edges.append((svc, "core.health", "imports"))

    for svc in list(service_modules)[:6]:
        edges.append((svc, "util.tracing", "imports"))
        edges.append((svc, "util.metrics", "imports"))

    for svc in list(service_modules)[6:12]:
        edges.append((svc, "util.logging", "imports"))
        edges.append((svc, "util.http_client", "imports"))

    for svc in list(service_modules)[12:18]:
        edges.append((svc, "util.retry_helpers", "imports"))

    for svc in list(service_modules)[:8]:
        edges.append((svc, "util.validation", "imports"))

    for svc in list(service_modules)[8:14]:
        edges.append((svc, "util.serialization", "imports"))

    for svc in ["svc.notifications", "svc.messages"]:
        edges.append((svc, "3p.celery", "depends_on"))

    edges += [
        ("svc.search", "3p.elasticsearch", "depends_on"),
        ("svc.analytics", "3p.pandas", "depends_on"),
        ("svc.analytics", "3p.numpy", "depends_on"),
        ("svc.media", "3p.boto3", "depends_on"),
        ("svc.exports", "3p.protobuf", "depends_on"),
        ("svc.scheduler", "3p.celery", "depends_on"),
        ("svc.scheduler", "cfg.worker", "configures"),
    ]

    for svc in ["svc.auth", "svc.users", "svc.orders", "svc.payments",
                "svc.billing", "svc.inventory"]:
        edges.append((svc, "core.retry", "imports"))
        edges.append((svc, "core.circuit_breaker", "imports"))

    for cfg in ["cfg.app", "cfg.database", "cfg.cache", "cfg.queue", "cfg.auth"]:
        edges.append((cfg, "3p.django", "depends_on"))

    edges.append(("3p.urllib3", "3p.requests", "extends"))

    edges += [
        ("core.graph", "core.cache_base", "depends_on"),
        ("core.emitter", "core.handler", "depends_on"),
        ("core.handler", "core.logging_base", "imports"),
        ("core.crypto", "core.retry", "depends_on"),
        ("data.migration_framework", "data.query_builder", "imports"),
        ("core.resolver", "core.handler", "depends_on"),
        ("core.handler", "core.resolver", "depends_on"),
        ("svc.billing", "svc.orders", "depends_on"),
        ("svc.orders", "svc.billing", "imports"),
    ]

    for svc in list(service_modules)[18:25]:
        edges.append((svc, "core.engine", "depends_on"))
        edges.append((svc, "core.config_base", "depends_on"))
        edges.append((svc, "util.logging", "imports"))

    for model in list(data_modules)[12:18]:
        edges.append((model, "data.connection_pool", "depends_on"))

    edges += [
        ("svc.sessions", "data.models_session", "imports"),
        ("svc.sessions", "core.cache_base", "depends_on"),
        ("svc.sessions", "cfg.app", "configures"),
        ("svc.tenants", "data.models_user", "imports"),
        ("svc.tenants", "cfg.tenant", "configures"),
        ("svc.webhooks", "core.emitter", "depends_on"),
        ("svc.webhooks", "cfg.endpoints", "configures"),
    ]

    for cfg in list(config_modules)[:8]:
        edges.append((cfg, "core.config_base", "implements"))

    seen = set()
    unique_edges = []
    for src, tgt, label in edges:
        key = (src, tgt, label)
        if key not in seen:
            seen.add(key)
            unique_edges.append((src, tgt, label))

    for src, tgt, label in unique_edges:
        mem.relate(src, tgt, label=label)

    print(f"  {mem.graph.node_count} nodes, {mem.graph.edge_count} edges")
    print()

    # =====================================================================
    # SECTION 3: Centrality Analysis
    # =====================================================================

    print("=" * 70)
    print("SECTION 3: Most Critical Modules (Centrality)")
    print("=" * 70)

    degree = mem.degree_centrality_labels()
    betweenness = mem.betweenness_centrality_labels()

    combined = {}
    for label in all_modules:
        d = degree.get(label, 0.0)
        b = betweenness.get(label, 0.0)
        combined[label] = d * 0.4 + b * 0.6

    print("  Top 10 critical modules (degree + betweenness):")
    print(f"  {'Module':<35s} {'Degree':>8s} {'Between':>8s} {'Score':>8s}")
    print("  " + "-" * 63)
    for label, score in sorted(combined.items(), key=lambda x: -x[1])[:10]:
        d = degree.get(label, 0.0)
        b = betweenness.get(label, 0.0)
        print(f"  {label:<35s} {d:8.3f} {b:8.3f} {score:8.3f}")
    print()

    # =====================================================================
    # SECTION 4: Circular Dependencies
    # =====================================================================

    print("=" * 70)
    print("SECTION 4: Circular Dependencies")
    print("=" * 70)

    cycles = mem.detect_cycles_labels(max_cycles=10)
    if cycles:
        print(f"  Found {len(cycles)} circular dependency chains:")
        for i, cycle in enumerate(cycles, 1):
            print(f"    Cycle {i}: {' -> '.join(cycle)} -> {cycle[0]}")
    else:
        print("  No circular dependencies detected")
    print()

    # =====================================================================
    # SECTION 5: Blast Radius Analysis
    # =====================================================================

    print("=" * 70)
    print("SECTION 5: Blast Radius of Core Modules")
    print("=" * 70)

    blast_targets = [
        "core.engine", "core.config_base", "core.auth_base",
        "core.event_bus", "core.cache_base", "util.logging",
    ]

    for target in blast_targets:
        neighborhood = mem.query(target, strategy="bfs", max_depth=6, max_nodes=200)
        affected = [n.label for n in neighborhood if n.label != target and n.data.get("category") != "test"]
        print(f"  {target}: blast radius = {len(affected)} modules")
        if len(affected) <= 12:
            print(f"    Affected: {sorted(affected)}")
    print()

    # =====================================================================
    # SECTION 6: Transitive Dependency Discovery
    # =====================================================================

    print("=" * 70)
    print("SECTION 6: Transitive Dependency Discovery")
    print("=" * 70)

    mem.add_rules(TransitiveRule(edge_label="depends_on", new_label="indirectly_depends_on"))
    chain_seeds = {"core.engine", "core.registry", "core.resolver",
                   "core.config_base", "core.logging_base",
                   "core.auth_base", "core.crypto"}
    result = mem.reason(
        seed_concepts=chain_seeds,
        max_depth=3,
        max_total_states=50,
    )
    new_count = sum(1 for e in mem.graph.edges if e.label == "indirectly_depends_on")
    expansion = result.get("expansion", {})
    print(f"  TransitiveRule applied: {new_count} indirect dependencies discovered")
    print(f"  Multiway states explored: {expansion.get('states_created', 0)}")
    print(f"  Rules applied: {expansion.get('rules_applied', 0)}")
    if new_count > 0:
        sample = [le for le in mem.graph.labeled_edges if le["label"] == "indirectly_depends_on"][:5]
        for le in sample:
            s = le["source_labels"][0] if le["source_labels"] else "?"
            t = le["target_labels"][0] if le["target_labels"] else "?"
            print(f"    {s} -> {t}")
    print()

    # =====================================================================
    # SECTION 7: Outdated Third-Party Dependencies
    # =====================================================================

    print("=" * 70)
    print("SECTION 7: Outdated Third-Party Dependencies")
    print("=" * 70)

    current_year = 2026
    print("  Packages not updated in 2+ years:")
    outdated = []
    for label, data in third_party.items():
        age = current_year - data["last_updated"]
        if age >= 2:
            outdated.append((label, data))
            deps_count = sum(
                1 for le in mem.graph.labeled_edges
                if le["label"] in ("depends_on", "imports")
                and label in le["target_labels"]
            )
            print(f"    {label:<20s} version={data['version']:<8s} "
                  f"last_updated={data['last_updated']}  "
                  f"age={age}yr  dependents={deps_count}  "
                  f"pinned={data['is_pinned']}")
    if not outdated:
        print("    (none)")
    print()

    # =====================================================================
    # SECTION 8: Test Coverage Gaps
    # =====================================================================

    print("=" * 70)
    print("SECTION 8: Test Coverage Risk Analysis")
    print("=" * 70)

    print("  Modules with low test coverage AND many dependents:")
    at_risk = []
    for label, data in all_modules.items():
        tc = data.get("test_coverage", 1.0)
        if tc > 0.7:
            continue
        neighborhood = mem.query(label, strategy="bfs", max_depth=3, max_nodes=50)
        dep_count = len([n for n in neighborhood if n.label != label])
        if dep_count >= 3:
            at_risk.append((label, tc, dep_count))

    at_risk.sort(key=lambda x: x[1])
    for label, tc, deps in at_risk[:10]:
        print(f"    {label:<35s} coverage={tc:.0%}  dependents={deps}")
    print()

    # =====================================================================
    # SECTION 9: Subsystem Coupling Analysis
    # =====================================================================

    print("=" * 70)
    print("SECTION 9: Subsystem Coupling Analysis")
    print("=" * 70)

    subsystems = {
        "core": [l for l, d in core_modules.items()],
        "services": [l for l, d in service_modules.items()],
        "data": [l for l, d in data_modules.items()],
        "third_party": [l for l, d in third_party.items()],
        "config": [l for l, d in config_modules.items()],
        "shared": [l for l, d in shared_utils.items()],
        "test": [l for l, d in test_modules.items()],
    }

    print("  Cross-subsystem dependency matrix:")
    header = "  " + "".join(f"{k:>12s}" for k in subsystems if k != "test")
    print(header)
    print("  " + "-" * (len(header) - 2))

    for src_sub, src_labels in subsystems.items():
        if src_sub == "test":
            continue
        row = f"  {src_sub:<10s}"
        for tgt_sub, tgt_labels in subsystems.items():
            if tgt_sub == "test":
                continue
            count = 0
            for e in mem.graph.labeled_edges:
                if e["label"] not in ("depends_on", "imports", "extends"):
                    continue
                if (e["source_labels"] and e["target_labels"]
                        and e["source_labels"][0] in src_labels
                        and e["target_labels"][0] in tgt_labels):
                    count += 1
            row += f"{count:>12d}"
        print(row)
    print()

    # =====================================================================
    # SECTION 10: Summary
    # =====================================================================

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    stats = mem.stats()
    print(f"  Graph: {stats['nodes']} nodes, {stats['edges']} edges")
    print(f"  Circular dependencies: {len(cycles)} cycles")
    print(f"  Connected components: {stats['components']}")
    print(f"  Indirect dependencies found: {new_count}")
    print(f"  Outdated packages: {len(outdated)}")
    print(f"  Low-coverage at-risk modules: {len(at_risk)}")
    print()

    top = sorted(combined.items(), key=lambda x: -x[1])[0]
    print(f"  Highest-risk module: {top[0]} (criticality={top[1]:.3f})")
    blast = mem.query(top[0], strategy="bfs", max_depth=6, max_nodes=200)
    blast_count = len([n for n in blast if n.label != top[0] and n.data.get("category") != "test"])
    print(f"  Its blast radius: {blast_count} modules affected by a change")
    print()


if __name__ == "__main__":
    main()
