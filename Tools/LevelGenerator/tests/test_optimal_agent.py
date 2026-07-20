from __future__ import annotations

from dataclasses import replace

import pytest
from tiny_routes_core.models import LevelDocument

from app.agents import OptimalAgent, PlayerObservation
from app.services import PuzzleStateTransitionService, StrategySearchService


def _optimal_level() -> LevelDocument:
    return LevelDocument.from_dict(
        {
            "schemaVersion": 3,
            "id": "optimal_agent_fixture",
            "name": "Optimal Agent Fixture",
            "startNodeID": "start",
            "packageNodeID": "destination",
            "destinationNodeID": "destination",
            "timeLimitSeconds": 30,
            "parTaps": 1,
            "objectives": [
                {
                    "id": "destination_objective",
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
                        "outgoingEdgeIDs": ["trap", "planned"],
                    },
                    {"id": "dead_end", "x": 2, "y": 0, "outgoingEdgeIDs": []},
                    {
                        "id": "junction",
                        "x": 1,
                        "y": 1,
                        "outgoingEdgeIDs": ["finish", "later_trap"],
                    },
                    {"id": "later_dead_end", "x": 2, "y": 2, "outgoingEdgeIDs": []},
                    {"id": "destination", "x": 3, "y": 0, "outgoingEdgeIDs": []},
                ],
                "edges": [
                    {"id": "trap", "fromNodeID": "start", "toNodeID": "dead_end"},
                    {"id": "planned", "fromNodeID": "start", "toNodeID": "junction"},
                    {"id": "finish", "fromNodeID": "junction", "toNodeID": "destination"},
                    {"id": "later_trap", "fromNodeID": "junction", "toNodeID": "later_dead_end"},
                ],
            },
        }
    )


def test_optimal_agent_adapts_exact_proof_across_the_canonical_path() -> None:
    level = _optimal_level()
    transitions = PuzzleStateTransitionService()
    state = transitions.initial_state(level)
    proof = StrategySearchService().search(level)
    agent = OptimalAgent(level, search_result=proof)

    first_observation = PlayerObservation(
        state,
        transitions.available_actions(level, state),
    )
    first = agent.choose_action(first_observation)
    assert first is not None
    assert first.selected_edge_id == "planned"

    successor = transitions.transition(level, state, first).state
    second_observation = PlayerObservation(
        successor,
        transitions.available_actions(level, successor),
    )
    second = agent.choose_decision(second_observation)
    assert second is not None
    assert second.selected_edge_id == "finish"
    assert agent.search_result is proof


def test_optimal_agent_never_selects_an_action_missing_from_observation() -> None:
    level = _optimal_level()
    transitions = PuzzleStateTransitionService()
    state = transitions.initial_state(level)
    trap = next(
        action
        for action in transitions.available_actions(level, state)
        if action.selected_edge_id == "trap"
    )
    agent = OptimalAgent(level)

    assert agent.choose_action(PlayerObservation(state, (trap,))) == trap


def test_optimal_agent_rejects_incomplete_or_unsuccessful_proof() -> None:
    level = _optimal_level()
    proof = StrategySearchService().search(level)

    with pytest.raises(ValueError, match="exhaustive"):
        OptimalAgent(level, search_result=replace(proof, exhaustive=False))
    with pytest.raises(ValueError, match="successful"):
        OptimalAgent(
            level,
            search_result=replace(
                proof,
                optimal_cost=None,
                canonical_optimal_strategy=None,
                equal_cost_optimal_strategies=(),
                near_optimal_strategies=(),
                longer_successful_strategies=(),
            ),
        )
