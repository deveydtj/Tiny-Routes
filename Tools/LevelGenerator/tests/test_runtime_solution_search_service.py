from __future__ import annotations

from tiny_routes_core.models import (
    LevelDocument, LevelRules, RouteEdge, RouteGraph, RouteNode, SwitchInteractionMode,
)

from app.models.abstract_puzzle_solution import AbstractPuzzleSolutionMetadata
from app.services.runtime_solution_search_service import RuntimeSolutionSearchService
from app.services.solution_builder_service import SolutionBuilderService
from app.services.strategy_search_service import StrategySearchService


def _metadata(decisions: tuple[str, ...], path: tuple[str, ...]) -> AbstractPuzzleSolutionMetadata:
    return AbstractPuzzleSolutionMetadata(
        decision_node_ids=decisions,
        solution_switch_states=(),
        required_path=path,
        alternate_path_count=0,
        dead_end_count=1,
        failure_path_count=1,
        false_route_count=1,
        loop_count=0,
        minimum_required_decisions=len(decisions),
        optional_tap_count=0,
        repeated_switch_usage=len(set(decisions)) < len(decisions),
        package_before_destination=True,
    )


def _level(*, outgoing_targets: tuple[str, ...] = ("dead", "package"), lookahead: float = 1.35) -> LevelDocument:
    nodes = [
        RouteNode("start", 0, 0, ["start_switch"]),
        RouteNode("switch", 2, 0, [f"switch_{target}" for target in outgoing_targets]),
        RouteNode("package", 3, 0, ["package_destination"]),
        RouteNode("destination", 4, 0, []),
        RouteNode("dead", 2, 1, []),
    ]
    edges = [
        RouteEdge("start_switch", "start", "switch"),
        *(RouteEdge(f"switch_{target}", "switch", target) for target in outgoing_targets),
        RouteEdge("package_destination", "package", "destination"),
    ]
    for target in outgoing_targets:
        if target not in {node.id for node in nodes}:
            nodes.append(RouteNode(target, 2, len(nodes), []))
    return LevelDocument(
        "level_test", "Test", RouteGraph(nodes, edges), "start", "package", "destination", 15, 3,
        rules=LevelRules(SwitchInteractionMode.LIVE_LOOKAHEAD, lookahead, 0.12),
        _rules_present=True,
    )


def test_two_way_switch_gets_one_legal_verified_timestamp() -> None:
    level = _level()
    result = RuntimeSolutionSearchService().search(
        level, _metadata(("switch",), ("start", "switch", "package", "destination"))
    )

    assert result.passed
    assert len(result.actions) == 1
    assert result.diagnostics[0].window_open_seconds < result.actions[0].time_seconds
    assert result.actions[0].time_seconds < result.diagnostics[0].window_close_seconds
    assert result.replay_result.passed
    assert all(tap.code.value == "accepted" for tap in result.replay_result.taps)


def test_four_way_switch_rejects_three_rotations_when_window_is_too_short() -> None:
    level = _level(outgoing_targets=("dead", "branch_a", "branch_b", "package"), lookahead=0.2)
    result = RuntimeSolutionSearchService().search(
        level,
        _metadata(("switch", "switch", "switch"), ("start", "switch", "package", "destination")),
    )

    assert not result.passed
    assert result.failure_reason == "insufficient_rotation_window"
    assert result.diagnostics[0].rotation_count == 3


def test_revisited_switch_receives_separate_windows() -> None:
    level = _level(outgoing_targets=("package", "loop"))
    loop = next(node for node in level.graph.nodes if node.id == "loop")
    loop.x, loop.y, loop.outgoingEdgeIDs = 3, 1, ["loop_switch"]
    level.graph.edges.append(RouteEdge("loop_switch", "loop", "switch"))
    result = RuntimeSolutionSearchService().search(
        level,
        _metadata(
            ("switch", "switch"),
            ("start", "switch", "loop", "switch", "package", "destination"),
        ),
    )

    assert result.passed
    assert [item.visit_index for item in result.diagnostics] == [1, 2]
    assert result.diagnostics[0].window_close_seconds < result.diagnostics[1].window_open_seconds


