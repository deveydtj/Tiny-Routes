from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from ..models.layout_constraints import (
    BoundingBox,
    ConstraintViolation,
    RepairOperation,
    RepairOperationKind,
)
from ..models.layout_graph import LayoutCorridorKind
from ..models.layout_graph import LayoutGraph
from ..models.layout_result import LayoutResult
from .pre_post_state_layout_validation_service import (
    PrePostStateLayoutValidationService,
)
from .stateful_hub_spacing_service import StatefulHubSpacingService


ViolationEvaluator = Callable[
    [dict[str, tuple[float, float]], dict[str, str]], Iterable[ConstraintViolation]
]


@dataclass(frozen=True)
class LayoutRepairConfig:
    grid_size: float = 0.05
    maximum_attempts: int = 48


class LayoutRepairService:
    """Applies bounded, deterministic local changes without changing connectivity."""

    _severity = {
        "implicit_intersection_without_node": 100,
        "node_spacing_failure": 90,
        "switch_exit_overlap": 80,
        "road_proximity_failure": 70,
        "important_node_visibility_failure": 60,
        "portrait_safety_failure": 50,
        "layout_state_route_crossing_failure": 100,
        "layout_state_node_clearance_failure": 90,
        "layout_state_lock_indicator_node_overlap": 85,
        "layout_state_lock_indicator_objective_overlap": 85,
        "layout_state_active_switch_objective_overlap": 85,
        "objective_marker_overlap": 85,
        "objective_marker_stateful_hub_overlap": 85,
        "objective_marker_node_clearance_failure": 80,
        "objective_marker_road_clearance_failure": 80,
        "stateful_hub_outgoing_separation_failure": 80,
        "stateful_hub_return_exit_overlap": 80,
        "stateful_hub_exit_clearance_failure": 75,
        "stateful_hub_return_approach_clearance_failure": 75,
        "layout_state_camera_bounds_failure": 60,
        "layout_state_lock_indicator_camera_failure": 60,
        "layout_state_active_switch_camera_failure": 60,
        "objective_marker_camera_frame_failure": 60,
        "stateful_hub_camera_frame_failure": 60,
    }

    def __init__(self, config: LayoutRepairConfig | None = None) -> None:
        self.config = config or LayoutRepairConfig()

    def repair(
        self,
        layout: LayoutResult,
        graph: LayoutGraph,
        edge_shapes: dict[str, str],
        evaluate: ViolationEvaluator,
    ) -> LayoutResult:
        positions = dict(layout.positions)
        shapes = dict(edge_shapes)
        violations = self._rank(evaluate(positions, shapes))
        operations: list[RepairOperation] = list(layout.repair_operations)
        attempted_operations: list[RepairOperation] = list(layout.attempted_repair_operations)
        attempts = 0

        while violations and attempts < self.config.maximum_attempts:
            baseline = self._score(violations)
            accepted = False
            for operation, candidate_positions, candidate_shapes in self._candidates(
                graph, positions, shapes, violations[0]
            ):
                attempts += 1
                attempted_operations.append(operation)
                candidate_violations = self._rank(evaluate(candidate_positions, candidate_shapes))
                if self._score(candidate_violations) < baseline:
                    positions, shapes, violations = candidate_positions, candidate_shapes, candidate_violations
                    operations.append(operation)
                    accepted = True
                    break
                if attempts >= self.config.maximum_attempts:
                    break
            if not accepted:
                break

        return LayoutResult(
            positions=positions,
            edge_shapes=shapes,
            objective_marker_positions=dict(layout.objective_marker_positions),
            lock_indicator_positions=dict(layout.lock_indicator_positions),
            layers=layout.layers,
            switch_ports=layout.switch_ports,
            candidate_bend_points=layout.candidate_bend_points,
            violations=tuple(violations),
            repair_operations=tuple(operations),
            attempted_repair_operations=tuple(attempted_operations),
        )

    def repair_phase_aware(
        self,
        layout: LayoutResult,
        graph: LayoutGraph,
        edge_shapes: dict[str, str] | None = None,
        *,
        bounds: BoundingBox | None = None,
    ) -> LayoutResult:
        """Repair every objective-state overlay without mutating puzzle logic.

        Positions, bend order, and overlay anchors are copied for every candidate.
        The immutable ``LayoutGraph`` is only read, so node/edge identity,
        authored edge order, availability, and objective progression cannot be
        changed by a repair.
        """

        positions = dict(layout.positions)
        shapes = dict(edge_shapes if edge_shapes is not None else layout.edge_shapes)
        marker_positions = dict(layout.objective_marker_positions)
        lock_positions = dict(layout.lock_indicator_positions)
        validator = PrePostStateLayoutValidationService()
        hub_spacing = StatefulHubSpacingService()
        resolved_bounds = bounds or BoundingBox()

        def evaluate() -> list[ConstraintViolation]:
            state_result = validator.validate(
                graph,
                positions,
                bounds=resolved_bounds,
                objective_marker_positions=marker_positions,
                lock_indicator_positions=lock_positions,
                edge_shapes=shapes,
            )
            return self._rank((
                *state_result.violations,
                *hub_spacing.validate(graph, positions, bounds=resolved_bounds),
            ))

        violations = evaluate()
        operations = list(layout.repair_operations)
        attempted = list(layout.attempted_repair_operations)
        attempts = 0
        while violations and attempts < self.config.maximum_attempts:
            baseline = self._score(violations)
            accepted = False
            for operation, candidate in self._phase_candidates(
                graph,
                positions,
                shapes,
                marker_positions,
                lock_positions,
                violations[0],
            ):
                attempts += 1
                attempted.append(operation)
                (
                    candidate_positions,
                    candidate_shapes,
                    candidate_markers,
                    candidate_locks,
                ) = candidate
                state_result = validator.validate(
                    graph,
                    candidate_positions,
                    bounds=resolved_bounds,
                    objective_marker_positions=candidate_markers,
                    lock_indicator_positions=candidate_locks,
                    edge_shapes=candidate_shapes,
                )
                candidate_violations = self._rank((
                    *state_result.violations,
                    *hub_spacing.validate(
                        graph,
                        candidate_positions,
                        bounds=resolved_bounds,
                    ),
                ))
                if self._score(candidate_violations) < baseline:
                    positions = candidate_positions
                    shapes = candidate_shapes
                    marker_positions = candidate_markers
                    lock_positions = candidate_locks
                    violations = candidate_violations
                    operations.append(operation)
                    accepted = True
                    break
                if attempts >= self.config.maximum_attempts:
                    break
            if not accepted:
                break

        return LayoutResult(
            positions=positions,
            edge_shapes=shapes,
            objective_marker_positions=marker_positions,
            lock_indicator_positions=lock_positions,
            layers=layout.layers,
            switch_ports=layout.switch_ports,
            candidate_bend_points=layout.candidate_bend_points,
            violations=tuple(violations),
            repair_operations=tuple(operations),
            attempted_repair_operations=tuple(attempted),
        )

    def _rank(self, violations: Iterable[ConstraintViolation]) -> list[ConstraintViolation]:
        return sorted(
            violations,
            key=lambda item: (-self._severity.get(item.code, 10), item.code, item.node_id or "", item.edge_id or ""),
        )

    def _score(self, violations: Iterable[ConstraintViolation]) -> tuple[int, int]:
        values = list(violations)
        return (sum(self._severity.get(item.code, 10) for item in values), len(values))

    def _candidates(self, graph, positions, shapes, violation):
        step = self.config.grid_size
        node_ids = [violation.node_id] if violation.node_id in positions else sorted(positions)
        # One-cell moves, including moving a rejoin point, are the cheapest repairs.
        for node_id in node_ids:
            for dc, dr in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                candidate = dict(positions)
                x, y = candidate[node_id]
                candidate[node_id] = (round(x + dc * step, 4), round(y + dr * step, 4))
                kind = RepairOperationKind.MOVE_REJOIN if self._is_rejoin(graph, node_id) else RepairOperationKind.MOVE_NODE
                yield RepairOperation(kind, node_id, dc, dr, violation.code), candidate, dict(shapes)

        # Swap/mirror sibling lanes around each split.
        for node in sorted(graph.nodes, key=lambda item: item.node_id):
            children = sorted(node.outgoing_node_ids)
            if len(children) < 2 or any(child not in positions for child in children[:2]):
                continue
            candidate = dict(positions)
            first, second = children[:2]
            candidate[first], candidate[second] = candidate[second], candidate[first]
            yield RepairOperation(RepairOperationKind.SWAP_SIBLING_LANES, node.node_id, reason=violation.code), candidate, dict(shapes)
            mirrored = dict(positions)
            origin_x = positions[node.node_id][0]
            for child in children:
                x, y = mirrored[child]
                mirrored[child] = (round(2 * origin_x - x, 4), y)
            yield RepairOperation(RepairOperationKind.MIRROR_BRANCH, node.node_id, reason=violation.code), mirrored, dict(shapes)

        # Bend-order changes do not touch topology.
        for edge in sorted(graph.edges, key=lambda item: item.edge_id):
            candidate_shapes = dict(shapes)
            current = candidate_shapes.get(edge.edge_id, "horizontalFirst")
            candidate_shapes[edge.edge_id] = "verticalFirst" if current == "horizontalFirst" else "horizontalFirst"
            yield RepairOperation(RepairOperationKind.INSERT_BEND, edge.edge_id, reason=violation.code), dict(positions), candidate_shapes

        # Expand vertical spacing last because it affects the whole local drawing.
        if positions:
            center_y = sum(y for _, y in positions.values()) / len(positions)
            expanded = {
                node_id: (x, round(center_y + (y - center_y) * 1.1, 4))
                for node_id, (x, y) in positions.items()
            }
            yield RepairOperation(RepairOperationKind.EXPAND_LAYER, "layout", delta_row=1, reason=violation.code), expanded, dict(shapes)

    def _phase_candidates(
        self,
        graph: LayoutGraph,
        positions: dict[str, tuple[float, float]],
        shapes: dict[str, str],
        marker_positions: dict[str, tuple[float, float]],
        lock_positions: dict[str, tuple[float, float]],
        violation: ConstraintViolation,
    ):
        step = self.config.grid_size

        def result(candidate_positions=None, candidate_shapes=None, candidate_markers=None, candidate_locks=None):
            return (
                dict(candidate_positions if candidate_positions is not None else positions),
                dict(candidate_shapes if candidate_shapes is not None else shapes),
                dict(candidate_markers if candidate_markers is not None else marker_positions),
                dict(candidate_locks if candidate_locks is not None else lock_positions),
            )

        edge_by_id = {edge.edge_id: edge for edge in graph.edges}
        target_edge = edge_by_id.get(violation.edge_id or "")
        if target_edge is not None:
            if violation.code == "layout_state_route_crossing_failure":
                candidate = dict(shapes)
                current = candidate.get(target_edge.edge_id, "horizontalFirst")
                candidate[target_edge.edge_id] = (
                    "verticalFirst"
                    if current == "horizontalFirst"
                    else "horizontalFirst"
                )
                yield RepairOperation(
                    RepairOperationKind.CHANGE_BEND_ORDER,
                    target_edge.edge_id,
                    reason=violation.code,
                ), result(candidate_shapes=candidate)
            if "lock_indicator" in violation.code:
                start = positions.get(target_edge.from_node_id)
                end = positions.get(target_edge.to_node_id)
                if start is not None and end is not None:
                    anchor = lock_positions.get(
                        target_edge.edge_id,
                        ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2),
                    )
                    dx, dy = end[0] - start[0], end[1] - start[1]
                    offsets = (
                        ((-1, 0), (1, 0))
                        if abs(dx) < abs(dy)
                        else ((0, -1), (0, 1))
                    )
                    for dc, dr in offsets:
                        candidate = dict(lock_positions)
                        candidate[target_edge.edge_id] = (
                            round(anchor[0] + dc * step, 4),
                            round(anchor[1] + dr * step, 4),
                        )
                        yield RepairOperation(
                            RepairOperationKind.MOVE_LOCK_INDICATOR,
                            target_edge.edge_id,
                            dc,
                            dr,
                            violation.code,
                        ), result(candidate_locks=candidate)

        target_objectives = tuple(
            objective
            for objective in graph.objectives
            if objective.node_id == violation.node_id
        )
        if "objective" in violation.code:
            for objective in target_objectives:
                anchor = marker_positions.get(
                    objective.objective_id,
                    positions.get(objective.node_id),
                )
                if anchor is None:
                    continue
                for dc, dr in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    candidate = dict(marker_positions)
                    candidate[objective.objective_id] = (
                        round(anchor[0] + dc * step, 4),
                        round(anchor[1] + dr * step, 4),
                    )
                    yield RepairOperation(
                        RepairOperationKind.RELOCATE_OBJECTIVE_MARKER,
                        objective.objective_id,
                        dc,
                        dr,
                        violation.code,
                    ), result(candidate_markers=candidate)

        # Stateful hubs are moved first for hub- and active-switch-specific failures.
        hub_ids = [
            node.node_id
            for node in sorted(graph.nodes, key=lambda item: item.node_id)
            if node.is_revisited_hub and node.node_id in positions
        ]
        if violation.node_id in hub_ids:
            hub_ids = [violation.node_id, *(item for item in hub_ids if item != violation.node_id)]
        for hub_id in hub_ids:
            for dc, dr in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                candidate = dict(positions)
                x, y = candidate[hub_id]
                candidate[hub_id] = (round(x + dc * step, 4), round(y + dr * step, 4))
                yield RepairOperation(
                    RepairOperationKind.MOVE_STATEFUL_HUB,
                    hub_id,
                    dc,
                    dr,
                    violation.code,
                ), result(candidate_positions=candidate)

        # Widen later-phase return approaches by moving the approach endpoint away.
        for edge in self._return_edges(graph):
            if edge.from_node_id not in positions or edge.to_node_id not in positions:
                continue
            start = positions[edge.from_node_id]
            end = positions[edge.to_node_id]
            dx = start[0] - end[0]
            dy = start[1] - end[1]
            dc, dr = (1 if dx >= 0 else -1, 0) if abs(dx) >= abs(dy) else (0, 1 if dy >= 0 else -1)
            candidate = dict(positions)
            candidate[edge.from_node_id] = (
                round(start[0] + dc * step, 4),
                round(start[1] + dr * step, 4),
            )
            yield RepairOperation(
                RepairOperationKind.WIDEN_RETURN_LANE,
                edge.edge_id,
                dc,
                dr,
                violation.code,
            ), result(candidate_positions=candidate)

        # Objective artwork can move independently of its gameplay node.
        objectives = sorted(graph.objectives, key=lambda item: (item.phase_index, item.objective_id))
        if violation.node_id is not None:
            objectives.sort(key=lambda item: item.node_id != violation.node_id)
        for objective in objectives:
            anchor = marker_positions.get(
                objective.objective_id,
                positions.get(objective.node_id),
            )
            if anchor is None:
                continue
            for dc, dr in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                candidate = dict(marker_positions)
                candidate[objective.objective_id] = (
                    round(anchor[0] + dc * step, 4),
                    round(anchor[1] + dr * step, 4),
                )
                yield RepairOperation(
                    RepairOperationKind.RELOCATE_OBJECTIVE_MARKER,
                    objective.objective_id,
                    dc,
                    dr,
                    violation.code,
                ), result(candidate_markers=candidate)

        # Lock icons slide perpendicular to their road, away from crossings/nodes.
        edges = sorted(graph.edges, key=lambda item: item.edge_id)
        if violation.edge_id is not None:
            edges.sort(key=lambda item: item.edge_id != violation.edge_id)
        for edge in edges:
            start = positions.get(edge.from_node_id)
            end = positions.get(edge.to_node_id)
            if start is None or end is None:
                continue
            anchor = lock_positions.get(
                edge.edge_id,
                ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2),
            )
            dx, dy = end[0] - start[0], end[1] - start[1]
            offsets = ((-1, 0), (1, 0)) if abs(dx) < abs(dy) else ((0, -1), (0, 1))
            for dc, dr in offsets:
                candidate = dict(lock_positions)
                candidate[edge.edge_id] = (
                    round(anchor[0] + dc * step, 4),
                    round(anchor[1] + dr * step, 4),
                )
                yield RepairOperation(
                    RepairOperationKind.MOVE_LOCK_INDICATOR,
                    edge.edge_id,
                    dc,
                    dr,
                    violation.code,
                ), result(candidate_locks=candidate)

        # Swap complete branch lanes while retaining authored edge order.
        for node in sorted(graph.nodes, key=lambda item: item.node_id):
            children = tuple(child for child in node.outgoing_node_ids if child in positions)
            if len(children) < 2:
                continue
            candidate = dict(positions)
            first, second = children[:2]
            candidate[first], candidate[second] = candidate[second], candidate[first]
            yield RepairOperation(
                RepairOperationKind.SWAP_BRANCH_LANES,
                node.node_id,
                reason=violation.code,
            ), result(candidate_positions=candidate)

        # Separate phase-exclusive nodes vertically; shared hubs remain fixed.
        phase_count = graph.objective_phase_count
        if phase_count > 1:
            candidate = dict(positions)
            changed = False
            for node in graph.nodes:
                if node.node_id not in candidate or len(node.objective_phase_indices) != 1:
                    continue
                phase = node.objective_phase_indices[0]
                offset = (phase - ((phase_count - 1) / 2)) * step
                if offset:
                    x, y = candidate[node.node_id]
                    candidate[node.node_id] = (x, round(y + offset, 4))
                    changed = True
            if changed:
                yield RepairOperation(
                    RepairOperationKind.EXPAND_PHASE_SPACING,
                    "layout",
                    delta_row=1,
                    reason=violation.code,
                ), result(candidate_positions=candidate)

        # Bend order is visual geometry only and never changes edge identity/order.
        for edge in edges:
            candidate = dict(shapes)
            current = candidate.get(edge.edge_id, "horizontalFirst")
            candidate[edge.edge_id] = (
                "verticalFirst" if current == "horizontalFirst" else "horizontalFirst"
            )
            yield RepairOperation(
                RepairOperationKind.CHANGE_BEND_ORDER,
                edge.edge_id,
                reason=violation.code,
            ), result(candidate_shapes=candidate)

    @staticmethod
    def _return_edges(graph: LayoutGraph):
        hub_ids = set(graph.stateful_hub_node_ids)
        return tuple(
            edge
            for edge in sorted(graph.edges, key=lambda item: item.edge_id)
            if edge.to_node_id in hub_ids
            and (
                LayoutCorridorKind.RECOVERY in edge.corridor_kinds
                or any(phase > 0 for phase in edge.objective_phase_indices)
            )
        )

    @staticmethod
    def _is_rejoin(graph: LayoutGraph, node_id: str) -> bool:
        return next((len(node.incoming_node_ids) > 1 for node in graph.nodes if node.node_id == node_id), False)
