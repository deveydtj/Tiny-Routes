from __future__ import annotations

import pytest

from app.services.difficulty_service import DifficultyService
from app.services.solution_builder_service import SolutionBuilderService
from .late_tap_chain_fixture import (
    late_tap_chain_new_times,
    late_tap_chain_positions,
    late_tap_chain_route,
    late_tap_chain_route_edge_shapes,
    late_tap_chain_tap_nodes,
)


def test_no_tap_solution() -> None:
    solution = SolutionBuilderService().build_no_tap_solution(
        "level_012",
        solution_route=["start", "package", "destination"],
    )

    assert solution.levelID == "level_012"
    assert solution.maxTaps == 0
    assert solution.requiresWithinTimeLimit is True
    assert solution.isPlaceholder is None
    assert solution.actions == []
    assert solution._extra["metadata"]["solutionRoute"] == ["start", "package", "destination"]


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


def test_build_route_timed_tap_solution_schedules_before_switch_arrivals() -> None:
    preset = DifficultyService().get_preset("easy")
    solution = SolutionBuilderService().build_route_timed_tap_solution(
        "level_001",
        ["switch_a", "switch_b"],
        ["start", "switch_a", "package", "switch_b", "destination"],
        {
            "start": (0.0, 0.0),
            "switch_a": (1.0, 0.0),
            "package": (2.0, 0.0),
            "switch_b": (3.0, 0.0),
            "destination": (4.0, 0.0),
        },
        preset,
        "test",
        route_edge_ids_by_pair={
            ("start", "switch_a"): "e_start_switch_a",
            ("switch_a", "package"): "e_switch_a_package",
            ("package", "switch_b"): "e_package_switch_b",
            ("switch_b", "destination"): "e_switch_b_destination",
        },
        outgoing_edge_ids_by_node={
            "switch_a": ["e_switch_a_dead_end", "e_switch_a_package"],
            "switch_b": ["e_switch_b_dead_end", "e_switch_b_destination"],
        },
    )

    assert [action.timeSeconds for action in solution.actions] == [0.65, 2.65]
    assert solution._extra["metadata"]["solutionRoute"] == [
        "start",
        "switch_a",
        "package",
        "switch_b",
        "destination",
    ]
    assert solution._extra["metadata"]["requiredTapOrder"] == ["switch_a", "switch_b"]
    assert solution.actions[0]._extra["reason"] == "Rotate switch 'switch_a' toward 'package' before arrival."
    assert solution.actions[0]._extra["expectedEdgeAfterTap"] == "e_switch_a_package"
    assert solution.actions[0]._extra["switchStateBeforeTap"] == "e_switch_a_dead_end"
    assert solution.actions[0]._extra["switchStateAfterTap"] == "e_switch_a_package"
    assert solution.actions[0]._extra["reactionWindowSeconds"] == 0.35


def test_build_route_timed_tap_solution_uses_rounded_path_timing_for_late_tap_chain() -> None:
    preset = DifficultyService().get_preset("hard")

    solution = SolutionBuilderService().build_route_timed_tap_solution(
        "level_028",
        late_tap_chain_tap_nodes(),
        late_tap_chain_route(),
        late_tap_chain_positions(),
        preset,
        "test",
        route_edge_shapes=late_tap_chain_route_edge_shapes(),
    )

    assert [action.timeSeconds for action in solution.actions] == late_tap_chain_new_times()
