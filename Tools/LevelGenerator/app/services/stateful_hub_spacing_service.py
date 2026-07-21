"""Deterministic layout reservations and validation for cross-phase hubs."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..models.layout_constraints import BoundingBox, ConstraintViolation, ReservedIconClearance
from ..models.layout_graph import LayoutGraph, LayoutGraphEdge


@dataclass(frozen=True)
class StatefulHubSpacingThresholds:
    horizontal_clearance_cells: int = 3
    vertical_clearance_cells: int = 3
    minimum_approach_length: float = 0.3
    minimum_exit_length: float = 0.34
    minimum_stateful_exit_length: float = 0.42
    minimum_outgoing_angle_degrees: float = 32.0
    minimum_return_exit_angle_degrees: float = 24.0
    camera_margin: float = 0.12

    def __post_init__(self) -> None:
        for field_name in ("horizontal_clearance_cells", "vertical_clearance_cells"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"{field_name} must be a positive integer")
        for field_name in (
            "minimum_approach_length",
            "minimum_exit_length",
            "minimum_stateful_exit_length",
            "minimum_outgoing_angle_degrees",
            "minimum_return_exit_angle_degrees",
            "camera_margin",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} must be non-negative")


@dataclass(frozen=True)
class StatefulHubSpacingRule:
    hub_node_id: str
    objective_phase_indices: tuple[int, ...]
    outgoing_node_ids: tuple[str, ...]
    return_approach_node_ids: tuple[str, ...]
    stateful_edge_ids: tuple[str, ...]
    reserved_clearance: ReservedIconClearance


class StatefulHubSpacingService:
    """Reserve and prove enough space to understand a hub on every visit."""

    def __init__(self, thresholds: StatefulHubSpacingThresholds | None = None) -> None:
        self.thresholds = thresholds or StatefulHubSpacingThresholds()

    def rules_for(self, graph: LayoutGraph) -> tuple[StatefulHubSpacingRule, ...]:
        edge_by_destination: dict[str, list[LayoutGraphEdge]] = {}
        edge_by_source: dict[str, list[LayoutGraphEdge]] = {}
        for edge in graph.edges:
            edge_by_destination.setdefault(edge.to_node_id, []).append(edge)
            edge_by_source.setdefault(edge.from_node_id, []).append(edge)

        rules: list[StatefulHubSpacingRule] = []
        for node in graph.nodes:
            if not node.is_revisited_hub:
                continue
            later_phases = set(node.objective_phase_indices[1:])
            incoming = edge_by_destination.get(node.node_id, [])
            return_approaches = tuple(sorted({
                edge.from_node_id
                for edge in incoming
                if later_phases.intersection(edge.objective_phase_indices)
            }))
            if not return_approaches and len(incoming) > 1:
                return_approaches = tuple(
                    edge.from_node_id
                    for edge in sorted(incoming, key=lambda item: item.edge_id)[1:]
                )
            incident = (*incoming, *edge_by_source.get(node.node_id, ()))
            stateful_edges = tuple(sorted(
                edge.edge_id for edge in incident if edge.state_relationships
            ))
            rules.append(StatefulHubSpacingRule(
                hub_node_id=node.node_id,
                objective_phase_indices=node.objective_phase_indices,
                outgoing_node_ids=tuple(sorted(node.outgoing_node_ids)),
                return_approach_node_ids=return_approaches,
                stateful_edge_ids=stateful_edges,
                reserved_clearance=ReservedIconClearance(
                    node.node_id,
                    self.thresholds.horizontal_clearance_cells,
                    self.thresholds.vertical_clearance_cells,
                ),
            ))
        return tuple(rules)

    def validate(
        self,
        graph: LayoutGraph,
        positions: dict[str, tuple[float, float]],
        *,
        bounds: BoundingBox | None = None,
    ) -> tuple[ConstraintViolation, ...]:
        issues: list[ConstraintViolation] = []
        edge_by_id = {edge.edge_id: edge for edge in graph.edges}
        resolved_bounds = bounds or BoundingBox()
        for rule in self.rules_for(graph):
            if rule.hub_node_id not in positions:
                issues.append(ConstraintViolation(
                    "stateful_hub_position_missing",
                    f"Stateful hub '{rule.hub_node_id}' has no layout position.",
                    node_id=rule.hub_node_id,
                ))
                continue
            hub = positions[rule.hub_node_id]
            required_neighbors = set(rule.outgoing_node_ids).union(
                rule.return_approach_node_ids
            )
            missing = sorted(required_neighbors.difference(positions))
            for node_id in missing:
                issues.append(ConstraintViolation(
                    "stateful_hub_neighbor_position_missing",
                    f"Stateful hub '{rule.hub_node_id}' is missing neighbor '{node_id}'.",
                    node_id=rule.hub_node_id,
                ))

            outgoing_vectors: list[tuple[str, tuple[float, float]]] = []
            stateful_pairs = {
                (edge.from_node_id, edge.to_node_id)
                for edge_id in rule.stateful_edge_ids
                if (edge := edge_by_id.get(edge_id)) is not None
            }
            for node_id in rule.outgoing_node_ids:
                if node_id not in positions:
                    continue
                vector = self._vector(hub, positions[node_id])
                distance = self._length(vector)
                threshold = (
                    self.thresholds.minimum_stateful_exit_length
                    if (rule.hub_node_id, node_id) in stateful_pairs
                    else self.thresholds.minimum_exit_length
                )
                if distance < threshold:
                    issues.append(ConstraintViolation(
                        "stateful_hub_exit_clearance_failure",
                        f"Exit '{rule.hub_node_id}' -> '{node_id}' is {distance:.3f}; "
                        f"minimum is {threshold:.3f}.",
                        node_id=rule.hub_node_id,
                    ))
                outgoing_vectors.append((node_id, vector))

            for index, (first_id, first_vector) in enumerate(outgoing_vectors):
                for second_id, second_vector in outgoing_vectors[index + 1:]:
                    angle = self._angle(first_vector, second_vector)
                    if angle < self.thresholds.minimum_outgoing_angle_degrees:
                        issues.append(ConstraintViolation(
                            "stateful_hub_outgoing_separation_failure",
                            f"Exits to '{first_id}' and '{second_id}' are separated by "
                            f"{angle:.1f} degrees; minimum is "
                            f"{self.thresholds.minimum_outgoing_angle_degrees:.1f}.",
                            node_id=rule.hub_node_id,
                        ))

            for approach_id in rule.return_approach_node_ids:
                if approach_id not in positions:
                    continue
                approach_vector = self._vector(hub, positions[approach_id])
                distance = self._length(approach_vector)
                if distance < self.thresholds.minimum_approach_length:
                    issues.append(ConstraintViolation(
                        "stateful_hub_return_approach_clearance_failure",
                        f"Return approach '{approach_id}' -> '{rule.hub_node_id}' is "
                        f"{distance:.3f}; minimum is "
                        f"{self.thresholds.minimum_approach_length:.3f}.",
                        node_id=rule.hub_node_id,
                    ))
                for exit_id, exit_vector in outgoing_vectors:
                    if exit_id == approach_id:
                        continue
                    angle = self._angle(approach_vector, exit_vector)
                    if angle < self.thresholds.minimum_return_exit_angle_degrees:
                        issues.append(ConstraintViolation(
                            "stateful_hub_return_exit_overlap",
                            f"Return approach from '{approach_id}' overlaps exit to "
                            f"'{exit_id}' at {angle:.1f} degrees.",
                            node_id=rule.hub_node_id,
                        ))

            neighborhood = [hub, *(positions[node_id] for node_id in required_neighbors if node_id in positions)]
            margin = self.thresholds.camera_margin
            if any(
                x < resolved_bounds.min_x + margin
                or x > resolved_bounds.max_x - margin
                or y < resolved_bounds.min_y + margin
                or y > resolved_bounds.max_y - margin
                for x, y in neighborhood
            ):
                issues.append(ConstraintViolation(
                    "stateful_hub_camera_frame_failure",
                    f"Stateful hub '{rule.hub_node_id}' and its approaches do not fit "
                    "inside the safe camera frame.",
                    node_id=rule.hub_node_id,
                ))
        return tuple(issues)

    @staticmethod
    def _vector(
        origin: tuple[float, float],
        target: tuple[float, float],
    ) -> tuple[float, float]:
        return target[0] - origin[0], target[1] - origin[1]

    @staticmethod
    def _length(vector: tuple[float, float]) -> float:
        return math.hypot(*vector)

    @classmethod
    def _angle(
        cls,
        first: tuple[float, float],
        second: tuple[float, float],
    ) -> float:
        denominator = cls._length(first) * cls._length(second)
        if denominator == 0:
            return 0.0
        cosine = max(-1.0, min(1.0, ((first[0] * second[0]) + (first[1] * second[1])) / denominator))
        return math.degrees(math.acos(cosine))
