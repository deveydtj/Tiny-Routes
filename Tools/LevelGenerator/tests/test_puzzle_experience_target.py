from __future__ import annotations

import pytest

from app.models import PuzzleExperienceTarget


def _target(**overrides) -> PuzzleExperienceTarget:
    values = {
        "difficulty": " Hard ",
        "objective_count_range": (3, 5),
        "meaningful_decision_range": (5, 7),
        "planning_decision_minimum": 3,
        "adaptive_decision_minimum": 2,
        "dependency_depth_range": (3, 5),
        "state_change_range": (2, 3),
        "revisit_range": (1, 3),
        "successful_route_class_range": (1, 4),
        "recoverable_mistake_range": (2, 4),
        "fatal_mistake_cap": 2,
        "decision_window_targets": (1.45, 3.0),
        "allowed_mechanic_categories": ("objective_gate", "hub_revisit"),
        "layout_complexity_target": 0.75,
        "desired_solve_time_range": (20.0, 55.0),
    }
    values.update(overrides)
    return PuzzleExperienceTarget(**values)


def test_puzzle_experience_target_preserves_all_resolved_constraints() -> None:
    target = _target()

    assert target.difficulty == "hard"
    assert target.objective_count_range == (3, 5)
    assert target.meaningful_decision_range == (5, 7)
    assert target.planning_decision_minimum == 3
    assert target.adaptive_decision_minimum == 2
    assert target.dependency_depth_range == (3, 5)
    assert target.state_change_range == (2, 3)
    assert target.revisit_range == (1, 3)
    assert target.successful_route_class_range == (1, 4)
    assert target.recoverable_mistake_range == (2, 4)
    assert target.fatal_mistake_cap == 2
    assert target.decision_window_targets == (1.45, 3.0)
    assert target.allowed_mechanic_categories == ("objective_gate", "hub_revisit")
    assert target.layout_complexity_target == 0.75
    assert target.desired_solve_time_range == (20.0, 55.0)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("objective_count_range", (5, 3), "non-negative and ordered"),
        ("meaningful_decision_range", (1.0, 3), "values must be integers"),
        ("planning_decision_minimum", -1, "non-negative integer"),
        ("decision_window_targets", (2.0, 1.0), "non-negative and ordered"),
        ("layout_complexity_target", 1.1, "between 0.0 and 1.0"),
        ("desired_solve_time_range", (10.0, float("inf")), "finite numbers"),
    ],
)
def test_puzzle_experience_target_rejects_invalid_constraints(
    field_name: str,
    value,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _target(**{field_name: value})


def test_puzzle_experience_target_rejects_duplicate_mechanic_categories() -> None:
    with pytest.raises(ValueError, match="must be unique"):
        _target(allowed_mechanic_categories=("hub_revisit", "hub_revisit"))
