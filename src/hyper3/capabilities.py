from __future__ import annotations

from enum import Enum
from typing import Any


class CapabilityLevel(Enum):
    MINIMAL = "minimal"
    STANDARD = "standard"
    ENHANCED = "enhanced"
    FULL = "full"


def _probe_graph(memory: object) -> bool:
    graph = getattr(memory, "_graph", None)
    if graph is None:
        return False
    try:
        return len(getattr(graph, "nodes", [])) > 0
    except Exception:
        return False


def _probe_rules(memory: object) -> bool:
    rules = getattr(memory, "_rules", None)
    if not rules:
        return False
    graph = getattr(memory, "_graph", None)
    if graph is None:
        return False
    try:
        nodes = getattr(graph, "nodes", [])
        if not nodes:
            return bool(rules)
        active = frozenset(n.id for n in nodes[:3])
        for rule in rules:
            matches = rule.find_matches(graph, active)
            if matches:
                return True
        return False
    except Exception:
        return bool(rules)


def _probe_multiway(memory: object) -> bool:
    engine = getattr(memory, "_multiway_engine", None)
    if engine is None:
        return False
    try:
        multiway = getattr(engine, "multiway", None)
        if multiway is None:
            return False
        states = getattr(multiway, "_states", {})
        return len(states) > 0
    except Exception:
        return False


def _probe_provenance(memory: object) -> bool:
    prov = getattr(memory, "_provenance", None)
    if prov is None:
        return False
    try:
        return len(getattr(prov, "_records", {})) > 0
    except Exception:
        return False


def _probe_quantum(memory: object) -> bool:
    quantum = getattr(memory, "_quantum", None)
    if quantum is None:
        return False
    try:
        states = getattr(quantum, "_states", {})
        return len(states) > 0
    except Exception:
        return False


def _probe_branchial(memory: object) -> bool:
    branchial = getattr(memory, "_branchial", None)
    if branchial is None:
        return False
    try:
        return len(getattr(branchial, "_coordinates", {})) > 0
    except Exception:
        return False


def _probe_rulial(memory: object) -> bool:
    rulial = getattr(memory, "_rulial", None)
    if rulial is None:
        return False
    try:
        history = getattr(rulial, "_position_history", [])
        return len(history) > 0
    except Exception:
        return False


def _probe_embedding(memory: object) -> bool:
    engine = getattr(memory, "_embedding_engine", None)
    if engine is None:
        return False
    try:
        return len(getattr(engine, "_cache", {})) > 0
    except Exception:
        return False


def _probe_retrieval(memory: object) -> bool:
    retrieval = getattr(memory, "_retrieval", None)
    if retrieval is None:
        return False
    try:
        feedback = getattr(retrieval, "_feedback", None)
        if feedback is None:
            return False
        return getattr(feedback, "size", lambda: 0)() > 0
    except Exception:
        return False


def _compute_capability_score(memory: object) -> dict[str, float]:
    probes = {
        "graph": _probe_graph,
        "rules": _probe_rules,
        "multiway": _probe_multiway,
        "provenance": _probe_provenance,
        "quantum": _probe_quantum,
        "branchial": _probe_branchial,
        "rulial": _probe_rulial,
        "embedding": _probe_embedding,
        "retrieval": _probe_retrieval,
    }
    scores: dict[str, float] = {}
    for name, probe_fn in probes.items():
        try:
            scores[name] = 1.0 if probe_fn(memory) else 0.0
        except Exception:
            scores[name] = 0.0

    graph = getattr(memory, "_graph", None)
    if graph is not None:
        try:
            nodes = list(getattr(graph, "nodes", []))
            if nodes:
                total_edges = sum(
                    len(list(getattr(graph, "edges_for", lambda x: [])(n.id)))
                    for n in nodes
                )
                density = total_edges / max(len(nodes) * (len(nodes) - 1), 1)
                scores["graph_density"] = min(density, 1.0)
            else:
                scores["graph_density"] = 0.0
        except Exception:
            scores["graph_density"] = 0.0

        try:
            quantum = getattr(memory, "_quantum", None)
            if quantum is not None:
                states = getattr(quantum, "_states", {})
                active = sum(
                    1 for s in states.values()
                    if not getattr(s, "collapsed", True)
                )
                scores["quantum_active_ratio"] = active / max(len(states), 1)
            else:
                scores["quantum_active_ratio"] = 0.0
        except Exception:
            scores["quantum_active_ratio"] = 0.0
    else:
        scores["graph_density"] = 0.0
        scores["quantum_active_ratio"] = 0.0

    return scores


def detect_capability_level(memory: object) -> CapabilityLevel:
    scores = _compute_capability_score(memory)

    core = scores.get("graph", 0) + scores.get("rules", 0)
    if core < 1.0:
        return CapabilityLevel.MINIMAL

    if scores.get("multiway", 0) == 0:
        return CapabilityLevel.MINIMAL

    advanced = (
        scores.get("provenance", 0)
        + scores.get("quantum", 0)
        + scores.get("branchial", 0)
        + scores.get("rulial", 0)
    )
    if advanced < 2.0:
        return CapabilityLevel.STANDARD
    if advanced < 4.0:
        return CapabilityLevel.ENHANCED

    full = scores.get("embedding", 0) + scores.get("retrieval", 0)
    if full < 1.5:
        return CapabilityLevel.ENHANCED
    return CapabilityLevel.FULL


def require_capability(level: CapabilityLevel):
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            current = detect_capability_level(self)
            levels = list(CapabilityLevel)
            current_idx = levels.index(current)
            required_idx = levels.index(level)
            if current_idx < required_idx:
                from hyper3.exceptions import Hyper3Error
                raise Hyper3Error(
                    f"requires {level.value} capability, current: {current.value}"
                )
            return func(self, *args, **kwargs)
        return wrapper
    return decorator
