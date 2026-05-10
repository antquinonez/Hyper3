from __future__ import annotations

from bisect import bisect_left, bisect_right
from typing import Any

from hyper3.kernel import Hypergraph


class AttributeIndex:
    def __init__(self, indexed_fields: set[str] | None = None) -> None:
        self._index: dict[str, dict[str, set[str]]] = {}
        self._range_index: dict[str, list[tuple[float, str]]] = {}
        self._text_index: dict[str, dict[str, set[str]]] = {}
        self._indexed_fields = indexed_fields
        self._dirty = True
        self._value_registry: dict[str, set[str]] = {}

    @property
    def dirty(self) -> bool:
        return self._dirty

    def mark_dirty(self) -> None:
        self._dirty = True

    def build(self, graph: Hypergraph) -> None:
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
        for field, entries in self._range_index.items():
            entries.sort(key=lambda x: x[0])
        self._dirty = False

    def _index_entry(self, node_id: str, field: str, value: Any) -> None:
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
        str_val = str(value) if not isinstance(value, str) else value
        return set(self._index.get(field, {}).get(str_val, set()))

    def lookup_range(self, field: str, min_val: float | None = None, max_val: float | None = None) -> set[str]:
        entries = self._range_index.get(field, [])
        if not entries:
            return set()
        lo = bisect_left(entries, (min_val, "")) if min_val is not None else 0
        hi = bisect_right(entries, (max_val, "\uffff")) if max_val is not None else len(entries)
        return {node_id for _, node_id in entries[lo:hi]}

    def lookup_multi(self, field: str, values: list[Any]) -> set[str]:
        result: set[str] = set()
        for v in values:
            result |= self.lookup(field, v)
        return result

    def lookup_text(self, field: str, tokens: list[str]) -> set[str]:
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
        values = self._value_registry.get(field, set())
        prefix_lower = prefix.lower()
        matches = sorted(
            [v for v in values if v.lower().startswith(prefix_lower)],
            key=lambda v: v.lower(),
        )
        return matches[:top_k]

    def field_values(self, field: str) -> list[str]:
        return sorted(self._value_registry.get(field, set()))

    def stats(self) -> dict[str, Any]:
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
        self.field = field
        self.value = value
        self.min_value = min_value
        self.max_value = max_value
        self.values = values
        self.negated = negated

    def __repr__(self) -> str:
        if self.values is not None:
            op = "NOT IN" if self.negated else "IN"
            return f"SearchFilter({self.field!r} {op} {self.values!r})"
        if self.min_value is not None or self.max_value is not None:
            return f"SearchFilter({self.field!r} {self.min_value}..{self.max_value})"
        op = "!=" if self.negated else "="
        return f"SearchFilter({self.field!r} {op} {self.value!r})"
