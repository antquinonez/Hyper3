from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any

from hyper3.community import CommunityResult
from hyper3.results import ActivationHit, SearchHit

if TYPE_CHECKING:
    from hyper3.memory import HypergraphMemory


class ConceptSet:
    """A scored set of concept labels supporting chainable exploration.

    Created via ``mem.find()``. Every selector and expander method returns
    another ConceptSet, enabling fluent multi-step workflows:

        results = (mem.find("cancer")
            .neighbors()
            .similar(top_k=10)
            .top(5)
            .labels)

    ConceptSet delegates to the existing namespace methods on HypergraphMemory.
    It does not hold graph state — it is a lens into the graph.
    """

    def __init__(
        self,
        mem: HypergraphMemory,
        items: list[tuple[str, float]] | None = None,
    ) -> None:
        """Initialize with a HypergraphMemory reference and optional scored items."""
        self._mem = mem
        self._items: list[tuple[str, float]] = items or []

    # -- Terminal: extract results ------------------------------------------

    @property
    def labels(self) -> list[str]:
        """Concept labels in score order (no duplicates)."""
        seen: set[str] = set()
        result: list[str] = []
        for label, _ in self._items:
            if label not in seen:
                seen.add(label)
                result.append(label)
        return result

    @property
    def scores(self) -> dict[str, float]:
        """Best score for each concept label."""
        result: dict[str, float] = {}
        for label, score in self._items:
            if label not in result or score > result[label]:
                result[label] = score
        return result

    @property
    def items(self) -> list[tuple[str, float]]:
        """All (label, score) pairs in insertion order."""
        return list(self._items)

    def __len__(self) -> int:
        """Return the number of unique concept labels."""
        return len(self.labels)

    def __iter__(self) -> Iterator[str]:
        """Iterate over unique concept labels in score order."""
        return iter(self.labels)

    def __contains__(self, label: object) -> bool:
        """Check whether a label is present in the set."""
        if not isinstance(label, str):
            return False
        return any(l == label for l, _ in self._items)

    def __repr__(self) -> str:
        """Return a concise string representation with concept count and preview."""
        n = len(self)
        preview = self.labels[:5]
        return f"ConceptSet({n} concepts{f': {preview}...' if n > 5 else ''})"

    # -- Selectors (narrow the set) -----------------------------------------

    def top(self, k: int) -> ConceptSet:
        """Keep only the top-k concepts by score.

        Args:
            k: Maximum number of concepts to keep.

        Returns:
            New ConceptSet with at most k concepts.
        """
        best = self._deduplicated()
        return ConceptSet(self._mem, best[:k])

    def filter(self, fn: Callable[[str, float], bool]) -> ConceptSet:
        """Filter concepts by a predicate on (label, score).

        Args:
            fn: Predicate receiving (label, score), returning True to keep.

        Returns:
            New ConceptSet with concepts passing the predicate.
        """
        return ConceptSet(self._mem, [(l, s) for l, s in self._items if fn(l, s)])

    def threshold(self, min_score: float) -> ConceptSet:
        """Drop concepts with score below min_score.

        Args:
            min_score: Minimum score to retain.

        Returns:
            New ConceptSet filtered by score.
        """
        return self.filter(lambda _, s: s >= min_score)

    def exclude(self, *labels: str) -> ConceptSet:
        """Remove specific concept labels.

        Args:
            labels: Labels to exclude.

        Returns:
            New ConceptSet without the specified labels.
        """
        exclude_set = set(labels)
        return self.filter(lambda l, _: l not in exclude_set)

    def unique(self) -> ConceptSet:
        """Remove duplicate labels, keeping the highest score.

        Returns:
            New ConceptSet with unique labels.
        """
        return ConceptSet(self._mem, self._deduplicated())

    # -- Expanders (grow the set, return ConceptSet) ------------------------

    def neighbors(self, *, edge_label: str | None = None,
                  direction: str = "any") -> ConceptSet:
        """Expand to neighbors of all concepts in the set.

        Delegates to ``mem.neighbors()`` for each label.

        Args:
            edge_label: Filter by edge label. None = all edges.
            direction: ``"out"``, ``"in"``, or ``"any"``.

        Returns:
            New ConceptSet containing the neighbors.
        """
        all_items: list[tuple[str, float]] = []
        for label in self.labels:
            nbrs = self._mem.neighbors(label, edge_label=edge_label, direction=direction)
            all_items.extend((nbr, 1.0) for nbr in nbrs)
        return ConceptSet(self._mem, all_items)

    def similar(self, *, top_k: int = 10,
                threshold: float | None = None) -> ConceptSet:
        """Find concepts similar to each concept in the set.

        Delegates to ``mem.search.similar()`` for each label.

        Args:
            top_k: Maximum similar concepts per label.
            threshold: Minimum similarity score.

        Returns:
            New ConceptSet of similar concepts with similarity scores.
        """
        all_items: list[tuple[str, float]] = []
        for label in self.labels:
            hits: list[SearchHit] = self._mem.search.similar(
                label, top_k=top_k, threshold=threshold)
            all_items.extend((hit.label, hit.score) for hit in hits)
        return ConceptSet(self._mem, all_items)

    def activate(self, *, energy: float = 1.0,
                  top_k: int = 10) -> ConceptSet:
        """Spread activation from each concept in the set.

        Delegates to ``mem.search.activate()`` for each label.

        Args:
            energy: Initial activation energy.
            top_k: Maximum activated concepts per label.

        Returns:
            New ConceptSet of activated concepts with energy scores.
        """
        all_items: list[tuple[str, float]] = []
        for label in self.labels:
            hits: list[ActivationHit] = self._mem.search.activate(
                label, energy=energy, top_k=top_k)
            all_items.extend((hit.label, hit.energy) for hit in hits)
        return ConceptSet(self._mem, all_items)

    def query(self, *, top_k: int = 10,
              use_ltr: bool = False) -> ConceptSet:
        """Retrieve concepts related to each concept in the set.

        Delegates to ``mem.search.query()`` for each label.

        Args:
            top_k: Maximum results per label.
            use_ltr: Apply learned relevance scoring.

        Returns:
            New ConceptSet of retrieved concepts with relevance scores.
        """
        all_items: list[tuple[str, float]] = []
        for label in self.labels:
            hits: list[SearchHit] = self._mem.search.query(
                label, top_k=top_k, use_ltr=use_ltr)
            all_items.extend((hit.label, hit.score) for hit in hits)
        return ConceptSet(self._mem, all_items)

    def diffuse(self, *, energy: float = 1.0, mode: str = "linear",
                iterations: int | None = None) -> ConceptSet:
        """Spread activation across hyperedge boundaries.

        Delegates to ``mem.search.diffuse()`` for each label.

        Args:
            energy: Initial activation energy.
            mode: Diffusion mode (``"linear"``, ``"exponential"``).
            iterations: Number of diffusion steps.

        Returns:
            New ConceptSet of activated concepts with energy scores.
        """
        all_items: list[tuple[str, float]] = []
        for label in self.labels:
            hits: list[ActivationHit] = self._mem.search.diffuse(
                label, energy=energy, mode=mode, iterations=iterations)
            all_items.extend((hit.label, hit.energy) for hit in hits)
        return ConceptSet(self._mem, all_items)

    def paths_to(self, target: str, *, label: str | None = None,
                  max_depth: int = 5, max_paths: int = 10) -> ConceptSet:
        """Find paths from each concept to a target.

        Delegates to ``mem.analyze.paths()`` for each label.

        Args:
            target: Target concept label.
            label: Filter edges by label.
            max_depth: Maximum path length.
            max_paths: Maximum paths per source.

        Returns:
            New ConceptSet of all concepts appearing in any path.
        """
        all_items: list[tuple[str, float]] = []
        for source in self.labels:
            paths = self._mem.analyze.paths(
                source, target, label=label,
                max_depth=max_depth, max_paths=max_paths)
            for path in paths:
                depth = len(path)
                all_items.extend((c, 1.0 / depth if depth > 0 else 1.0) for c in path)
        return ConceptSet(self._mem, all_items)

    # -- Analysis methods ---------------------------------------------------

    def centrality(self, method: str, **kwargs: Any) -> ConceptSet:
        """Compute centrality scores for concepts in the set.

        Delegates to ``mem.analyze.centrality()``.

        Args:
            method: Centrality method name (e.g. ``"pagerank"``).
            **kwargs: Additional arguments for the centrality algorithm.

        Returns:
            New ConceptSet scored by centrality.
        """
        full = self._mem.analyze.centrality(method, **kwargs)
        if not isinstance(full, dict):
            full = {}
        items = [(l, s) for l, s in full.items() if l in self.labels]
        return ConceptSet(self._mem, items)

    def communities(self, **kwargs: Any) -> CommunityResult:
        """Detect communities in the graph.

        This is a terminal operation — it returns CommunityResult, not ConceptSet.
        Community detection operates on the full graph structure, not restricted
        to the concepts in this set.

        Args:
            **kwargs: Arguments passed to ``mem.analyze.communities()``.

        Returns:
            CommunityResult with community assignments.
        """
        return self._mem.analyze.communities(**kwargs)

    def anomalies(self, **kwargs: Any) -> list[Any]:
        """Detect structural anomalies for each concept in the set.

        This is a terminal operation.

        Args:
            **kwargs: Arguments passed to ``mem.analyze.anomalies()``.

        Returns:
            List of anomaly detection results.
        """
        results = []
        for label in self.labels:
            result = self._mem.analyze.anomalies(label, **kwargs)
            results.append(result)
        return results

    def describe(self) -> Any:
        """Generate a description of the subgraph induced by these concepts.

        This is a terminal operation.

        Returns:
            GraphDescription result.
        """
        return self._mem.analyze.subgraph(set(self.labels))

    # -- Mutation methods ---------------------------------------------------

    def link_to(self, target: str | ConceptSet, *, label: str = "",
                weight: float = 1.0) -> int:
        """Link all concepts in the set to a target.

        Args:
            target: Target label or ConceptSet. If ConceptSet, links to
                each of its members.
            label: Edge label.
            weight: Edge weight.

        Returns:
            Number of edges created.
        """
        targets = target.labels if isinstance(target, ConceptSet) else [target]
        count = 0
        for src in self.labels:
            for tgt in targets:
                if src != tgt:
                    self._mem.link(src, tgt, label=label, weight=weight)
                    count += 1
        return count

    def link_all(self, *, label: str = "", weight: float = 1.0) -> int:
        """Link all concepts in the set to each other pairwise.

        Args:
            label: Edge label.
            weight: Edge weight.

        Returns:
            Number of edges created.
        """
        labels = self.labels
        count = 0
        for i, src in enumerate(labels):
            for tgt in labels[i + 1:]:
                self._mem.link(src, tgt, label=label, weight=weight)
                count += 1
        return count

    def add_data(self, **kwargs: Any) -> int:
        """Set data fields on all concepts in the set.

        Args:
            **kwargs: Key-value pairs to merge into each node's data dict.

        Returns:
            Number of nodes updated.
        """
        count = 0
        for label in self.labels:
            self._mem.set(label, **kwargs)
            count += 1
        return count

    # -- Internal helpers ---------------------------------------------------

    def _deduplicated(self) -> list[tuple[str, float]]:
        """Return items deduplicated by label, keeping highest score, sorted descending."""
        best: dict[str, float] = {}
        for label, score in self._items:
            if label not in best or score > best[label]:
                best[label] = score
        return sorted(best.items(), key=lambda x: -x[1])
