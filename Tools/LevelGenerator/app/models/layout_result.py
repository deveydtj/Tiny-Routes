from __future__ import annotations

from dataclasses import dataclass, field

from .layout_constraints import ConstraintViolation, RepairOperation, ReservedIconClearance
from .layout_graph import CandidateBendPoint, GridCell, Lane, SwitchPortDirection


@dataclass(frozen=True)
class LayerAssignment:
    node_id: str
    logical_layer: int
    lane: Lane
    grid_cell: GridCell


@dataclass(frozen=True)
class LayoutLayerResult:
    assignments: tuple[LayerAssignment, ...]
    return_edge_ids: tuple[str, ...] = ()
    reserved_icon_clearances: tuple[ReservedIconClearance, ...] = ()
    violations: tuple[ConstraintViolation, ...] = ()

    @property
    def by_node_id(self) -> dict[str, LayerAssignment]:
        return {assignment.node_id: assignment for assignment in self.assignments}


@dataclass(frozen=True)
class LayoutResult:
    positions: dict[str, tuple[float, float]]
    layers: LayoutLayerResult | None = None
    switch_ports: dict[str, tuple[SwitchPortDirection, ...]] = field(default_factory=dict)
    candidate_bend_points: tuple[CandidateBendPoint, ...] = ()
    violations: tuple[ConstraintViolation, ...] = ()
    repair_operations: tuple[RepairOperation, ...] = ()
    attempted_repair_operations: tuple[RepairOperation, ...] = ()
    edge_shapes: dict[str, str] = field(default_factory=dict)
    objective_marker_positions: dict[str, tuple[float, float]] = field(default_factory=dict)
    lock_indicator_positions: dict[str, tuple[float, float]] = field(default_factory=dict)


@dataclass(frozen=True)
class LayoutPlanResult:
    strategy: str
    variant: str
    positions: dict[str, tuple[float, float]]
    validation_issues: tuple[ConstraintViolation, ...]
    metadata: dict[str, object]

    @property
    def is_valid(self) -> bool:
        return not self.validation_issues
