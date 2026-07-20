from __future__ import annotations

from tiny_routes_core.models import LevelDocument

from app.agents import (
    OneStepLookaheadAgent,
    PlayerObservation,
    TwoStepPlanningAgent,
)
from app.models import PuzzleTerminalOutcome
from app.services import PuzzleStateTransitionService


def two_step_fixture() -> LevelDocument:
    return LevelDocument.from_dict(
        {
            "schemaVersion": 3,
            "id": "two_step_fixture",
            "name": "Two Step Fixture",
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
                        "outgoingEdgeIDs": ["tempting", "planned"],
                    },
                    {
                        "id": "near_junction",
                        "x": 8,
                        "y": 0,
                        "outgoingEdgeIDs": ["near_trap_a", "near_trap_b"],
                    },
                    {
                        "id": "far_junction",
                        "x": 4,
                        "y": 4,
                        "outgoingEdgeIDs": ["finish", "far_trap"],
                    },
                    {"id": "dead_a", "x": 9, "y": 1, "outgoingEdgeIDs": []},
                    {"id": "dead_b", "x": 9, "y": -1, "outgoingEdgeIDs": []},
                    {"id": "dead_c", "x": 5, "y": 5, "outgoingEdgeIDs": []},
                    {"id": "destination", "x": 10, "y": 0, "outgoingEdgeIDs": []},
                ],
                "edges": [
                    {"id": "tempting", "fromNodeID": "start", "toNodeID": "near_junction"},
                    {"id": "planned", "fromNodeID": "start", "toNodeID": "far_junction"},
                    {"id": "near_trap_a", "fromNodeID": "near_junction", "toNodeID": "dead_a"},
                    {"id": "near_trap_b", "fromNodeID": "near_junction", "toNodeID": "dead_b"},
                    {"id": "finish", "fromNodeID": "far_junction", "toNodeID": "destination"},
                    {"id": "far_trap", "fromNodeID": "far_junction", "toNodeID": "dead_c"},
                ],
            },
        }
    )


def test_two_step_agent_sees_a_success_beyond_one_step_horizon() -> None:
    level = two_step_fixture()
    transitions = PuzzleStateTransitionService()
    state = transitions.initial_state(level)
    observation = PlayerObservation(state, transitions.available_actions(level, state))

    assert OneStepLookaheadAgent(level).choose_action(observation).selected_edge_id == "tempting"
    assert TwoStepPlanningAgent(level).choose_action(observation).selected_edge_id == "planned"


def test_two_step_agent_is_deterministic_and_confined_to_observed_actions() -> None:
    level = two_step_fixture()
    transitions = PuzzleStateTransitionService()
    state = transitions.initial_state(level)
    tempting = next(
        action
        for action in transitions.available_actions(level, state)
        if action.selected_edge_id == "tempting"
    )
    observation = PlayerObservation(state, (tempting,))
    agent = TwoStepPlanningAgent(level)

    assert agent.choose_action(observation) == tempting
    assert agent.choose_decision(observation) == tempting


def test_two_step_agent_returns_none_for_terminal_observation() -> None:
    level = two_step_fixture()
    state = PuzzleStateTransitionService().initial_state(level).evolve(
        terminal_outcome=PuzzleTerminalOutcome.FAILURE,
    )

    assert TwoStepPlanningAgent(level).choose_action(PlayerObservation(state, ())) is None
