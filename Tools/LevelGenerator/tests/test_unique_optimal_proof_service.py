from __future__ import annotations

from tiny_routes_core.models import LevelDocument

from app.models import OptimalStrategyRequirements
from app.services import (
    StrategySearchConfig,
    StrategySearchService,
    UniqueOptimalProofService,
)


def _two_route_level(*, tied: bool) -> LevelDocument:
    lower_x = 1 if tied else 2
    return LevelDocument.from_dict(
        {
            "schemaVersion": 3,
            "id": "proof_fixture",
            "name": "Proof Fixture",
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
                    {"id": "lower_switch", "x": lower_x, "y": -1, "outgoingEdgeIDs": ["lower_win", "lower_fail"]},
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


def _incomplete_level() -> LevelDocument:
    return LevelDocument.from_dict(
        {
            "schemaVersion": 3,
            "id": "incomplete_proof_fixture",
            "name": "Incomplete Proof Fixture",
            "startNodeID": "start",
            "packageNodeID": "destination",
            "destinationNodeID": "destination",
            "timeLimitSeconds": 30,
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
                    {"id": "start", "x": 0, "y": 0, "outgoingEdgeIDs": ["win", "enter_loop"]},
                    {"id": "loop", "x": 1, "y": 0, "outgoingEdgeIDs": ["again", "fail"]},
                    {"id": "dead", "x": 1, "y": -1, "outgoingEdgeIDs": []},
                    {"id": "destination", "x": 0, "y": 1, "outgoingEdgeIDs": []},
                ],
                "edges": [
                    {"id": "win", "fromNodeID": "start", "toNodeID": "destination"},
                    {"id": "enter_loop", "fromNodeID": "start", "toNodeID": "loop"},
                    {"id": "again", "fromNodeID": "loop", "toNodeID": "loop"},
                    {"id": "fail", "fromNodeID": "loop", "toNodeID": "dead"},
                ],
            },
        }
    )


def test_proof_accepts_one_exhaustively_proven_target_compliant_optimum() -> None:
    level = _two_route_level(tied=False)
    result = StrategySearchService().search(level)

    proof = UniqueOptimalProofService().prove(
        level,
        result,
        requirements=OptimalStrategyRequirements(
            required_decision_node_ids=("start", "upper_switch"),
            required_selected_edge_ids=("upper", "upper_win"),
            required_objective_ids=("destination",),
        ),
    )

    assert proof.accepted
    assert proof.exhaustive
    assert proof.is_unique
    assert proof.rejection_reasons == ()


def test_proof_rejects_non_equivalent_equal_cost_optima() -> None:
    level = _two_route_level(tied=True)
    proof = UniqueOptimalProofService().prove(
        level,
        StrategySearchService().search(level),
    )

    assert not proof.accepted
    assert not proof.is_unique
    assert proof.rejection_reasons == ("unique_optimal_multiple_strategy_classes",)
    assert len(proof.equal_cost_strategy_classes) == 2


def test_proof_rejects_incomplete_search_even_after_finding_a_success() -> None:
    level = _incomplete_level()
    result = StrategySearchService().search(
        level,
        config=StrategySearchConfig(maximum_explored_states=1),
    )
    proof = UniqueOptimalProofService().prove(level, result)

    assert result.succeeded
    assert not proof.accepted
    assert "unique_optimal_search_incomplete" in proof.rejection_reasons
    assert "unique_optimal_limit:strategy_state_limit_reached" in proof.rejection_reasons


def test_proof_rejects_missing_required_strategy_evidence() -> None:
    level = _two_route_level(tied=False)
    proof = UniqueOptimalProofService().prove(
        level,
        StrategySearchService().search(level),
        requirements=OptimalStrategyRequirements(
            required_decision_node_ids=("unrealized_hub",),
            required_opened_edge_ids=("unrealized_shortcut",),
        ),
    )

    assert not proof.accepted
    assert proof.rejection_reasons == (
        "unique_optimal_required_decision_node_missing:unrealized_hub",
        "unique_optimal_required_opened_edge_missing:unrealized_shortcut",
    )
