"""Exact, role-aware isomorphism for authored recipe graphs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import fields, is_dataclass
from typing import Any

from ..models.graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode


class GraphIsomorphismService:
    """Canonicalize graph logic while ignoring IDs and presentation metadata.

    A recipe is a rooted, edge-ordered directed graph.  The root is the first
    node of the required path and outgoing edge order is the authored switch
    order, so a deterministic traversal provides an exact canonical labeling
    for every node reachable from the root.  The small disconnected remainder
    is canonicalized by trying each possible component root.
    """

    def signature_for(self, recipe: GraphRecipe) -> str:
        """Return a stable SHA-256 signature for the recipe's logical graph."""

        canonical_form, _ = self._canonicalize(recipe)
        return hashlib.sha256(canonical_form.encode("utf-8")).hexdigest()

    def canonical_form_for(self, recipe: GraphRecipe) -> str:
        """Return the ID-independent canonical payload used by comparisons."""

        canonical_form, _ = self._canonicalize(recipe)
        return canonical_form

    def are_isomorphic(self, first: GraphRecipe, second: GraphRecipe) -> bool:
        return self.canonical_form_for(first) == self.canonical_form_for(second)

    def is_isomorphic(self, first: GraphRecipe, second: GraphRecipe) -> bool:
        """Singular-name compatibility alias."""

        return self.are_isomorphic(first, second)

    def node_mapping(
        self,
        first: GraphRecipe,
        second: GraphRecipe,
    ) -> dict[str, str] | None:
        """Return the canonical node mapping, or ``None`` for different graphs."""

        first_form, first_order = self._canonicalize(first)
        second_form, second_order = self._canonicalize(second)
        if first_form != second_form:
            return None
        return dict(zip(first_order, second_order, strict=True))

    def canonical_node_indices(self, recipe: GraphRecipe) -> dict[str, int]:
        """Expose canonical indices for services that need ID-free references."""

        _, order = self._canonicalize(recipe)
        return {node_id: index for index, node_id in enumerate(order)}

    def node_descriptor(self, recipe: GraphRecipe, node: GraphRecipeNode) -> tuple[Any, ...]:
        """Return the role and ordered-objective identity of a node."""

        start_node_id = recipe.required_path[0] if recipe.required_path else "start"
        special_roles: list[tuple[str, int]] = []
        if node.id == start_node_id:
            special_roles.append(("start", -1))

        objective_phases = self._objective_phases(recipe)
        if node.id in objective_phases:
            special_roles.append(("objective", objective_phases[node.id]))
        elif node.id == recipe.package_node_id:
            special_roles.append(("objective", 0))
        if node.id == recipe.destination_node_id:
            destination_phase = objective_phases.get(
                node.id,
                max(objective_phases.values(), default=0) + 1,
            )
            special_roles.append(("destination", destination_phase))

        return (
            str(node.role).strip().lower(),
            tuple(special_roles),
        )

    def edge_descriptor(self, edge: GraphRecipeEdge, authored_index: int) -> tuple[Any, ...]:
        """Return runtime-relevant edge state, including authored switch order."""

        attributes: list[tuple[str, Any]] = []
        if is_dataclass(edge):
            for field in fields(edge):
                if field.name in {"from_node_id", "to_node_id", "id"}:
                    continue
                attributes.append((field.name, self._json_value(getattr(edge, field.name))))
        else:  # Defensive support for graph-compatible test doubles.
            attributes.extend(
                (
                    ("availability", self._json_value(getattr(edge, "availability", "always"))),
                    ("usage_limit", self._json_value(getattr(edge, "usage_limit", None))),
                )
            )
        return (authored_index, tuple(attributes))

    def _canonicalize(self, recipe: GraphRecipe) -> tuple[str, tuple[str, ...]]:
        node_by_id = {node.id: node for node in recipe.nodes}
        if len(node_by_id) != len(recipe.nodes):
            raise ValueError("graph_isomorphism_duplicate_node_id")
        for edge in recipe.edges:
            if edge.from_node_id not in node_by_id or edge.to_node_id not in node_by_id:
                raise ValueError("graph_isomorphism_edge_references_unknown_node")
        if not node_by_id:
            return self._serialize(recipe, ()), ()

        outgoing = self._outgoing(recipe)
        start_node_id = recipe.required_path[0] if recipe.required_path else None
        if start_node_id not in node_by_id:
            start_node_id = None

        initial_order: tuple[str, ...] = ()
        if start_node_id is not None:
            initial_order = self._traverse(start_node_id, outgoing, frozenset())
        order = self._canonical_disconnected_order(recipe, outgoing, initial_order)
        return self._serialize(recipe, order), order

    def _canonical_disconnected_order(
        self,
        recipe: GraphRecipe,
        outgoing: dict[str, tuple[GraphRecipeEdge, ...]],
        prefix: tuple[str, ...],
    ) -> tuple[str, ...]:
        remaining = {node.id for node in recipe.nodes}.difference(prefix)
        if not remaining:
            return prefix

        # Disconnected recipe fragments are rare and small. Trying each next
        # root keeps canonicalization exact without making node IDs observable.
        candidates: list[tuple[str, tuple[str, ...]]] = []
        visited = frozenset(prefix)
        for seed in remaining:
            block = self._traverse(seed, outgoing, visited)
            candidate_order = self._canonical_disconnected_order(
                recipe,
                outgoing,
                (*prefix, *block),
            )
            candidates.append((self._serialize(recipe, candidate_order), candidate_order))
        return min(candidates, key=lambda item: item[0])[1]

    @staticmethod
    def _traverse(
        seed: str,
        outgoing: dict[str, tuple[GraphRecipeEdge, ...]],
        already_visited: frozenset[str],
    ) -> tuple[str, ...]:
        order: list[str] = []
        visited = set(already_visited)
        queue = [seed]
        while queue:
            node_id = queue.pop(0)
            if node_id in visited:
                continue
            visited.add(node_id)
            order.append(node_id)
            queue.extend(
                edge.to_node_id
                for edge in outgoing.get(node_id, ())
                if edge.to_node_id not in visited
            )
        return tuple(order)

    @staticmethod
    def _outgoing(recipe: GraphRecipe) -> dict[str, tuple[GraphRecipeEdge, ...]]:
        grouped: dict[str, list[GraphRecipeEdge]] = {}
        for edge in recipe.edges:
            grouped.setdefault(edge.from_node_id, []).append(edge)
        return {node_id: tuple(edges) for node_id, edges in grouped.items()}

    def _serialize(self, recipe: GraphRecipe, order: tuple[str, ...]) -> str:
        index_by_id = {node_id: index for index, node_id in enumerate(order)}
        node_by_id = {node.id: node for node in recipe.nodes}
        outgoing = self._outgoing(recipe)
        payload = {
            "nodes": [self.node_descriptor(recipe, node_by_id[node_id]) for node_id in order],
            "edges": [
                (
                    index_by_id[from_node_id],
                    index_by_id[edge.to_node_id],
                    self.edge_descriptor(edge, authored_index),
                )
                for from_node_id in order
                for authored_index, edge in enumerate(outgoing.get(from_node_id, ()))
            ],
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    @staticmethod
    def _objective_phases(recipe: GraphRecipe) -> dict[str, int]:
        phases: dict[str, int] = {}
        for objective in getattr(recipe, "objectives", ()) or ():
            node_id = getattr(objective, "node_id", None) or getattr(objective, "nodeID", None)
            sequence = getattr(objective, "sequence_index", None)
            if sequence is None:
                sequence = getattr(objective, "sequenceIndex", None)
            if isinstance(node_id, str) and isinstance(sequence, int):
                phases[node_id] = sequence
        return phases

    @classmethod
    def _json_value(cls, value: Any) -> Any:
        if is_dataclass(value):
            return {
                field.name: cls._json_value(getattr(value, field.name))
                for field in fields(value)
            }
        if isinstance(value, dict):
            return {
                str(key): cls._json_value(item)
                for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            }
        if isinstance(value, (list, tuple)):
            return [cls._json_value(item) for item in value]
        if isinstance(value, set):
            return sorted(cls._json_value(item) for item in value)
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)