def test_verified_solution_sidecar_uses_search_actions_and_diagnostics() -> None:
    level = _level()
    result = RuntimeSolutionSearchService().search(
        level, _metadata(("switch",), ("start", "switch", "package", "destination"))
    )
    solution = SolutionBuilderService().build_verified_runtime_solution(
        level.id, result, "Verified.", ("start", "switch", "package", "destination")
    )

    assert solution.maxTaps == len(result.replay_result.taps) == 1
    assert solution.actions == sorted(solution.actions, key=lambda action: action.timeSeconds)
    assert solution.actions[0]._extra["windowOpenSeconds"] < solution.actions[0].timeSeconds
    assert solution.actions[0].timeSeconds < solution.actions[0]._extra["windowCloseSeconds"]
    assert solution._extra["metadata"]["validationVersion"] == "verified_runtime_solution_v1"


def test_exact_strategy_timing_tracks_objective_state_normalization_and_one_use_roads() -> None:
    level = LevelDocument.from_dict(
        {
            "schemaVersion": 3,
            "id": "stateful_runtime_timing",
            "name": "Stateful Runtime Timing",
            "startNodeID": "start",
            "packageNodeID": "checkpoint",
            "destinationNodeID": "destination",
            "timeLimitSeconds": 20,
            "parTaps": 1,
            "rules": {
                "switchInteractionMode": "liveLookahead",
                "switchLookaheadSeconds": 1.35,
                "switchTapCooldownSeconds": 0.12,
            },
            "objectives": [
                {
                    "id": "inspect",
                    "nodeID": "checkpoint",
                    "kind": "checkpoint",
                    "sequenceIndex": 0,
                    "revealPolicy": "always",
                },
                {
                    "id": "finish",
                    "nodeID": "destination",
                    "kind": "destination",
                    "sequenceIndex": 1,
                    "revealPolicy": "whenActive",
                },
            ],
            "graph": {
                "nodes": [
                    {"id": "start", "x": 0, "y": 0, "outgoingEdgeIDs": ["to_hub"]},
                    {
                        "id": "hub",
                        "x": 2,
                        "y": 0,
                        "outgoingEdgeIDs": ["to_checkpoint", "to_dead", "to_destination"],
                    },
                    {"id": "dead", "x": 2, "y": -1, "outgoingEdgeIDs": []},
                    {"id": "checkpoint", "x": 3, "y": 1, "outgoingEdgeIDs": ["return_hub"]},
                    {"id": "destination", "x": 4, "y": 0, "outgoingEdgeIDs": []},
                ],
                "edges": [
                    {"id": "to_hub", "fromNodeID": "start", "toNodeID": "hub"},
                    {"id": "to_dead", "fromNodeID": "hub", "toNodeID": "dead"},
                    {
                        "id": "to_checkpoint",
                        "fromNodeID": "hub",
                        "toNodeID": "checkpoint",
                        "availabilityRule": {"maximumObjectiveIndex": 0, "usageLimit": 1},
                    },
                    {
                        "id": "to_destination",
                        "fromNodeID": "hub",
                        "toNodeID": "destination",
                        "availabilityRule": {
                            "requiredCompletedObjectiveIDs": ["inspect"],
                            "minimumObjectiveIndex": 1,
                        },
                    },
                    {"id": "return_hub", "fromNodeID": "checkpoint", "toNodeID": "hub"},
                ],
            },
        }
    )
    exact = StrategySearchService().search(level).canonical_optimal_strategy

    result = RuntimeSolutionSearchService().search(level, exact)

    assert result.passed
    assert [action.expected_edge_after_tap for action in result.actions] == ["to_destination"]
    assert [item.visit_index for item in result.diagnostics] == [1, 2]
    assert [item.rotation_count for item in result.diagnostics] == [0, 1]
    assert [item.selected_edge_id for item in result.diagnostics] == [
        "to_checkpoint",
        "to_destination",
    ]
    assert [item.objective_index for item in result.diagnostics] == [0, 1]
    assert result.diagnostics[0].active_objective_id == "inspect"
    assert result.diagnostics[1].active_objective_id == "finish"
    assert result.diagnostics[1].completed_objective_ids == ("inspect",)
    assert "to_checkpoint" in result.diagnostics[1].consumed_edge_ids
    assert "to_checkpoint" not in result.diagnostics[1].available_edge_ids
    assert "to_destination" in result.diagnostics[1].available_edge_ids
    assert result.jitter_report is not None and result.jitter_report.passed
