from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Modality(Enum):
    """Information modality used to tag hypernodes and hyperedges (textual, conceptual, temporal, causal, sensory, abstract)."""

    TEXTUAL = "textual"
    CONCEPTUAL = "conceptual"
    TEMPORAL = "temporal"
    CAUSAL = "convergence"
    SENSORY = "sensory"
    ABSTRACT = "abstract"


class AbstractionLayer(Enum):
    """Abstraction level of a node or edge in the knowledge hierarchy (detail, intermediate, summary)."""

    DETAIL = "detail"
    INTERMEDIATE = "intermediate"
    SUMMARY = "summary"


@dataclass
class Metadata:
    """Auxiliary metadata for hypernodes and hyperedges: temporal tags, modality tags, abstraction layer, and custom key-value pairs."""

    temporal_tags: dict[str, Any] = field(default_factory=dict)
    modality_tags: set[Modality] = field(default_factory=set)
    abstraction_layer: AbstractionLayer = AbstractionLayer.INTERMEDIATE
    custom: dict[str, Any] = field(default_factory=dict)


@dataclass
class Hypernode:
    """A vertex in the hypergraph carrying a label, arbitrary data payload, access statistics, weight, and metadata."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    label: str = ""
    data: Any = None
    metadata: Metadata = field(default_factory=Metadata)
    access_count: int = 0
    created_at: float = 0.0
    last_accessed: float = 0.0
    weight: float = 1.0

    def touch(self, now: float) -> None:
        """Record an access by incrementing the counter and updating the timestamp."""
        self.access_count += 1
        self.last_accessed = now

    @property
    def is_active(self) -> bool:
        """Whether this node has been accessed at least once."""
        return self.access_count > 0

    def matches(self, other: Hypernode) -> float:
        """Compute a similarity score in [0, 1] against another node's data.

        For dict data, returns the fraction of shared keys with matching values.
        For scalar types, returns 1.0 on exact equality and 0.0 otherwise.

        Args:
            other: The node to compare against.

        Returns:
            Similarity score between 0.0 and 1.0.
        """
        if self.data is None or other.data is None:
            return 0.0
        if self.data == other.data:
            return 1.0
        if isinstance(self.data, (str, int, float, bool)) and self.data == other.data:
            return 1.0
        if isinstance(self.data, dict) and isinstance(other.data, dict):
            shared = set(self.data.keys()) & set(other.data.keys())
            if not shared:
                return 0.0
            matches = sum(1 for k in shared if self.data[k] == other.data[k])
            return matches / len(shared)
        return 0.0


@dataclass
class Hyperedge:
    """A directed hyperedge connecting a frozenset of source node IDs to a frozenset of target node IDs, with a semantic label, weight, and metadata."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_ids: frozenset[str] = field(default_factory=frozenset)
    target_ids: frozenset[str] = field(default_factory=frozenset)
    label: str = ""
    data: Any = None
    metadata: Metadata = field(default_factory=Metadata)
    weight: float = 1.0
    _node_ids_cache: frozenset[str] | None = field(default=None, repr=False)

    @property
    def node_ids(self) -> frozenset[str]:
        """Union of source and target node IDs. Cached after first access."""
        cached = self._node_ids_cache
        if cached is None:
            cached = self.source_ids | self.target_ids
            object.__setattr__(self, '_node_ids_cache', cached)
        return cached
