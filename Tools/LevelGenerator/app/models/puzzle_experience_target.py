"""Strategic and presentation targets for a generated puzzle experience."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


IntRange = tuple[int, int]
FloatRange = tuple[float, float]


@dataclass(frozen=True)
class PuzzleExperienceTarget:
    """Difficulty-resolved constraints that a blueprint must satisfy.

    This model intentionally describes player-facing outcomes rather than graph
    structure. Blueprint generation can therefore reject weak intent before it
    spends work on motif composition, layout, or runtime scheduling.
    """

    difficulty: str
    objective_count_range: IntRange
    meaningful_decision_range: IntRange
    planning_decision_minimum: int
    adaptive_decision_minimum: int
    dependency_depth_range: IntRange
    state_change_range: IntRange
    revisit_range: IntRange
    successful_route_class_range: IntRange
    recoverable_mistake_range: IntRange
    fatal_mistake_cap: int
    decision_window_targets: FloatRange
    allowed_mechanic_categories: tuple[str, ...]
    layout_complexity_target: float
    desired_solve_time_range: FloatRange

    def __post_init__(self) -> None:
        difficulty = self.difficulty.strip().lower()
        if not difficulty:
            raise ValueError("difficulty must not be empty")
        object.__setattr__(self, "difficulty", difficulty)

        for field_name in (
            "objective_count_range",
            "meaningful_decision_range",
            "dependency_depth_range",
            "state_change_range",
            "revisit_range",
            "successful_route_class_range",
            "recoverable_mistake_range",
        ):
            self._validate_int_range(field_name, getattr(self, field_name))

        for field_name in (
            "planning_decision_minimum",
            "adaptive_decision_minimum",
            "fatal_mistake_cap",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")

        meaningful_maximum = self.meaningful_decision_range[1]
        if self.planning_decision_minimum > meaningful_maximum:
            raise ValueError(
                "planning_decision_minimum cannot exceed meaningful decision maximum"
            )
        if self.adaptive_decision_minimum > meaningful_maximum:
            raise ValueError(
                "adaptive_decision_minimum cannot exceed meaningful decision maximum"
            )

        self._validate_float_range("decision_window_targets", self.decision_window_targets)
        self._validate_float_range("desired_solve_time_range", self.desired_solve_time_range)

        mechanics = tuple(category.strip() for category in self.allowed_mechanic_categories)
        if any(not category for category in mechanics):
            raise ValueError("allowed_mechanic_categories cannot contain empty values")
        if len(mechanics) != len(set(mechanics)):
            raise ValueError("allowed_mechanic_categories must be unique")
        object.__setattr__(self, "allowed_mechanic_categories", mechanics)

        complexity = self.layout_complexity_target
        if (
            isinstance(complexity, bool)
            or not isinstance(complexity, (int, float))
            or not isfinite(float(complexity))
            or not 0.0 <= float(complexity) <= 1.0
        ):
            raise ValueError("layout_complexity_target must be between 0.0 and 1.0")
        object.__setattr__(self, "layout_complexity_target", float(complexity))

    @staticmethod
    def _validate_int_range(field_name: str, value: IntRange) -> None:
        if not isinstance(value, tuple) or len(value) != 2:
            raise ValueError(f"{field_name} must be a two-item tuple")
        lower, upper = value
        if any(not isinstance(item, int) or isinstance(item, bool) for item in value):
            raise ValueError(f"{field_name} values must be integers")
        if lower < 0 or upper < lower:
            raise ValueError(f"{field_name} must be non-negative and ordered")

    @staticmethod
    def _validate_float_range(field_name: str, value: FloatRange) -> None:
        if not isinstance(value, tuple) or len(value) != 2:
            raise ValueError(f"{field_name} must be a two-item tuple")
        if any(
            isinstance(item, bool)
            or not isinstance(item, (int, float))
            or not isfinite(float(item))
            for item in value
        ):
            raise ValueError(f"{field_name} values must be finite numbers")
        lower, upper = (float(value[0]), float(value[1]))
        if lower < 0.0 or upper < lower:
            raise ValueError(f"{field_name} must be non-negative and ordered")
