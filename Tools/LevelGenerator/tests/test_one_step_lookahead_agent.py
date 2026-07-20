from __future__ import annotations

from tiny_routes_core.models import LevelDocument

from app.agents import (
    GreedyObjectiveAgent,
    OneStepLookaheadAgent,
    PlayerObservation,
)
from app.models import PuzzleTerminalOutcome
from app.services import PuzzleStateTransitionService


def _local_trap_level() -> LevelDocument:
    return LevelDocument.from_dict(
        {
            "schemaVersion": 3,
            "id": "one_step_fixture",
            "name": "One Step Fixture",
            "startNodeID": "start",
            "packageNodeID": "destination",
            "destinationNodeID": "destination",
            "timeLimitSeconds": 30,
            "parTaps": 0,
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
                        "outgoingEdgeIDs": ["near_trap", "safe_road"],
                    },
                    {"id": "trap", "x": 9, "y": 0, "outgoingEdgeIDs": []},
                    {
                        "id": "junction",
                        "x": 5,
                        "y": 4,
                        "outgoingEdgeIDs": ["finish", "later_trap"],
                    },
                    {"id": "later_dead_end", "x": 4, "y": 5, "outgoingEdgeIDs": []},
                    {"id": "destination", "x": 10, "y": 0, "outgoingEdgeIDs": []},
                ],
                "edges": [
                    {"id": "near_trap", "fromNodeID": "start", "toNodeID": "trap"},
                    {"id": "safe_road", "fromNodeID": "start", "toNodeID": "junction"},
                    {"id": "finish", "fromNodeID": "junction", "toNodeID": "destination"},
                    {
                        "id": "later_trap",
                        "fromNodeID": "junction",
                        "toNodeID": "later_dead_end",
                    },
                ],
            },
        }
    )


def test_one_step_agent_avoids_failure_greedy_cannot_see() -> None:
    level = _local_trap_level()
    transitions = PuzzleStateTransitionService()
    state = transitions.initial_state(level)
    observation = PlayerObservation(state, transitions.available_actions(level, state))

    assert (
        GreedyObjectiveAgent(level).choose_action(observation).selected_edge_id
        == "near_trap"
    )
    assert (
        OneStepLookaheadAgent(level).choose_action(observation).selected_edge_id
        == "safe_road"
    )


def test_one_step_agent_is_deterministic_and_uses_only_observed_actions() -> None:
    level = _local_trap_level()
    transitions = PuzzleStateTransitionService()
    state = transitions.initial_state(level)
    safe_action = next(
        action
        for action in transitions.available_actions(level, state)
        if action.selected_edge_id == "safe_road"
    )
    observation = PlayerObservation(state, (safe_action,))

    first = OneStepLookaheadAgent(level).choose_decision(observation)
    second = OneStepLookaheadAgent(level).choose_decision(observation)

    assert first == second == safe_action


def test_one_step_agent_returns_none_for_terminal_observation() -> None:
    level = _local_trap_level()
    state = PuzzleStateTransitionService().initial_state(level).evolve(
        terminal_outcome=PuzzleTerminalOutcome.FAILURE,
    )

    assert OneStepLookaheadAgent(level).choose_action(PlayerObservation(state, ())) is None
