from __future__ import annotations

import re


class IDAllocator:
    def __init__(self) -> None:
        self._node_ids: set[str] = set()
        self._edge_ids: set[str] = set()

    def reserve_node_id(self, base_name: str) -> str:
        node_id = self._unique(_safe_snake_case(base_name) or "node", self._node_ids)
        self._node_ids.add(node_id)
        return node_id

    def reserve_edge_id(self, from_node: str, to_node: str) -> str:
        base = f"e_{_safe_snake_case(from_node) or 'from'}_{_safe_snake_case(to_node) or 'to'}"
        edge_id = self._unique(base, self._edge_ids)
        self._edge_ids.add(edge_id)
        return edge_id

    def reserve_existing_node_id(self, node_id: str) -> None:
        if node_id in self._node_ids:
            raise ValueError(f"Duplicate node ID: {node_id}")
        self._node_ids.add(node_id)

    def reserve_existing_edge_id(self, edge_id: str) -> None:
        if edge_id in self._edge_ids:
            raise ValueError(f"Duplicate edge ID: {edge_id}")
        self._edge_ids.add(edge_id)

    @staticmethod
    def _unique(base: str, used: set[str]) -> str:
        if base not in used:
            return base
        suffix = 2
        while f"{base}_{suffix}" in used:
            suffix += 1
        return f"{base}_{suffix}"


def _safe_snake_case(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", value.strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if normalized and normalized[0].isdigit():
        normalized = f"id_{normalized}"
    return normalized
