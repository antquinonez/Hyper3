from __future__ import annotations

from enum import Enum


class CapabilityLevel(Enum):
    MINIMAL = "minimal"
    STANDARD = "standard"
    ENHANCED = "enhanced"
    FULL = "full"


def _probe_graph(memory: object) -> bool:
    """Return ``True`` when the memory has a non-empty graph."""
    graph = getattr(memory, "_graph", None)
    if graph is None:
        return False
    try:
        return len(getattr(graph, "nodes", [])) > 0
    except Exception:
        return False


def _probe_rules(memory: object) -> bool:
    """Return ``True`` when rules exist and at least one produces matches."""
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
    """Return ``True`` when the multiway engine has expanded states."""
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
    """Return ``True`` when provenance records exist."""
    prov = getattr(memory, "_provenance", None)
    if prov is None:
        return False
    try:
        return len(getattr(prov, "_records", {})) > 0
    except Exception:
        return False


def _probe_belief(memory: object) -> bool:
    """Return ``True`` when belief states have been created."""
    belief = getattr(memory, "_belief", None)
    if belief is None:
        return False
    try:
        states = getattr(belief, "_states", {})
        return len(states) > 0
    except Exception:
        return False


def _probe_branchial(memory: object) -> bool:
    """Return ``True`` when branchial coordinates have been assigned."""
    branchial = getattr(memory, "_branchial", None)
    if branchial is None:
        return False
    try:
        return len(getattr(branchial, "_coordinates", {})) > 0
    except Exception:
        return False


def _probe_rulial(memory: object) -> bool:
    """Return ``True`` when the rulial space has position history."""
    rulial = getattr(memory, "_rulial", None)
    if rulial is None:
        return False
    try:
        history = getattr(rulial, "_position_history", [])
        return len(history) > 0
    except Exception:
        return False


def _probe_embedding(memory: object) -> bool:
    """Return ``True`` when the embedding engine has cached vectors."""
    engine = getattr(memory, "_embedding_engine", None)
    if engine is None:
        return False
    try:
        return len(getattr(engine, "_cache", {})) > 0
    except Exception:
        return False


def _probe_retrieval(memory: object) -> bool:
    """Return ``True`` when the retrieval engine has recorded feedback."""
    retrieval = getattr(memory, "_retrieval", None)
    if retrieval is None:
        return False
    try:
        feedback = getattr(retrieval, "_feedback", None)
        if feedback is None:
            return False
        size_val = getattr(feedback, "size", 0)
        if callable(size_val):
            sz = size_val()
            return int(sz) > 0  # type: ignore[arg-type]
        return int(size_val) > 0  # type: ignore[arg-type]
    except Exception:
        return False


def _compute_capability_score(memory: object) -> dict[str, float]:
    """Run all probes and return a dict mapping feature names to 0/1 scores."""
    probes = {
        "graph": _probe_graph,
        "rules": _probe_rules,
        "multiway": _probe_multiway,
        "provenance": _probe_provenance,
        "belief": _probe_belief,
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
                total_edges = sum(len(list(getattr(graph, "incident_edges", lambda x: [])(n.id))) for n in nodes)
                density = total_edges / max(len(nodes) * (len(nodes) - 1), 1)
                scores["graph_density"] = min(density, 1.0)
            else:
                scores["graph_density"] = 0.0
        except Exception:
            scores["graph_density"] = 0.0

        try:
            belief = getattr(memory, "_belief", None)
            if belief is not None:
                states = getattr(belief, "_states", {})
                active = sum(1 for s in states.values() if not getattr(s, "resolved", True))
                scores["belief_active_ratio"] = active / max(len(states), 1)
            else:
                scores["belief_active_ratio"] = 0.0
        except Exception:
            scores["belief_active_ratio"] = 0.0
    else:
        scores["graph_density"] = 0.0
        scores["belief_active_ratio"] = 0.0

    return scores


def detect_capability_level(memory: object) -> CapabilityLevel:
    """Classify the memory's capability level based on subsystem probe scores.

    Args:
        memory: A ``HypergraphMemory`` instance (typed as ``object`` to avoid
            circular imports).

    Returns:
        The detected :class:`CapabilityLevel`.
    """
    scores = _compute_capability_score(memory)

    core = scores.get("graph", 0) + scores.get("rules", 0)
    if core < 1.0:
        return CapabilityLevel.MINIMAL

    if scores.get("multiway", 0) == 0:
        return CapabilityLevel.MINIMAL

    advanced = (
        scores.get("provenance", 0) + scores.get("belief", 0) + scores.get("branchial", 0) + scores.get("rulial", 0)
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
    """Decorator that gates a method on a minimum capability level.

    Calls :func:`detect_capability_level` on ``self`` at runtime and
    raises :class:`~hyper3.exceptions.Hyper3Error` if the current level
    is below the required one.  Uses ``functools.wraps`` to preserve
    the decorated function's name, docstring, and module.
    """
    import functools

    def decorator(func):
        """Wrap *func* so the capability check runs before each call."""

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            """Invoke the decorated method after verifying capability level."""
            current = detect_capability_level(self)
            levels = list(CapabilityLevel)
            current_idx = levels.index(current)
            required_idx = levels.index(level)
            if current_idx < required_idx:
                from hyper3.exceptions import Hyper3Error

                raise Hyper3Error(f"requires {level.value} capability, current: {current.value}")
            return func(self, *args, **kwargs)

        return wrapper

    return decorator
