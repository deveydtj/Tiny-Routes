from __future__ import annotations

import pytest
from tiny_routes_core.models import LevelDocument

from app.agents import PlayerObservation, RandomAgent
from app.models import PuzzleTerminalOutcome
from app.services import PuzzleStateTransitionService


def _choice_level() -> LevelDocument:
    return LevelDocument.from_dict(
        {
            "schemaVersion": 3,
            "id": "random_agent_fixture",
            "name": "Random Agent Fixture",
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
                    {
                        "id": "start",
                        "x": 0,
                        "y": 0,
                        "outgoingEdgeIDs": ["left", "center", "right"],
                    },
                    {"id": "left_end", "x": -1, "y": 1, "outgoingEdgeIDs": []},
                    {"id": "center_end", "x": 0, "y": 1, "outgoingEdgeIDs": []},
                    {"id": "destination", "x": 1, "y": 1, "outgoingEdgeIDs": []},
                ],
                "edges": [
                    {"id": "left", "fromNodeID": "start", "toNodeID": "left_end"},
                    {"id": "center", "fromNodeID": "start", "toNodeID": "center_end"},
                    {"id": "right", "fromNodeID": "start", "toNodeID": "destination"},
                ],
            },
        }
    )


def test_random_agent_is_seeded_reproducible_and_selects_only_visible_actions() -> None:
    level = _choice_level()
    transitions = PuzzleStateTransitionService()
    state = transitions.initial_state(level)
    observation = PlayerObservation(
        state,
        transitions.available_actions(level, state),
    )
    first = RandomAgent(seed=712)
    second = RandomAgent(seed=712)

    first_choices = tuple(
        first.choose_action(observation).selected_edge_id for _ in range(12)
    )
    second_choices = tuple(
        second.choose_action(observation).selected_edge_id for _ in range(12)
    )

    assert first_choices == second_choices
    assert set(first_choices) <= {"left", "center", "right"}
    assert len(set(first_choices)) > 1


def test_random_agent_returns_none_when_no_action_is_visible() -> None:
    level = _choice_level()
    state = PuzzleStateTransitionService().initial_state(level).evolve(
        terminal_outcome=PuzzleTerminalOutcome.FAILURE,
    )

    assert RandomAgent(seed=1).choose_action(PlayerObservation(state, ())) is None


def test_player_observation_rejects_hidden_or_wrong_node_actions() -> None:
    level = _choice_level()
    transitions = PuzzleStateTransitionService()
    state = transitions.initial_state(level)
    action = transitions.available_actions(level, state)[0]
    hidden_state = state.evolve(
        available_edge_ids=("center", "right"),
        active_switch_edge_ids=(("start", "center"),),
    )

    with pytest.raises(ValueError, match="visible available edges"):
        PlayerObservation(hidden_state, (action,))


@pytest.mark.parametrize("seed", [True, 1.5, "1"])
def test_random_agent_requires_an_integer_seed(seed) -> None:
    with pytest.raises(ValueError, match="seed must be an integer"):
        RandomAgent(seed=seed)
