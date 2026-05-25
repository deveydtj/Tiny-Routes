from __future__ import annotations

import math
from dataclasses import dataclass

from ..random_source import RandomSource


@dataclass(frozen=True)
class BoundingBox:
    min_x: float = -1.2
    max_x: float = 1.2
    min_y: float = -1.3
    max_y: float = 1.0


class GraphLayoutService:
    def __init__(
        self,
        bounds: BoundingBox | None = None,
        minimum_node_distance: float = 0.2,
        grid_size: float = 0.05,
    ) -> None:
        self.bounds = bounds or BoundingBox()
        self.minimum_node_distance = minimum_node_distance
        self.grid_size = grid_size

    def snap(self, value: float) -> float:
        return round(round(value / self.grid_size) * self.grid_size, 4)

    def snap_point(self, x: float, y: float) -> tuple[float, float]:
        return self.snap(x), self.snap(y)

    def is_inside_bounds(self, x: float, y: float) -> bool:
        return self.bounds.min_x <= x <= self.bounds.max_x and self.bounds.min_y <= y <= self.bounds.max_y

    def point_distance(self, a: tuple[float, float], b: tuple[float, float]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def has_overlaps(self, positions: dict[str, tuple[float, float]]) -> bool:
        return bool(self.overlapping_pairs(positions))

    def overlapping_pairs(self, positions: dict[str, tuple[float, float]]) -> list[tuple[str, str]]:
        node_ids = list(positions)
        pairs: list[tuple[str, str]] = []
        for index, first_id in enumerate(node_ids):
            for second_id in node_ids[index + 1:]:
                if self.point_distance(positions[first_id], positions[second_id]) < self.minimum_node_distance:
                    pairs.append((first_id, second_id))
        return pairs

    def zero_length_edges(self, level_document) -> list[str]:
        positions = {node.id: (node.x, node.y) for node in level_document.graph.nodes}
        edge_ids: list[str] = []
        for edge in level_document.graph.edges:
            if edge.fromNodeID in positions and edge.toNodeID in positions:
                if self.point_distance(positions[edge.fromNodeID], positions[edge.toNodeID]) == 0:
                    edge_ids.append(edge.id)
        return edge_ids

    def mirror_horizontally(self, positions: dict[str, tuple[float, float]]) -> dict[str, tuple[float, float]]:
        return {node_id: self.snap_point(-x, y) for node_id, (x, y) in positions.items()}

    def mirror_vertically(self, positions: dict[str, tuple[float, float]]) -> dict[str, tuple[float, float]]:
        return {node_id: self.snap_point(x, -y) for node_id, (x, y) in positions.items()}

    def apply_safe_jitter(
        self,
        positions: dict[str, tuple[float, float]],
        rng: RandomSource,
        amount: float = 0.03,
    ) -> dict[str, tuple[float, float]]:
        jittered: dict[str, tuple[float, float]] = {}
        for node_id, (x, y) in positions.items():
            candidate = self.snap_point(x + rng.uniform(-amount, amount), y + rng.uniform(-amount, amount))
            if self.is_inside_bounds(*candidate):
                jittered[node_id] = candidate
            else:
                jittered[node_id] = (x, y)
        return jittered if not self.has_overlaps(jittered) else positions

    def validate_positions(self, positions: dict[str, tuple[float, float]]) -> list[str]:
        messages: list[str] = []
        for node_id, (x, y) in positions.items():
            if not self.is_inside_bounds(x, y):
                messages.append(f"node_out_of_bounds:{node_id}")
        for first_id, second_id in self.overlapping_pairs(positions):
            messages.append(f"overlapping_nodes:{first_id}:{second_id}")
        return messages
