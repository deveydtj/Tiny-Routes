"""Typed production evidence for runtime input and state-readability timing."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


def _finite_non_negative(value: float, field_name: str) -> float:
    normalized = float(value)
    if not isfinite(normalized) or normalized < 0.0:
        raise ValueError(f"{field_name} must be finite and non-negative")
    return round(normalized, 9)


@dataclass(frozen=True)
class RapidMultiTapEncounter:
    node_id: str
    visit_index: int
    required_tap_count: int
    tap_times_seconds: tuple[float, ...]
    burst_duration_seconds: float
    opening_safety_margin_seconds: float
    closing_safety_margin_seconds: float
    required_safety_margin_seconds: float
    within_per_encounter_limit: bool
    preserves_safety_margin: bool


@dataclass(frozen=True)
class StateChangeVisibilityEvidence:
    state_change_time_seconds: float
    next_window_open_seconds: float
    visibility_seconds: float
    required_visibility_seconds: float
    next_decision_node_id: str
    next_decision_visit_index: int
    completed_objective_ids: tuple[str, ...] = ()
    opened_edge_ids: tuple[str, ...] = ()
    closed_edge_ids: tuple[str, ...] = ()
    consumed_edge_ids: tuple[str, ...] = ()
    active_objective_id: str | None = None
    passed: bool = True


@dataclass(frozen=True)
class RuntimeTimingAccessibilityReport:
    difficulty: str
    passed: bool
    rapid_multi_tap_encounter_cap: int
    maximum_taps_per_burst: int
    minimum_state_change_visibility_seconds: float
    rapid_multi_tap_encounters: tuple[RapidMultiTapEncounter, ...] = ()
    state_change_visibility: tuple[StateChangeVisibilityEvidence, ...] = ()
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        difficulty = self.difficulty.strip().lower()
        if not difficulty:
            raise ValueError("difficulty must not be empty")
        if (
            not isinstance(self.rapid_multi_tap_encounter_cap, int)
            or isinstance(self.rapid_multi_tap_encounter_cap, bool)
            or self.rapid_multi_tap_encounter_cap < 0
        ):
            raise ValueError("rapid_multi_tap_encounter_cap must be non-negative")
        if (
            not isinstance(self.maximum_taps_per_burst, int)
            or isinstance(self.maximum_taps_per_burst, bool)
            or self.maximum_taps_per_burst < 2
        ):
            raise ValueError("maximum_taps_per_burst must be at least two")
        minimum_visibility = _finite_non_negative(
            self.minimum_state_change_visibility_seconds,
            "minimum_state_change_visibility_seconds",
        )
        reasons = tuple(dict.fromkeys(self.rejection_reasons))
        if self.passed == bool(reasons):
            raise ValueError("passed must be the inverse of rejection_reasons")
        object.__setattr__(self, "difficulty", difficulty)
        object.__setattr__(
            self,
            "minimum_state_change_visibility_seconds",
            minimum_visibility,
        )
        object.__setattr__(
            self,
            "rapid_multi_tap_encounters",
            tuple(self.rapid_multi_tap_encounters),
        )
        object.__setattr__(
            self,
            "state_change_visibility",
            tuple(self.state_change_visibility),
        )
        object.__setattr__(self, "rejection_reasons", reasons)

    @property
    def failure_reason(self) -> str | None:
        return self.rejection_reasons[0] if self.rejection_reasons else None
