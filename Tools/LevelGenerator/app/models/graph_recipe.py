from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from .abstract_puzzle_solution import AbstractPuzzleSolutionMetadata


@dataclass(frozen=True)
class GraphRecipeNode:
    id: str
    role: str = "route"


@dataclass(frozen=True)
class GraphRecipeEdge:
    from_node_id: str
    to_node_id: str


@dataclass(frozen=True)
class GraphRecipe:
    level_id: str
    difficulty: str
    nodes: tuple[GraphRecipeNode, ...]
    edges: tuple[GraphRecipeEdge, ...]
    required_path: tuple[str, ...]
    tap_node_ids: tuple[str, ...]
    package_node_id: str = "package"
    destination_node_id: str = "destination"
    notes: tuple[str, ...] = field(default_factory=tuple)
    family_name: str = "graph_recipe"
    variant_name: str = "default"
    solved_metadata: AbstractPuzzleSolutionMetadata | None = None

    def validate(self) -> list[str]:
        messages: list[str] = []
        node_ids = {node.id for node in self.nodes}
        if not self.required_path:
            messages.append("required_path_empty")
            return messages
        if self.required_path[0] != "start":
            messages.append("required_path_must_start_at_start")
        if self.required_path[-1] != self.destination_node_id:
            messages.append("required_path_must_end_at_destination")
        if self.package_node_id not in self.required_path:
            messages.append("required_path_must_visit_package")
        elif self.required_path.index(self.package_node_id) > self.required_path.index(self.destination_node_id):
            messages.append("required_path_must_visit_package_before_destination")
        for node_id in self.required_path:
            if node_id not in node_ids:
                messages.append(f"required_path_unknown_node:{node_id}")
        for edge in self.edges:
            if edge.from_node_id not in node_ids:
                messages.append(f"edge_unknown_from_node:{edge.from_node_id}")
            if edge.to_node_id not in node_ids:
                messages.append(f"edge_unknown_to_node:{edge.to_node_id}")
        edge_pairs = {(edge.from_node_id, edge.to_node_id) for edge in self.edges}
        for from_node_id, to_node_id in zip(self.required_path, self.required_path[1:]):
            if (from_node_id, to_node_id) not in edge_pairs:
                messages.append(f"required_path_missing_edge:{from_node_id}:{to_node_id}")
        return messages

    @property
    def abstract_signature(self) -> str:
        payload = {
            "difficulty": self.difficulty,
            "family": self.family_name,
            "variant": self.variant_name,
            "nodes": [(node.id, node.role) for node in self.nodes],
            "edges": [(edge.from_node_id, edge.to_node_id) for edge in self.edges],
            "requiredPath": list(self.required_path),
            "tapNodeIDs": list(self.tap_node_ids),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
