"""Validate visual readability before and after every objective state change."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..models.layout_constraints import BoundingBox, ConstraintViolation
from ..models.layout_graph import LayoutGraph, LayoutGraphEdge
from ..models.layout_state import (
    LayoutStateSnapshot,
    LayoutStateValidation,
    PrePostStateLayoutValidationResult,
)
from ..models.motif_contract import MotifEdgeStateChangeKind
from .graph_layout_service import GraphLayoutService
from .objective_marker_clearance_service import ObjectiveMarkerClearanceService


@dataclass(frozen=True)
class PrePostStateLayoutThresholds:
    camera_margin: float = 0.08
    minimum_node_road_clearance: float = 0.14
    minimum_lock_node_clearance: float = 0.16
    minimum_lock_objective_clearance: float = 0.2
    minimum_active_switch_objective_clearance: float = 0.3

    def __post_init__(self) -> None:
        for field_name in (
            "camera_margin",
            "minimum_node_road_clearance",
            "minimum_lock_node_clearance",
            "minimum_lock_objective_clearance",
            "minimum_active_switch_objective_clearance",
        ):
            value = getattr(self, field_name)
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or value < 0
            ):
                raise ValueError(f"{field_name} must be non-negative")


class PrePostStateLayoutValidationService:
    """Fail a layout when any objective-phase overlay is unreadable."""

    def __init__(
        self,
        thresholds: PrePostStateLayoutThresholds | None = None,
        objective_markers: ObjectiveMarkerClearanceService | None = None,
    ) -> None:
        self.thresholds = thresholds or PrePostStateLayoutThresholds()
        self.objective_markers = objective_markers or ObjectiveMarkerClearanceService()
        self.geometry = GraphLayoutService()

    def snapshots_for(self, graph: LayoutGraph) -> tuple[LayoutStateSnapshot, ...]:
        objectives = tuple(sorted(
            graph.objectives,
            key=lambda item: (item.phase_index, item.objective_id),
        ))
        state_count = max(1, len(objectives) + 1)
        snapshots: list[LayoutStateSnapshot] = []
        for state_index in range(state_count):
            completed = objectives[:state_index]
            remaining = objectives[state_index:]
            active = remaining[0].objective_id if remaining else None
            visible = tuple(item.objective_id for item in remaining)
            available: list[str] = []
            locked: list[str] = []
            consumed: list[str] = []
            for edge in graph.edges:
                is_available, is_consumed = self._edge_state(
                    edge,
                    state_index,
                    graph,
                )
                if is_available:
                    available.append(edge.edge_id)
                elif is_consumed:
                    consumed.append(edge.edge_id)
                elif edge.state_relationships or edge.availability != "always":
                    locked.append(edge.edge_id)

            available_set = set(available)
            active_switches = tuple(
                node.node_id
                for node in sorted(graph.nodes, key=lambda item: item.node_id)
                if node.role == "switch"
                and active is not None
                and sum(
                    edge.edge_id in available_set
                    for edge in graph.edges
                    if edge.from_node_id == node.node_id
                ) >= 2
                and (
                    not node.objective_phase_indices
                    or min(state_index, max(graph.objective_phase_count - 1, 0))
                    in node.objective_phase_indices
                )
            )
            snapshots.append(LayoutStateSnapshot(
                state_index,
                tuple(item.objective_id for item in completed),
                active,
                visible,
                tuple(available),
                tuple(locked),
                tuple(consumed),
                active_switches,
            ))
        return tuple(snapshots)

    def validate(
        self,
        graph: LayoutGraph,
        positions: dict[str, tuple[float, float]],
        *,
        bounds: BoundingBox | None = None,
        objective_marker_positions: dict[str, tuple[float, float]] | None = None,
        lock_indicator_positions: dict[str, tuple[float, float]] | None = None,
        edge_shapes: dict[str, str] | None = None,
    ) -> PrePostStateLayoutValidationResult:
        resolved_bounds = bounds or BoundingBox()
        validations: list[LayoutStateValidation] = []
        edge_by_id = {edge.edge_id: edge for edge in graph.edges}
        for snapshot in self.snapshots_for(graph):
            issues = list(self.objective_markers.validate(
                graph,
                positions,
                marker_positions=objective_marker_positions,
                visible_objective_ids=snapshot.visible_objective_ids,
                active_objective_id=snapshot.active_objective_id,
                completed_objective_ids=snapshot.completed_objective_ids,
                edge_ids=snapshot.available_edge_ids,
                bounds=resolved_bounds,
            ))
            markers = self.objective_markers.placements_for(
                graph,
                positions,
                marker_positions=objective_marker_positions,
                visible_objective_ids=snapshot.visible_objective_ids,
                active_objective_id=snapshot.active_objective_id,
                completed_objective_ids=snapshot.completed_objective_ids,
            )
            available_edges = tuple(
                edge_by_id[edge_id]
                for edge_id in snapshot.available_edge_ids
                if edge_id in edge_by_id
            )
            locked_edges = tuple(
                edge_by_id[edge_id]
                for edge_id in snapshot.locked_edge_ids
                if edge_id in edge_by_id
            )
            lock_indicators = self._lock_indicators(
                locked_edges,
                positions,
                lock_indicator_positions,
            )
            issues.extend(self._missing_positions(graph, positions, snapshot.state_index))
            issues.extend(self._route_crossings(
                available_edges,
                positions,
                snapshot.state_index,
                edge_shapes,
            ))
            issues.extend(self._node_road_clearance(
                graph,
                available_edges,
                positions,
                snapshot.state_index,
                edge_shapes,
            ))
            issues.extend(self._lock_indicator_clearance(
                graph,
                lock_indicators,
                markers,
                positions,
                snapshot.state_index,
            ))
            issues.extend(self._active_switch_clearance(
                snapshot,
                markers,
                positions,
                resolved_bounds,
            ))
            issues.extend(self._camera_bounds(
                graph,
                markers,
                lock_indicators,
                positions,
                resolved_bounds,
                snapshot.state_index,
            ))
            validations.append(LayoutStateValidation(
                snapshot,
                markers,
                tuple(sorted(lock_indicators.items())),
                self._dedupe(issues),
            ))
        return PrePostStateLayoutValidationResult(tuple(validations))

    def _edge_state(
        self,
        edge: LayoutGraphEdge,
        state_index: int,
        graph: LayoutGraph,
    ) -> tuple[bool, bool]:
        available = (
            state_index == 0
            if edge.availability == "beforePackage"
            else state_index >= 1
            if edge.availability == "afterPackage"
            else True
        )
        consumed = False
        for relationship in edge.state_relationships:
            trigger = self._trigger_state_index(
                edge,
                relationship.transition_id,
                relationship.kind,
                graph,
            )
            if relationship.kind is MotifEdgeStateChangeKind.OPEN:
                available = available and state_index >= trigger
            elif relationship.kind is MotifEdgeStateChangeKind.CLOSE:
                available = available and state_index < trigger
            elif relationship.kind is MotifEdgeStateChangeKind.CONSUME:
                if state_index >= trigger:
                    available = False
                    consumed = True
        return available, consumed

    @staticmethod
    def _trigger_state_index(
        edge: LayoutGraphEdge,
        transition_id: str,
        kind: MotifEdgeStateChangeKind,
        graph: LayoutGraph,
    ) -> int:
        matching = next(
            (
                objective.phase_index + 1
                for objective in graph.objectives
                if objective.objective_id == transition_id
            ),
            None,
        )
        if matching is not None:
            return matching
        if edge.objective_phase_indices:
            if kind is MotifEdgeStateChangeKind.OPEN:
                return max(1, min(edge.objective_phase_indices))
            return max(edge.objective_phase_indices) + 1
        return 1

    def _missing_positions(
        self,
        graph: LayoutGraph,
        positions: dict[str, tuple[float, float]],
        state_index: int,
    ) -> tuple[ConstraintViolation, ...]:
        return tuple(
            ConstraintViolation(
                "layout_state_node_position_missing",
                f"State {state_index} has no position for node '{node.node_id}'.",
                node_id=node.node_id,
            )
            for node in graph.nodes
            if node.node_id not in positions
        )

    def _route_crossings(
        self,
        edges: tuple[LayoutGraphEdge, ...],
        positions: dict[str, tuple[float, float]],
        state_index: int,
        edge_shapes: dict[str, str] | None = None,
    ) -> tuple[ConstraintViolation, ...]:
        if not edge_shapes:
            crossings = self.geometry.edge_crossings(
                positions,
                (
                    (edge.from_node_id, edge.to_node_id, edge.edge_id)
                    for edge in edges
                ),
            )
        else:
            crossings = []
            for index, first in enumerate(edges):
                if first.from_node_id not in positions or first.to_node_id not in positions:
                    continue
                for second in edges[index + 1:]:
                    if second.from_node_id not in positions or second.to_node_id not in positions:
                        continue
                    if len({
                        first.from_node_id,
                        first.to_node_id,
                        second.from_node_id,
                        second.to_node_id,
                    }) < 4:
                        continue
                    if any(
                        self.geometry.segments_intersect(a1, a2, b1, b2)
                        for a1, a2 in self._edge_segments(first, positions, edge_shapes)
                        for b1, b2 in self._edge_segments(second, positions, edge_shapes)
                    ):
                        crossings.append((first.edge_id, second.edge_id))
        return tuple(
            ConstraintViolation(
                "layout_state_route_crossing_failure",
                f"State {state_index} has a visible crossing between roads "
                f"'{first}' and '{second}'.",
                edge_id=first,
            )
            for first, second in crossings
        )

    def _node_road_clearance(
        self,
        graph: LayoutGraph,
        edges: tuple[LayoutGraphEdge, ...],
        positions: dict[str, tuple[float, float]],
        state_index: int,
        edge_shapes: dict[str, str] | None = None,
    ) -> tuple[ConstraintViolation, ...]:
        issues: list[ConstraintViolation] = []
        for edge in edges:
            start = positions.get(edge.from_node_id)
            end = positions.get(edge.to_node_id)
            if start is None or end is None:
                continue
            for node in graph.nodes:
                if node.node_id in {edge.from_node_id, edge.to_node_id}:
                    continue
                point = positions.get(node.node_id)
                if point is None:
                    continue
                distance = min(
                    self._point_to_segment_distance(point, segment_start, segment_end)
                    for segment_start, segment_end in self._edge_segments(
                        edge,
                        positions,
                        edge_shapes,
                    )
                )
                if distance < self.thresholds.minimum_node_road_clearance:
                    issues.append(ConstraintViolation(
                        "layout_state_node_clearance_failure",
                        f"State {state_index} road '{edge.edge_id}' is {distance:.3f} "
                        f"from node '{node.node_id}'; minimum is "
                        f"{self.thresholds.minimum_node_road_clearance:.3f}.",
                        node_id=node.node_id,
                        edge_id=edge.edge_id,
                    ))
        return tuple(issues)

    @staticmethod
    def _edge_segments(
        edge: LayoutGraphEdge,
        positions: dict[str, tuple[float, float]],
        edge_shapes: dict[str, str] | None,
    ) -> tuple[
        tuple[tuple[float, float], tuple[float, float]],
        ...,
    ]:
        start = positions[edge.from_node_id]
        end = positions[edge.to_node_id]
        shape = (edge_shapes or {}).get(edge.edge_id)
        if shape not in {"horizontalFirst", "verticalFirst"}:
            return ((start, end),)
        bend = (
            (end[0], start[1])
            if shape == "horizontalFirst"
            else (start[0], end[1])
        )
        if bend in {start, end}:
            return ((start, end),)
        return ((start, bend), (bend, end))

    @staticmethod
    def _lock_indicators(
        edges: tuple[LayoutGraphEdge, ...],
        positions: dict[str, tuple[float, float]],
        overrides: dict[str, tuple[float, float]] | None = None,
    ) -> dict[str, tuple[float, float]]:
        indicators: dict[str, tuple[float, float]] = {}
        for edge in edges:
            if overrides is not None and edge.edge_id in overrides:
                indicators[edge.edge_id] = overrides[edge.edge_id]
                continue
            start = positions.get(edge.from_node_id)
            end = positions.get(edge.to_node_id)
            if start is None or end is None:
                continue
            indicators[edge.edge_id] = (
                (start[0] + end[0]) / 2,
                (start[1] + end[1]) / 2,
            )
        return indicators

    def _lock_indicator_clearance(
        self,
        graph: LayoutGraph,
        indicators: dict[str, tuple[float, float]],
        markers,
        positions: dict[str, tuple[float, float]],
        state_index: int,
    ) -> tuple[ConstraintViolation, ...]:
        issues: list[ConstraintViolation] = []
        edge_by_id = {edge.edge_id: edge for edge in graph.edges}
        for edge_id, indicator in indicators.items():
            edge = edge_by_id[edge_id]
            for node in graph.nodes:
                if node.node_id in {edge.from_node_id, edge.to_node_id}:
                    continue
                point = positions.get(node.node_id)
                if point is None:
                    continue
                distance = self._distance(indicator, point)
                if distance < self.thresholds.minimum_lock_node_clearance:
                    issues.append(ConstraintViolation(
                        "layout_state_lock_indicator_node_overlap",
                        f"State {state_index} lock indicator on '{edge_id}' is "
                        f"{distance:.3f} from node '{node.node_id}'.",
                        node_id=node.node_id,
                        edge_id=edge_id,
                    ))
            for marker in markers:
                distance = self._distance(indicator, marker.position)
                if distance < self.thresholds.minimum_lock_objective_clearance:
                    issues.append(ConstraintViolation(
                        "layout_state_lock_indicator_objective_overlap",
                        f"State {state_index} lock indicator on '{edge_id}' overlaps "
                        f"objective marker '{marker.objective_id}'.",
                        node_id=marker.node_id,
                        edge_id=edge_id,
                    ))
        return tuple(issues)

    def _active_switch_clearance(
        self,
        snapshot: LayoutStateSnapshot,
        markers,
        positions: dict[str, tuple[float, float]],
        bounds: BoundingBox,
    ) -> tuple[ConstraintViolation, ...]:
        issues: list[ConstraintViolation] = []
        for node_id in snapshot.active_switch_node_ids:
            point = positions.get(node_id)
            if point is None:
                continue
            for marker in markers:
                distance = self._distance(point, marker.position)
                if distance < self.thresholds.minimum_active_switch_objective_clearance:
                    issues.append(ConstraintViolation(
                        "layout_state_active_switch_objective_overlap",
                        f"State {snapshot.state_index} active-switch indicator at "
                        f"'{node_id}' overlaps objective '{marker.objective_id}'.",
                        node_id=node_id,
                    ))
            if not self._inside_safe_bounds(point, bounds):
                issues.append(ConstraintViolation(
                    "layout_state_active_switch_camera_failure",
                    f"State {snapshot.state_index} active-switch indicator at "
                    f"'{node_id}' is outside the safe camera frame.",
                    node_id=node_id,
                ))
        return tuple(issues)

    def _camera_bounds(
        self,
        graph: LayoutGraph,
        markers,
        indicators: dict[str, tuple[float, float]],
        positions: dict[str, tuple[float, float]],
        bounds: BoundingBox,
        state_index: int,
    ) -> tuple[ConstraintViolation, ...]:
        issues: list[ConstraintViolation] = []
        for node in graph.nodes:
            point = positions.get(node.node_id)
            if point is not None and not self._inside_safe_bounds(point, bounds):
                issues.append(ConstraintViolation(
                    "layout_state_camera_bounds_failure",
                    f"State {state_index} node '{node.node_id}' is outside the safe "
                    "camera frame.",
                    node_id=node.node_id,
                ))
        for edge_id, point in indicators.items():
            if not self._inside_safe_bounds(point, bounds):
                issues.append(ConstraintViolation(
                    "layout_state_lock_indicator_camera_failure",
                    f"State {state_index} lock indicator on '{edge_id}' is outside "
                    "the safe camera frame.",
                    edge_id=edge_id,
                ))
        return tuple(issues)

    def _inside_safe_bounds(
        self,
        point: tuple[float, float],
        bounds: BoundingBox,
    ) -> bool:
        margin = self.thresholds.camera_margin
        return (
            bounds.min_x + margin <= point[0] <= bounds.max_x - margin
            and bounds.min_y + margin <= point[1] <= bounds.max_y - margin
        )

    @staticmethod
    def _distance(
        first: tuple[float, float],
        second: tuple[float, float],
    ) -> float:
        return math.hypot(first[0] - second[0], first[1] - second[1])

    @classmethod
    def _point_to_segment_distance(
        cls,
        point: tuple[float, float],
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> float:
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        denominator = (dx * dx) + (dy * dy)
        if denominator == 0:
            return cls._distance(point, start)
        scale = max(0.0, min(1.0, (
            ((point[0] - start[0]) * dx) + ((point[1] - start[1]) * dy)
        ) / denominator))
        nearest = (start[0] + (scale * dx), start[1] + (scale * dy))
        return cls._distance(point, nearest)

    @staticmethod
    def _dedupe(
        issues: list[ConstraintViolation],
    ) -> tuple[ConstraintViolation, ...]:
        seen: set[tuple[str, str | None, str | None, str]] = set()
        result: list[ConstraintViolation] = []
        for issue in issues:
            key = (issue.code, issue.node_id, issue.edge_id, issue.message)
            if key in seen:
                continue
            seen.add(key)
            result.append(issue)
        return tuple(result)
