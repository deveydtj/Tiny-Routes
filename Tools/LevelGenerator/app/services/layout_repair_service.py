from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from ..models.layout_constraints import ConstraintViolation, RepairOperation, RepairOperationKind
from ..models.layout_graph import LayoutGraph
from ..models.layout_result import LayoutResult


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
            layers=layout.layers,
            switch_ports=layout.switch_ports,
            candidate_bend_points=layout.candidate_bend_points,
            violations=tuple(violations),
            repair_operations=tuple(operations),
            attempted_repair_operations=tuple(attempted_operations),
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

    @staticmethod
    def _is_rejoin(graph: LayoutGraph, node_id: str) -> bool:
        return next((len(node.incoming_node_ids) > 1 for node in graph.nodes if node.node_id == node_id), False)
