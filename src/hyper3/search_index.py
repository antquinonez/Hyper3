"""Inverted indexes for attribute-based node lookup on a Hypergraph.

Provides exact-match, range, multi-value, and full-text lookup over node
data fields, plus autocomplete-style value suggestions.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from typing import Any

from hyper3.kernel import Hypergraph


class AttributeIndex:
    """Maintains inverted indexes over node data fields for fast filtering.

    Three index structures are kept in sync with the underlying graph:

    * **exact index** — maps ``(field, value)`` to the set of node IDs whose
      ``data[field] == value``.
    * **range index** — sorted ``(numeric_value, node_id)`` pairs per field,
      enabling bisection-based range queries.
    * **text index** — maps lowercased tokens to node IDs for full-text
      intersection queries.

    The index is marked dirty on creation and must be explicitly rebuilt via
    ``build()`` after graph mutations.

    Args:
        indexed_fields: If provided, only these field names are indexed.
            ``None`` indexes every field found in node data.
    """

    def __init__(self, indexed_fields: set[str] | None = None) -> None:
        """Initialize the attribute index.

        Args:
            indexed_fields: Set of field names to index. None indexes all fields.
        """
        self._index: dict[str, dict[str, set[str]]] = {}
        self._range_index: dict[str, list[tuple[float, str]]] = {}
        self._text_index: dict[str, dict[str, set[str]]] = {}
        self._indexed_fields = indexed_fields
        self._dirty = True
        self._value_registry: dict[str, set[str]] = {}

    @property
    def dirty(self) -> bool:
        """Whether the index is out-of-date relative to the graph."""
        return self._dirty

    def mark_dirty(self) -> None:
        """Flag the index as needing a rebuild."""
        self._dirty = True

    def build(self, graph: Hypergraph) -> None:
        """Rebuild all indexes from the current graph state.

        Clears existing entries and re-indexes every node whose ``data`` is a
        dict.  Range indexes are sorted on completion.

        Args:
            graph: The hypergraph whose nodes to index.
        """
        self._index.clear()
        self._range_index.clear()
        self._text_index.clear()
        self._value_registry.clear()
        for node in graph.nodes:
            if not isinstance(node.data, dict):
                continue
            for field, value in node.data.items():
                if self._indexed_fields is not None and field not in self._indexed_fields:
                    continue
                self._index_entry(node.id, field, value)
        for entries in self._range_index.values():
            entries.sort(key=lambda x: x[0])
        self._dirty = False

    def _index_entry(self, node_id: str, field: str, value: Any) -> None:
        """Add a single field value for a node into all applicable indexes.

        Booleans and numerics are stored in the exact index (as strings) and
        numerics are additionally added to the range index.  Strings are stored
        in the exact index and tokenised into the text index.

        Args:
            node_id: Internal ID of the node.
            field: Data field name.
            value: The field value to index.
        """
        if isinstance(value, bool):
            str_val = str(value)
            self._index.setdefault(field, {}).setdefault(str_val, set()).add(node_id)
            self._value_registry.setdefault(field, set()).add(str_val)
            return
        if isinstance(value, (int, float)):
            str_val = str(value)
            self._index.setdefault(field, {}).setdefault(str_val, set()).add(node_id)
            self._value_registry.setdefault(field, set()).add(str_val)
            self._range_index.setdefault(field, []).append((float(value), node_id))
            return
        if isinstance(value, str):
            self._index.setdefault(field, {}).setdefault(value, set()).add(node_id)
            self._value_registry.setdefault(field, set()).add(value)
            for token in value.lower().split():
                self._text_index.setdefault(field, {}).setdefault(token, set()).add(node_id)

    def lookup(self, field: str, value: Any) -> set[str]:
        """Return node IDs whose ``data[field]`` exactly matches *value*.

        Args:
            field: Data field name.
            value: Value to match.  Non-string values are coerced via ``str()``.

        Returns:
            Set of matching node IDs (empty if no matches).
        """
        str_val = str(value) if not isinstance(value, str) else value
        return set(self._index.get(field, {}).get(str_val, set()))

    def lookup_range(self, field: str, min_val: float | None = None, max_val: float | None = None) -> set[str]:
        """Return node IDs whose numeric ``data[field]`` falls within a range.

        Uses bisection on the sorted range index for O(log n) lookups.

        Args:
            field: Data field name.
            min_val: Inclusive lower bound.  ``None`` means no lower bound.
            max_val: Inclusive upper bound.  ``None`` means no upper bound.

        Returns:
            Set of matching node IDs.
        """
        entries = self._range_index.get(field, [])
        if not entries:
            return set()
        lo = bisect_left(entries, (min_val, "")) if min_val is not None else 0
        hi = bisect_right(entries, (max_val, "\uffff")) if max_val is not None else len(entries)
        return {node_id for _, node_id in entries[lo:hi]}

    def lookup_multi(self, field: str, values: list[Any]) -> set[str]:
        """Return node IDs whose ``data[field]`` matches any of the given values.

        Args:
            field: Data field name.
            values: List of values to match (OR semantics).

        Returns:
            Union of all matching node IDs.
        """
        result: set[str] = set()
        for v in values:
            result |= self.lookup(field, v)
        return result

    def lookup_text(self, field: str, tokens: list[str]) -> set[str]:
        """Return node IDs whose string ``data[field]`` contains all tokens.

        Tokens are matched case-insensitively against the text index.  All
        tokens must be present (AND semantics).

        Args:
            field: Data field name.
            tokens: List of search tokens.

        Returns:
            Intersection of node IDs matching every token.
        """
        if not tokens:
            return set()
        field_index = self._text_index.get(field, {})
        sets = [field_index.get(t.lower(), set()) for t in tokens]
        if not sets:
            return set()
        result = sets[0]
        for s in sets[1:]:
            result = result & s
        return set(result)

    def lookup_filters(self, filters: list[SearchFilter]) -> set[str]:
        """Apply multiple filters with AND semantics and return matching node IDs.

        Short-circuits on the first filter that yields an empty set.

        Args:
            filters: List of ``SearchFilter`` instances to apply.

        Returns:
            Node IDs satisfying all filters.
        """
        if not filters:
            return set()
        all_node_ids: set[str] | None = None
        for f in filters:
            ids = self._apply_filter(f)
            if all_node_ids is None:
                all_node_ids = ids
            else:
                all_node_ids &= ids
            if all_node_ids is not None and not all_node_ids:
                return set()
        return all_node_ids or set()

    def _apply_filter(self, f: SearchFilter) -> set[str]:
        """Evaluate a single filter and return matching node IDs.

        Dispatches to the appropriate lookup method based on whether the
        filter specifies multiple values, a numeric range, or a single value.
        Negated filters compute the complement within the field's known IDs.

        Args:
            f: The filter to evaluate.

        Returns:
            Set of node IDs matching (or excluded by) the filter.
        """
        if f.values is not None:
            ids = self.lookup_multi(f.field, f.values)
        elif f.min_value is not None or f.max_value is not None:
            ids = self.lookup_range(f.field, f.min_value, f.max_value)
        else:
            ids = self.lookup(f.field, f.value)
        if f.negated:
            all_ids: set[str] = set()
            for bucket in self._index.get(f.field, {}).values():
                all_ids |= bucket
            return all_ids - ids
        return ids

    def suggest_values(self, field: str, prefix: str, top_k: int = 10) -> list[str]:
        """Suggest indexed values for a field that start with *prefix*.

        Matching is case-insensitive.  Results are sorted alphabetically.

        Args:
            field: Data field name.
            prefix: Prefix string to match.
            top_k: Maximum number of suggestions to return.

        Returns:
            List of matching values, sorted alphabetically.
        """
        values = self._value_registry.get(field, set())
        prefix_lower = prefix.lower()
        matches = sorted(
            [v for v in values if v.lower().startswith(prefix_lower)],
            key=lambda v: v.lower(),
        )
        return matches[:top_k]

    def field_values(self, field: str) -> list[str]:
        """Return all distinct indexed values for a field, sorted.

        Args:
            field: Data field name.

        Returns:
            Sorted list of unique string values.
        """
        return sorted(self._value_registry.get(field, set()))

    def stats(self) -> dict[str, Any]:
        """Return summary statistics about the index.

        Returns:
            Dict with keys ``field_count``, ``value_count``, ``entry_count``,
            ``range_fields``, ``text_fields``, and ``dirty``.
        """
        total_entries = sum(
            len(ids) for field_map in self._index.values() for ids in field_map.values()
        )
        total_values = sum(len(vals) for vals in self._value_registry.values())
        return {
            "field_count": len(self._value_registry),
            "value_count": total_values,
            "entry_count": total_entries,
            "range_fields": list(self._range_index.keys()),
            "text_fields": list(self._text_index.keys()),
            "dirty": self._dirty,
        }


class SearchFilter:
    """Declarative filter specification for attribute lookups.

    Supports exact match, multi-value IN match, numeric range, and negation.

    Args:
        field: Node data field to filter on.
        value: Single value for exact match.
        min_value: Inclusive lower bound for range queries.
        max_value: Inclusive upper bound for range queries.
        values: List of values for multi-value (IN) matching.
        negated: If ``True``, the match set is complemented.
    """

    __slots__ = ("field", "value", "min_value", "max_value", "values", "negated")

    def __init__(
        self,
        field: str,
        value: Any = None,
        *,
        min_value: float | None = None,
        max_value: float | None = None,
        values: list[Any] | None = None,
        negated: bool = False,
    ) -> None:
        """Initialize a search filter.

        Args:
            field: The node data field to filter on.
            value: Exact value to match.
            min_value: Range lower bound (inclusive).
            max_value: Range upper bound (inclusive).
            values: List of values for multi-value match.
            negated: Invert the filter condition.
        """
        self.field = field
        self.value = value
        self.min_value = min_value
        self.max_value = max_value
        self.values = values
        self.negated = negated

    def __repr__(self) -> str:
        """Return a human-readable representation of the filter."""
        if self.values is not None:
            op = "NOT IN" if self.negated else "IN"
            return f"SearchFilter({self.field!r} {op} {self.values!r})"
        if self.min_value is not None or self.max_value is not None:
            return f"SearchFilter({self.field!r} {self.min_value}..{self.max_value})"
        op = "!=" if self.negated else "="
        return f"SearchFilter({self.field!r} {op} {self.value!r})"
