from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DecisionProfile:
    """Measured strategic and runtime properties of a generated puzzle."""

    required_decision_count: int = 0
    unique_switch_count: int = 0
    repeated_switch_decision_count: int = 0
    switch_state_change_on_revisit_count: int = 0
    ordered_dependency_count: int = 0
    independent_decision_ratio: float = 0.0
    equivalent_minimum_solution_count: int = 0
    successful_alternate_route_count: int = 0
    failure_route_count: int = 0
    failure_outcome_types: tuple[str, ...] = ()
    dead_end_choice_count: int = 0
    destination_before_package_choice_count: int = 0
    recoverable_mistake_count: int = 0
    route_revisit_count: int = 0
    package_phase_decisions_before: int = 0
    package_phase_decisions_after: int = 0
    minimum_window_seconds: float | None = None
    average_window_seconds: float | None = None
    minimum_decision_spacing_seconds: float | None = None
    average_decision_spacing_seconds: float | None = None
    multiple_taps_in_window_count: int = 0
    front_loaded_legacy_solution_possible: bool = False
    no_op_or_equivalent_choice_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["failure_outcome_types"] = list(self.failure_outcome_types)
        return payload
