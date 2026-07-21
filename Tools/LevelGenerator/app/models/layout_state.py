"""Typed visual state used by phase-aware layout validation."""

from __future__ import annotations

from dataclasses import dataclass

from .layout_constraints import ConstraintViolation


@dataclass(frozen=True)
class ObjectiveMarkerPlacement:
    objective_id: str
    node_id: str
    phase_index: int
    status: str
    position: tuple[float, float]


@dataclass(frozen=True)
class LayoutStateSnapshot:
    """Player-visible layout state before the next ordered objective."""

    state_index: int
    completed_objective_ids: tuple[str, ...]
    active_objective_id: str | None
    visible_objective_ids: tuple[str, ...]
    available_edge_ids: tuple[str, ...]
    locked_edge_ids: tuple[str, ...]
    consumed_edge_ids: tuple[str, ...]
    active_switch_node_ids: tuple[str, ...]


@dataclass(frozen=True)
class LayoutStateValidation:
    snapshot: LayoutStateSnapshot
    objective_markers: tuple[ObjectiveMarkerPlacement, ...]
    lock_indicator_positions: tuple[tuple[str, tuple[float, float]], ...]
    violations: tuple[ConstraintViolation, ...]

    @property
    def is_valid(self) -> bool:
        return not self.violations


@dataclass(frozen=True)
class PrePostStateLayoutValidationResult:
    """Validation evidence for the initial and every post-objective state."""

    states: tuple[LayoutStateValidation, ...]

    @property
    def violations(self) -> tuple[ConstraintViolation, ...]:
        return tuple(
            violation
            for state in self.states
            for violation in state.violations
        )

    @property
    def is_valid(self) -> bool:
        return bool(self.states) and not self.violations
