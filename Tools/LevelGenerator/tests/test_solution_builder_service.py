from __future__ import annotations

import pytest

from app.services.difficulty_service import DifficultyService
from app.services.solution_builder_service import SolutionBuilderService


def test_no_tap_solution() -> None:
    solution = SolutionBuilderService().build_no_tap_solution("level_012")

    assert solution.levelID == "level_012"
    assert solution.maxTaps == 0
    assert solution.requiresWithinTimeLimit is True
    assert solution.isPlaceholder is None
    assert solution.actions == []


def test_tap_solution_sorts_actions_and_sets_max_taps() -> None:
    preset = DifficultyService().get_preset("easy")
    solution = SolutionBuilderService().build_tap_solution(
        "level_012",
        ["switch_b", "switch_a"],
        preset,
        "Tap two switches.",
        times=[0.8, 0.4],
    )

    assert solution.maxTaps == 2
    assert [action.timeSeconds for action in solution.actions] == [0.4, 0.8]
    assert [action.tapNodeID for action in solution.actions] == ["switch_a", "switch_b"]


def test_repeated_tap_solution_rejects_too_close_times() -> None:
    preset = DifficultyService().get_preset("medium")

    with pytest.raises(ValueError):
        SolutionBuilderService().build_tap_solution(
            "level_012",
            ["alpha", "alpha"],
            preset,
            "Repeat alpha.",
            times=[0.4, 0.5],
        )
