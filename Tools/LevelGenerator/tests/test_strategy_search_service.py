from __future__ import annotations

from tiny_routes_core.models import LevelDocument

from app.services import StrategySearchConfig, StrategySearchService


def _weighted_level() -> LevelDocument:
    return LevelDocument.from_dict(
        {
            "schemaVersion": 3,
            "id": "weighted_fixture",
            "name": "Weighted Fixture",
            "startNodeID": "start",
            "packageNodeID": "destination",
            "destinationNodeID": "destination",
            "timeLimitSeconds": 100,
            "parTaps": 0,
            "objectives": [
                {
                    "id": "destination",
                    "nodeID": "destination",
                    "kind": "destination",
                    "sequenceIndex": 0,
                    "revealPolicy": "always",
                }
            ],
            "graph": {
                "nodes": [
                    {
                        "id": "start",
                        "x": 0,
                        "y": 0,
                        "outgoingEdgeIDs": ["long_default", "short_tapped", "failure"],
                    },
                    {"id": "long_mid", "x": 5, "y": 0, "outgoingEdgeIDs": ["long_finish"]},
                    {"id": "short_mid", "x": 0, "y": 1, "outgoingEdgeIDs": ["short_finish"]},
                    {"id": "dead", "x": -1, "y": 0, "outgoingEdgeIDs": []},
                    {"id": "destination", "x": 0, "y": 2, "outgoingEdgeIDs": []},
                ],
                "edges": [
                    {"id": "long_default", "fromNodeID": "start", "toNodeID": "long_mid"},
                    {"id": "long_finish", "fromNodeID": "long_mid", "toNodeID": "destination"},
                    {"id": "short_tapped", "fromNodeID": "start", "toNodeID": "short_mid"},
                    {"id": "short_finish", "fromNodeID": "short_mid", "toNodeID": "destination"},
                    {"id": "failure", "fromNodeID": "start", "toNodeID": "dead"},
                ],
            },
        }
    )


def test_weighted_search_uses_taps_before_distance_and_classifies_outcomes() -> None:
    result = StrategySearchService().search(
        _weighted_level(),
        config=StrategySearchConfig(near_optimal_tap_margin=1),
    )

    assert result.succeeded
    assert result.exhaustive
    assert result.optimal_cost is not None
    assert result.optimal_cost.accepted_taps == 0
    assert result.canonical_optimal_strategy is not None
    assert result.canonical_optimal_strategy.actions[0].selected_edge_id == "long_default"
    assert [trace.actions[0].selected_edge_id for trace in result.near_optimal_strategies] == [
        "short_tapped"
    ]
    assert [trace.outcome_code for trace in result.failure_outcomes] == [
        "structural_dead_end"
    ]
    assert result.explored_state_count == 1


def test_search_reports_hard_action_bound_as_non_exhaustive() -> None:
    level = LevelDocument.from_dict(
        {
            "schemaVersion": 3,
            "id": "loop_fixture",
            "name": "Loop Fixture",
            "startNodeID": "loop",
            "packageNodeID": "destination",
            "destinationNodeID": "destination",
            "timeLimitSeconds": 10,
            "parTaps": 0,
            "objectives": [
                {
                    "id": "destination",
                    "nodeID": "destination",
                    "kind": "destination",
                    "sequenceIndex": 0,
                    "revealPolicy": "always",
                }
            ],
            "graph": {
                "nodes": [
                    {
                        "id": "loop",
                        "x": 0,
                        "y": 0,
                        "outgoingEdgeIDs": ["again", "give_up"],
                    },
                    {"id": "dead", "x": 0, "y": -1, "outgoingEdgeIDs": []},
                    {"id": "destination", "x": 1, "y": 0, "outgoingEdgeIDs": []},
                ],
                "edges": [
                    {"id": "again", "fromNodeID": "loop", "toNodeID": "loop"},
                    {"id": "give_up", "fromNodeID": "loop", "toNodeID": "dead"},
                ],
            },
        }
    )

    result = StrategySearchService().search(
        level,
        config=StrategySearchConfig(maximum_actions_per_strategy=2),
    )

    assert not result.succeeded
    assert not result.exhaustive
    assert result.limit_reasons == ("strategy_action_limit_reached",)
    assert "strategy_action_limit_reached" in {
        trace.outcome_code for trace in result.failure_outcomes
    }


def test_search_retains_all_equal_cost_optimal_action_classes() -> None:
    level = LevelDocument.from_dict(
        {
            "schemaVersion": 3,
            "id": "equal_fixture",
            "name": "Equal Fixture",
            "startNodeID": "start",
            "packageNodeID": "destination",
            "destinationNodeID": "destination",
            "timeLimitSeconds": 30,
            "parTaps": 1,
            "objectives": [
                {
                    "id": "destination",
                    "nodeID": "destination",
                    "kind": "destination",
                    "sequenceIndex": 0,
                    "revealPolicy": "always",
                }
            ],
            "graph": {
                "nodes": [
                    {"id": "start", "x": 0, "y": 0, "outgoingEdgeIDs": ["upper", "lower"]},
                    {"id": "upper_switch", "x": 1, "y": 1, "outgoingEdgeIDs": ["upper_fail", "upper_win"]},
                    {"id": "lower_switch", "x": 1, "y": -1, "outgoingEdgeIDs": ["lower_win", "lower_fail"]},
                    {"id": "upper_dead", "x": 2, "y": 2, "outgoingEdgeIDs": []},
                    {"id": "lower_dead", "x": 2, "y": -2, "outgoingEdgeIDs": []},
                    {"id": "destination", "x": 2, "y": 0, "outgoingEdgeIDs": []},
                ],
                "edges": [
                    {"id": "upper", "fromNodeID": "start", "toNodeID": "upper_switch"},
                    {"id": "lower", "fromNodeID": "start", "toNodeID": "lower_switch"},
                    {"id": "upper_fail", "fromNodeID": "upper_switch", "toNodeID": "upper_dead"},
                    {"id": "upper_win", "fromNodeID": "upper_switch", "toNodeID": "destination"},
                    {"id": "lower_win", "fromNodeID": "lower_switch", "toNodeID": "destination"},
                    {"id": "lower_fail", "fromNodeID": "lower_switch", "toNodeID": "lower_dead"},
                ],
            },
        }
    )

    result = StrategySearchService().search(level)

    assert result.exhaustive
    assert result.optimal_cost is not None
    assert result.optimal_cost.accepted_taps == 1
    assert len(result.equal_cost_optimal_strategies) == 2
    assert {
        trace.actions[0].selected_edge_id
        for trace in result.equal_cost_optimal_strategies
    } == {"upper", "lower"}
