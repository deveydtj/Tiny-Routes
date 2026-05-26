from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

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

    def scale_positions(
        self,
        positions: dict[str, tuple[float, float]],
        scale_x: float,
        scale_y: float | None = None,
        center: tuple[float, float] = (0.0, 0.0),
    ) -> dict[str, tuple[float, float]]:
        resolved_scale_y = scale_x if scale_y is None else scale_y
        center_x, center_y = center
        return {
            node_id: self.snap_point(
                center_x + ((x - center_x) * scale_x),
                center_y + ((y - center_y) * resolved_scale_y),
            )
            for node_id, (x, y) in positions.items()
        }

    def translate_positions(
        self,
        positions: dict[str, tuple[float, float]],
        dx: float,
        dy: float,
    ) -> dict[str, tuple[float, float]]:
        return {
            node_id: self.snap_point(x + dx, y + dy)
            for node_id, (x, y) in positions.items()
        }

    def rotate_positions(
        self,
        positions: dict[str, tuple[float, float]],
        degrees: float,
        center: tuple[float, float] = (0.0, 0.0),
    ) -> dict[str, tuple[float, float]]:
        radians = math.radians(degrees)
        cos_value = math.cos(radians)
        sin_value = math.sin(radians)
        center_x, center_y = center
        rotated: dict[str, tuple[float, float]] = {}
        for node_id, (x, y) in positions.items():
            offset_x = x - center_x
            offset_y = y - center_y
            rotated[node_id] = self.snap_point(
                center_x + (offset_x * cos_value) - (offset_y * sin_value),
                center_y + (offset_x * sin_value) + (offset_y * cos_value),
            )
        return rotated

    def normalize_positions(
        self,
        positions: dict[str, tuple[float, float]],
        padding: float = 0.05,
    ) -> dict[str, tuple[float, float]]:
        if not positions:
            return {}

        min_x = min(x for x, _ in positions.values())
        max_x = max(x for x, _ in positions.values())
        min_y = min(y for _, y in positions.values())
        max_y = max(y for _, y in positions.values())
        source_width = max(max_x - min_x, 1e-9)
        source_height = max(max_y - min_y, 1e-9)
        target_min_x = self.bounds.min_x + padding
        target_max_x = self.bounds.max_x - padding
        target_min_y = self.bounds.min_y + padding
        target_max_y = self.bounds.max_y - padding
        target_width = max(target_max_x - target_min_x, 1e-9)
        target_height = max(target_max_y - target_min_y, 1e-9)

        normalized: dict[str, tuple[float, float]] = {}
        for node_id, (x, y) in positions.items():
            normalized[node_id] = self.snap_point(
                target_min_x + (((x - min_x) / source_width) * target_width),
                target_min_y + (((y - min_y) / source_height) * target_height),
            )
        return normalized

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

    def edge_crossings(
        self,
        positions: dict[str, tuple[float, float]],
        edges: Iterable[tuple[str, str, str | None]],
    ) -> list[tuple[str | None, str | None]]:
        edge_list = list(edges)
        crossings: list[tuple[str | None, str | None]] = []
        for index, (from_a, to_a, edge_a_id) in enumerate(edge_list):
            if from_a not in positions or to_a not in positions:
                continue
            for from_b, to_b, edge_b_id in edge_list[index + 1:]:
                if from_b not in positions or to_b not in positions:
                    continue
                if len({from_a, to_a, from_b, to_b}) < 4:
                    continue
                if self.segments_intersect(positions[from_a], positions[to_a], positions[from_b], positions[to_b]):
                    crossings.append((edge_a_id, edge_b_id))
        return crossings

    def edge_crossings_for_level(self, level_document) -> list[tuple[str | None, str | None]]:
        positions = {node.id: (node.x, node.y) for node in level_document.graph.nodes}
        edges = [(edge.fromNodeID, edge.toNodeID, edge.id) for edge in level_document.graph.edges]
        return self.edge_crossings(positions, edges)

    def segments_intersect(
        self,
        a1: tuple[float, float],
        a2: tuple[float, float],
        b1: tuple[float, float],
        b2: tuple[float, float],
    ) -> bool:
        def orientation(p, q, r) -> float:
            return ((q[1] - p[1]) * (r[0] - q[0])) - ((q[0] - p[0]) * (r[1] - q[1]))

        def on_segment(p, q, r) -> bool:
            return (
                min(p[0], r[0]) <= q[0] <= max(p[0], r[0])
                and min(p[1], r[1]) <= q[1] <= max(p[1], r[1])
            )

        o1 = orientation(a1, a2, b1)
        o2 = orientation(a1, a2, b2)
        o3 = orientation(b1, b2, a1)
        o4 = orientation(b1, b2, a2)
        tolerance = 1e-9

        if o1 * o2 < -tolerance and o3 * o4 < -tolerance:
            return True
        if abs(o1) <= tolerance and on_segment(a1, b1, a2):
            return True
        if abs(o2) <= tolerance and on_segment(a1, b2, a2):
            return True
        if abs(o3) <= tolerance and on_segment(b1, a1, b2):
            return True
        if abs(o4) <= tolerance and on_segment(b1, a2, b2):
            return True
        return False

    def edge_spacing_issues(
        self,
        positions: dict[str, tuple[float, float]],
        edges: Iterable[tuple[str, str, str | None]],
        minimum_spacing: float,
    ) -> list[tuple[str, str | None, float]]:
        issues: list[tuple[str, str | None, float]] = []
        for from_node_id, to_node_id, edge_id in edges:
            if from_node_id not in positions or to_node_id not in positions:
                continue
            start = positions[from_node_id]
            end = positions[to_node_id]
            for node_id, point in positions.items():
                if node_id in {from_node_id, to_node_id}:
                    continue
                distance = self._point_to_segment_distance(point, start, end)
                if distance < minimum_spacing:
                    issues.append((node_id, edge_id, round(distance, 4)))
        return issues

    def readability_summary(
        self,
        positions: dict[str, tuple[float, float]],
        edges: Iterable[tuple[str, str, str | None]],
        minimum_edge_spacing: float = 0.12,
    ) -> dict[str, int]:
        return {
            "overlaps": len(self.overlapping_pairs(positions)),
            "crossings": len(self.edge_crossings(positions, edges)),
            "edgeSpacingIssues": len(self.edge_spacing_issues(positions, edges, minimum_edge_spacing)),
        }

    def validate_positions(self, positions: dict[str, tuple[float, float]]) -> list[str]:
        messages: list[str] = []
        for node_id, (x, y) in positions.items():
            if not self.is_inside_bounds(x, y):
                messages.append(f"node_out_of_bounds:{node_id}")
        for first_id, second_id in self.overlapping_pairs(positions):
            messages.append(f"overlapping_nodes:{first_id}:{second_id}")
        return messages

    def _point_to_segment_distance(
        self,
        point: tuple[float, float],
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> float:
        segment_x = end[0] - start[0]
        segment_y = end[1] - start[1]
        length_squared = (segment_x * segment_x) + (segment_y * segment_y)
        if length_squared == 0:
            return self.point_distance(point, start)
        projection = (
            ((point[0] - start[0]) * segment_x) + ((point[1] - start[1]) * segment_y)
        ) / length_squared
        projection = max(0.0, min(1.0, projection))
        closest = (start[0] + (projection * segment_x), start[1] + (projection * segment_y))
        return self.point_distance(point, closest)
