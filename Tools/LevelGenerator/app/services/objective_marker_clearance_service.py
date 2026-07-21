"""Objective-marker placement reservations and geometric clearance checks."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..models.layout_constraints import (
    BoundingBox,
    ConstraintViolation,
    ReservedIconClearance,
)
from ..models.layout_graph import LayoutGraph, LayoutObjective
from ..models.layout_state import ObjectiveMarkerPlacement


@dataclass(frozen=True)
class ObjectiveMarkerClearanceThresholds:
    horizontal_clearance_cells: int = 2
    vertical_clearance_cells: int = 2
    minimum_marker_separation: float = 0.32
    minimum_node_clearance: float = 0.24
    minimum_stateful_hub_clearance: float = 0.38
    minimum_road_clearance: float = 0.16
    camera_margin: float = 0.1

    def __post_init__(self) -> None:
        for field_name in ("horizontal_clearance_cells", "vertical_clearance_cells"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"{field_name} must be a positive integer")
        for field_name in (
            "minimum_marker_separation",
            "minimum_node_clearance",
            "minimum_stateful_hub_clearance",
            "minimum_road_clearance",
            "camera_margin",
        ):
            value = getattr(self, field_name)
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or value < 0
            ):
                raise ValueError(f"{field_name} must be non-negative")


@dataclass(frozen=True)
class ObjectiveMarkerClearanceRule:
    objective_id: str
    node_id: str
    phase_index: int
    reserved_clearance: ReservedIconClearance


class ObjectiveMarkerClearanceService:
    """Keep current and future objective artwork readable in every phase."""

    def __init__(
        self,
        thresholds: ObjectiveMarkerClearanceThresholds | None = None,
    ) -> None:
        self.thresholds = thresholds or ObjectiveMarkerClearanceThresholds()

    def rules_for(
        self,
        graph: LayoutGraph,
    ) -> tuple[ObjectiveMarkerClearanceRule, ...]:
        return tuple(
            ObjectiveMarkerClearanceRule(
                objective.objective_id,
                objective.node_id,
                objective.phase_index,
                ReservedIconClearance(
                    objective.node_id,
                    self.thresholds.horizontal_clearance_cells,
                    self.thresholds.vertical_clearance_cells,
                ),
            )
            for objective in sorted(
                graph.objectives,
                key=lambda item: (item.phase_index, item.objective_id),
            )
        )

    def placements_for(
        self,
        graph: LayoutGraph,
        positions: dict[str, tuple[float, float]],
        *,
        marker_positions: dict[str, tuple[float, float]] | None = None,
        visible_objective_ids: tuple[str, ...] | None = None,
        active_objective_id: str | None = None,
        completed_objective_ids: tuple[str, ...] = (),
    ) -> tuple[ObjectiveMarkerPlacement, ...]:
        visible = (
            {objective.objective_id for objective in graph.objectives}
            if visible_objective_ids is None
            else set(visible_objective_ids)
        )
        completed = set(completed_objective_ids)
        placements: list[ObjectiveMarkerPlacement] = []
        for objective in sorted(
            graph.objectives,
            key=lambda item: (item.phase_index, item.objective_id),
        ):
            resolved_positions = marker_positions or {}
            if (
                objective.objective_id not in visible
                or (
                    objective.objective_id not in resolved_positions
                    and objective.node_id not in positions
                )
            ):
                continue
            status = (
                "active"
                if objective.objective_id == active_objective_id
                else "completed"
                if objective.objective_id in completed
                else "future"
            )
            marker_position = resolved_positions.get(objective.objective_id)
            if marker_position is None:
                marker_position = positions[objective.node_id]
            placements.append(ObjectiveMarkerPlacement(
                objective.objective_id,
                objective.node_id,
                objective.phase_index,
                status,
                marker_position,
            ))
        return tuple(placements)

    def validate(
        self,
        graph: LayoutGraph,
        positions: dict[str, tuple[float, float]],
        *,
        marker_positions: dict[str, tuple[float, float]] | None = None,
        visible_objective_ids: tuple[str, ...] | None = None,
        active_objective_id: str | None = None,
        completed_objective_ids: tuple[str, ...] = (),
        edge_ids: tuple[str, ...] | None = None,
        bounds: BoundingBox | None = None,
    ) -> tuple[ConstraintViolation, ...]:
        selected = self._selected_objectives(graph, visible_objective_ids)
        issues: list[ConstraintViolation] = []
        for objective in selected:
            if objective.node_id not in positions:
                issues.append(ConstraintViolation(
                    "objective_marker_position_missing",
                    f"Objective '{objective.objective_id}' has no marker position.",
                    node_id=objective.node_id,
                ))

        placements = self.placements_for(
            graph,
            positions,
            marker_positions=marker_positions,
            visible_objective_ids=tuple(item.objective_id for item in selected),
            active_objective_id=active_objective_id,
            completed_objective_ids=completed_objective_ids,
        )
        objective_node_ids = {item.node_id for item in selected}
        stateful_hub_ids = set(graph.stateful_hub_node_ids)

        for index, first in enumerate(placements):
            for second in placements[index + 1:]:
                distance = self._distance(first.position, second.position)
                if distance < self.thresholds.minimum_marker_separation:
                    issues.append(ConstraintViolation(
                        "objective_marker_overlap",
                        f"Objective markers '{first.objective_id}' and "
                        f"'{second.objective_id}' are {distance:.3f} apart; minimum is "
                        f"{self.thresholds.minimum_marker_separation:.3f}.",
                        node_id=first.node_id,
                    ))

            for node in graph.nodes:
                if node.node_id == first.node_id or node.node_id in objective_node_ids:
                    continue
                point = positions.get(node.node_id)
                if point is None:
                    continue
                threshold = (
                    self.thresholds.minimum_stateful_hub_clearance
                    if node.node_id in stateful_hub_ids
                    else self.thresholds.minimum_node_clearance
                )
                distance = self._distance(first.position, point)
                if distance < threshold:
                    code = (
                        "objective_marker_stateful_hub_overlap"
                        if node.node_id in stateful_hub_ids
                        else "objective_marker_node_clearance_failure"
                    )
                    issues.append(ConstraintViolation(
                        code,
                        f"Objective marker '{first.objective_id}' is {distance:.3f} "
                        f"from node '{node.node_id}'; minimum is {threshold:.3f}.",
                        node_id=first.node_id,
                    ))

            if first.node_id in stateful_hub_ids:
                issues.append(ConstraintViolation(
                    "objective_marker_stateful_hub_overlap",
                    f"Objective marker '{first.objective_id}' occupies stateful hub "
                    f"'{first.node_id}'.",
                    node_id=first.node_id,
                ))

        selected_edge_ids = (
            {edge.edge_id for edge in graph.edges}
            if edge_ids is None
            else set(edge_ids)
        )
        for placement in placements:
            for edge in graph.edges:
                if edge.edge_id not in selected_edge_ids:
                    continue
                if placement.node_id in {edge.from_node_id, edge.to_node_id}:
                    continue
                start = positions.get(edge.from_node_id)
                end = positions.get(edge.to_node_id)
                if start is None or end is None:
                    continue
                distance = self._point_to_segment_distance(
                    placement.position,
                    start,
                    end,
                )
                if distance < self.thresholds.minimum_road_clearance:
                    issues.append(ConstraintViolation(
                        "objective_marker_road_clearance_failure",
                        f"Road '{edge.edge_id}' is {distance:.3f} from objective "
                        f"marker '{placement.objective_id}'; minimum is "
                        f"{self.thresholds.minimum_road_clearance:.3f}.",
                        node_id=placement.node_id,
                        edge_id=edge.edge_id,
                    ))

        resolved_bounds = bounds or BoundingBox()
        margin = self.thresholds.camera_margin
        for placement in placements:
            x, y = placement.position
            if (
                x < resolved_bounds.min_x + margin
                or x > resolved_bounds.max_x - margin
                or y < resolved_bounds.min_y + margin
                or y > resolved_bounds.max_y - margin
            ):
                issues.append(ConstraintViolation(
                    "objective_marker_camera_frame_failure",
                    f"Objective marker '{placement.objective_id}' is outside the "
                    "safe camera frame.",
                    node_id=placement.node_id,
                ))
        return tuple(issues)

    @staticmethod
    def _selected_objectives(
        graph: LayoutGraph,
        visible_objective_ids: tuple[str, ...] | None,
    ) -> tuple[LayoutObjective, ...]:
        visible = None if visible_objective_ids is None else set(visible_objective_ids)
        return tuple(
            objective
            for objective in sorted(
                graph.objectives,
                key=lambda item: (item.phase_index, item.objective_id),
            )
            if visible is None or objective.objective_id in visible
        )

    @staticmethod
    def _distance(
        first: tuple[float, float],
        second: tuple[float, float],
    ) -> float:
        return math.hypot(first[0] - second[0], first[1] - second[1])

    @staticmethod
    def _point_to_segment_distance(
        point: tuple[float, float],
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> float:
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        denominator = (dx * dx) + (dy * dy)
        if denominator == 0:
            return ObjectiveMarkerClearanceService._distance(point, start)
        scale = max(0.0, min(1.0, (
            ((point[0] - start[0]) * dx) + ((point[1] - start[1]) * dy)
        ) / denominator))
        nearest = (start[0] + (scale * dx), start[1] + (scale * dy))
        return ObjectiveMarkerClearanceService._distance(point, nearest)
