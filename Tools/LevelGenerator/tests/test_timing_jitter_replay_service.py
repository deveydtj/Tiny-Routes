from __future__ import annotations

from tiny_routes_core.models import (
    LevelDocument,
    LevelRules,
    RouteEdge,
    RouteGraph,
    RouteNode,
    SwitchInteractionMode,
)

from app.models.runtime_solution_search import RuntimeSolutionAction
from app.services.timing_jitter_replay_service import TimingJitterReplayService


def _level() -> LevelDocument:
    return LevelDocument(
        "jitter_fixture",
        "Jitter Fixture",
        RouteGraph(
            [
                RouteNode("start", 0, 0, ["to_switch"]),
                RouteNode("switch", 2, 0, ["to_dead", "to_package"]),
                RouteNode("dead", 2, 1, []),
                RouteNode("package", 3, 0, ["to_destination"]),
                RouteNode("destination", 4, 0, []),
            ],
            [
                RouteEdge("to_switch", "start", "switch"),
                RouteEdge("to_dead", "switch", "dead"),
                RouteEdge("to_package", "switch", "package"),
                RouteEdge("to_destination", "package", "destination"),
            ],
        ),
        "start",
        "package",
        "destination",
        15,
        1,
        rules=LevelRules(SwitchInteractionMode.LIVE_LOOKAHEAD, 1.35, 0.12),
        _rules_present=True,
    )


def test_jitter_replay_covers_timestamp_frame_and_speed_variations() -> None:
    report = TimingJitterReplayService().replay(
        _level(),
        (RuntimeSolutionAction(1.3, "switch", "to_package"),),
    )

    assert report.passed
    scenario_ids = {scenario.scenario_id for scenario in report.scenarios}
    assert {"uniform_minus_100ms", "uniform_plus_100ms"} <= scenario_ids
    assert {"frame_60hz_floor", "frame_30hz_ceil"} <= scenario_ids
    assert any(scenario_id.startswith("speed_minus") for scenario_id in scenario_ids)
    assert all(scenario.failure_reason is None for scenario in report.scenarios)


def test_jitter_replay_rejects_a_nominally_legal_edge_of_window_tap() -> None:
    report = TimingJitterReplayService().replay(
        _level(),
        (RuntimeSolutionAction(0.66, "switch", "to_package"),),
    )

    assert not report.passed
    assert report.failure_reason == "solution_jitter_failure"
    assert any(
        scenario.scenario_id == "uniform_minus_100ms" and not scenario.passed
        for scenario in report.scenarios
    )
    assert all(reason.startswith("solution_jitter_failure:") for reason in report.rejection_reasons)
