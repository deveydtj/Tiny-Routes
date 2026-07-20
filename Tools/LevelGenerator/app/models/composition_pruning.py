"""Constraint and evidence models for partial composition pruning."""

from __future__ import annotations

from dataclasses import dataclass

from .puzzle_blueprint import PuzzleBlueprint


IntRange = tuple[int, int]


def _range(value: IntRange, field_name: str) -> IntRange:
    if not isinstance(value, tuple) or len(value) != 2:
        raise ValueError(f"{field_name} must be a two-item tuple")
    lower, upper = value
    if any(not isinstance(item, int) or isinstance(item, bool) for item in value):
        raise ValueError(f"{field_name} values must be integers")
    if lower < 0 or upper < lower:
        raise ValueError(f"{field_name} must be non-negative and ordered")
    return value


@dataclass(frozen=True)
class CompositionStrategicConstraints:
    """Hard bounds used while a blueprint is being composed."""

    blueprint_id: str
    objective_count_range: IntRange
    meaningful_decision_range: IntRange
    adaptive_decision_minimum: int
    dependency_depth_range: IntRange
    revisit_range: IntRange
    recovery_range: IntRange
    switch_count_range: IntRange
    maximum_switch_degree: int
    layout_width_range: IntRange
    layout_height_range: IntRange
    adaptive_decision_ids: tuple[str, ...] = ()
    revisit_decision_ids: tuple[str, ...] = ()
    maximum_switches_per_remaining_decision: int = 2

    def __post_init__(self) -> None:
        if not isinstance(self.blueprint_id, str) or not self.blueprint_id.strip():
            raise ValueError("blueprint_id must not be empty")
        object.__setattr__(self, "blueprint_id", self.blueprint_id.strip())
        for field_name in (
            "objective_count_range",
            "meaningful_decision_range",
            "dependency_depth_range",
            "revisit_range",
            "recovery_range",
            "switch_count_range",
            "layout_width_range",
            "layout_height_range",
        ):
            object.__setattr__(
                self,
                field_name,
                _range(getattr(self, field_name), field_name),
            )
        for field_name in (
            "adaptive_decision_minimum",
            "maximum_switch_degree",
            "maximum_switches_per_remaining_decision",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        if self.maximum_switch_degree < 2:
            raise ValueError("maximum_switch_degree must be at least two")
        if self.maximum_switches_per_remaining_decision < 1:
            raise ValueError(
                "maximum_switches_per_remaining_decision must be at least one"
            )
        for field_name in ("adaptive_decision_ids", "revisit_decision_ids"):
            values = tuple(value.strip() for value in getattr(self, field_name))
            if any(not value for value in values):
                raise ValueError(f"{field_name} cannot contain empty values")
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} must be unique")
            object.__setattr__(self, field_name, values)

    @classmethod
    def from_blueprint(
        cls,
        blueprint: PuzzleBlueprint,
        *,
        switch_count_range: IntRange,
        maximum_switch_degree: int,
        layout_width_range: IntRange,
        layout_height_range: IntRange,
    ) -> "CompositionStrategicConstraints":
        if not isinstance(blueprint, PuzzleBlueprint):
            raise TypeError("blueprint must be a PuzzleBlueprint")
        issues = blueprint.validate()
        if issues:
            raise ValueError(f"blueprint is invalid: {issues[0]}")
        target = blueprint.experience_target
        return cls(
            blueprint_id=blueprint.id,
            objective_count_range=target.objective_count_range,
            meaningful_decision_range=target.meaningful_decision_range,
            adaptive_decision_minimum=target.adaptive_decision_minimum,
            dependency_depth_range=target.dependency_depth_range,
            revisit_range=target.revisit_range,
            recovery_range=target.recoverable_mistake_range,
            switch_count_range=switch_count_range,
            maximum_switch_degree=maximum_switch_degree,
            layout_width_range=layout_width_range,
            layout_height_range=layout_height_range,
            adaptive_decision_ids=blueprint.adaptive_decision_ids,
            revisit_decision_ids=blueprint.required_revisit_decision_ids,
        )


@dataclass(frozen=True)
class CompositionPruningAssessment:
    """Deterministic reasons for retaining or pruning one partial state."""

    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        reasons = tuple(reason.strip() for reason in self.rejection_reasons)
        if any(not reason for reason in reasons):
            raise ValueError("rejection_reasons cannot contain empty values")
        object.__setattr__(self, "rejection_reasons", tuple(sorted(set(reasons))))

    @property
    def should_prune(self) -> bool:
        return bool(self.rejection_reasons)

    @property
    def is_feasible(self) -> bool:
        return not self.should_prune
