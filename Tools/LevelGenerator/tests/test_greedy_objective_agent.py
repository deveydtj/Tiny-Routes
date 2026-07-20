from __future__ import annotations

from tiny_routes_core.models import LevelDocument

from app.agents import GreedyObjectiveAgent, PlayerObservation
from app.models import PuzzleTerminalOutcome
from app.services import PuzzleStateTransitionService


def _two_phase_level() -> LevelDocument:
    return LevelDocument.from_dict(
        {
            "schemaVersion": 3,
            "id": "greedy_objective_fixture",
            "name": "Greedy Objective Fixture",
            "startNodeID": "start",
            "packageNodeID": "pickup",
            "destinationNodeID": "destination",
            "timeLimitSeconds": 30,
            "parTaps": 0,
            "objectives": [
                {
                    "id": "pickup_objective",
                    "nodeID": "pickup",
                    "kind": "pickup",
                    "sequenceIndex": 0,
                    "revealPolicy": "always",
                },
                {
                    "id": "destination_objective",
                    "nodeID": "destination",
                    "kind": "destination",
                    "sequenceIndex": 1,
                    "revealPolicy": "afterPrevious",
                },
            ],
            "graph": {
                "nodes": [
                    {"id": "start", "x": 0, "y": 0, "outgoingEdgeIDs": ["to_pickup"]},
                    {
                        "id": "pickup",
                        "x": 5,
                        "y": 0,
                        "outgoingEdgeIDs": ["away", "toward_destination"],
                    },
                    {"id": "away_end", "x": 0, "y": 4, "outgoingEdgeIDs": []},
                    {"id": "destination", "x": 10, "y": 0, "outgoingEdgeIDs": []},
                ],
                "edges": [
                    {"id": "to_pickup", "fromNodeID": "start", "toNodeID": "pickup"},
                    {"id": "away", "fromNodeID": "pickup", "toNodeID": "away_end"},
                    {
                        "id": "toward_destination",
                        "fromNodeID": "pickup",
                        "toNodeID": "destination",
                    },
                ],
            },
        }
    )


def test_greedy_agent_uses_the_current_ordered_objective() -> None:
    level = _two_phase_level()
    transitions = PuzzleStateTransitionService()
    initial = transitions.initial_state(level)

    pickup_arrival = transitions.transition(
        level,
        initial,
        transitions.available_actions(level, initial)[0],
    ).state
    observation = PlayerObservation(
        pickup_arrival,
        transitions.available_actions(level, pickup_arrival),
    )

    assert pickup_arrival.objective_index == 1
    assert (
        GreedyObjectiveAgent(level).choose_action(observation).selected_edge_id
        == "toward_destination"
    )


def test_greedy_agent_breaks_equal_distance_ties_by_visible_action_order() -> None:
    level = _two_phase_level()
    away_end = next(node for node in level.graph.nodes if node.id == "away_end")
    destination = next(node for node in level.graph.nodes if node.id == "destination")
    away_end.x = destination.x
    away_end.y = destination.y
    transitions = PuzzleStateTransitionService()
    initial = transitions.initial_state(level)
    state = transitions.transition(
        level,
        initial,
        transitions.available_actions(level, initial)[0],
    ).state
    actions = transitions.available_actions(level, state)

    assert (
        GreedyObjectiveAgent(level)
        .choose_decision(PlayerObservation(state, actions))
        .selected_edge_id
        == "away"
    )
    assert (
        GreedyObjectiveAgent(level)
        .choose_decision(PlayerObservation(state, tuple(reversed(actions))))
        .selected_edge_id
        == "toward_destination"
    )


def test_greedy_agent_returns_none_for_terminal_observation() -> None:
    level = _two_phase_level()
    state = PuzzleStateTransitionService().initial_state(level).evolve(
        terminal_outcome=PuzzleTerminalOutcome.FAILURE,
    )

    assert GreedyObjectiveAgent(level).choose_action(PlayerObservation(state, ())) is None
